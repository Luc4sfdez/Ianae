"""
Worker Executor autonomo para IANAE.

Cierra el loop de autonomia: detecta ordenes pendientes, genera cambios via LLM,
aplica archivos, corre tests, y publica reportes — sin intervencion humana.

Flujo:
  Daemon -> publica orden -> WorkerExecutor detecta -> LLM genera cambios
  -> aplica -> tests -> reporta -> Daemon detecta -> siguiente orden

Uso:
  python worker_executor.py worker-core
  python worker_executor.py worker-core --project-root /ruta/al/proyecto
"""

import os
import re
import sys
import time
import shutil
import subprocess
import logging
from pathlib import Path
import json
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient
from llm_provider import ProviderChain
from workflow_status import mark_as_in_progress, mark_as_completed, mark_as_blocked
from structured_logger import get_logger
from config import (
    DOCS_SERVICE_URL,
    LLM_PROVIDERS,
    VALID_WORKERS,
    WORKER_CHECK_INTERVAL,
    WORKER_MAX_TOKENS,
    WORKER_MAX_FILES,
    WORKER_MAX_RETRIES,
    WORKER_RETRY_DELAY,
    WORKER_SCOPES,
    WORKER_CHUNK_PLAN_TOKENS,
    WORKER_CHUNK_FILE_TOKENS,
    WORKER_ANTHROPIC_FILE_TOKENS,
    WORKER_COMPLEXITY_THRESHOLD_FILES,
    WORKER_LARGE_FILE_LINES,
)

logger = get_logger("worker_executor")


def parse_llm_file_blocks(response_text: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Parsea la respuesta del LLM extrayendo bloques de archivo y reporte.

    Formato esperado:
        ### FILE: src/core/emergente.py
        ```python
        # contenido
        ```

        ### REPORT
        Descripcion de cambios...

    Returns:
        (files, report) donde files es lista de {"path": ..., "content": ...}
    """
    files = []
    report = ""

    # Extraer bloques ### FILE: path
    file_pattern = re.compile(
        r'###\s*FILE:\s*(.+?)\s*\n'
        r'```[a-zA-Z]*\s*\n'
        r'(.*?)'
        r'\n```',
        re.DOTALL,
    )

    for match in file_pattern.finditer(response_text):
        file_path = match.group(1).strip()
        content = match.group(2)
        files.append({"path": file_path, "content": content})

    # Extraer ### REPORT
    report_match = re.search(
        r'###\s*REPORT\s*\n(.*)',
        response_text,
        re.DOTALL,
    )
    if report_match:
        report = report_match.group(1).strip()
        # Cortar el report si hay otro bloque despues (no deberia)
        next_block = re.search(r'\n###\s', report)
        if next_block:
            report = report[:next_block.start()].strip()

    return files, report


class WorkerExecutor:
    """
    Motor de ejecucion autonomo para workers IANAE.

    Poll ordenes pendientes, genera cambios via LLM, aplica, corre tests,
    y publica reportes. Incluye scope enforcement y rollback automatico.
    """

    def __init__(
        self,
        worker_name: str,
        project_root: str,
        scope_paths: Optional[List[str]] = None,
        check_interval: int = WORKER_CHECK_INTERVAL,
    ):
        if worker_name not in VALID_WORKERS:
            raise ValueError(
                f"Worker no valido: {worker_name}. "
                f"Validos: {', '.join(VALID_WORKERS)}"
            )

        self.worker_name = worker_name
        self.project_root = Path(project_root).resolve()
        self.check_interval = check_interval

        # Scope desde config o parametro
        scope_config = WORKER_SCOPES.get(worker_name, {})
        self.scope_paths = scope_paths or scope_config.get("paths", [])
        self.test_cmd = scope_config.get("test_cmd", "python -m pytest tests/ -q")

        # Clients
        self.docs_client = DocsClient(DOCS_SERVICE_URL)
        self.llm_chain = ProviderChain(LLM_PROVIDERS)

        # System prompt del worker
        self.system_prompt = self._load_system_prompt()

        # Backup para rollback
        self._backups: Dict[str, bytes] = {}

        # Tracking de reintentos: {doc_id: attempts_count}
        self._attempts: Dict[int, int] = {}

        # IDs de ordenes completadas o permanentemente fallidas (no reintentar)
        self._processed_ids: set = set()

        # Titulos ya vistos (anti-duplicados: si hay 2 ordenes con mismo titulo, skip la segunda)
        self._seen_titles: set = set()

        # Ultimo output de tests fallidos (para feedback en reintentos)
        self._last_test_output: str = ""

        logger.info(
            f"WorkerExecutor inicializado",
            worker=worker_name,
            project_root=str(self.project_root),
            scope=self.scope_paths,
            test_cmd=self.test_cmd,
            providers=self.llm_chain.available_providers,
        )

    # Tarifas por 1M tokens (USD)
    COST_RATES = {
        "deepseek": {"input": 0.27, "output": 1.10},
        "qwen": {"input": 0.80, "output": 2.00},
        "anthropic": {"input": 3.00, "output": 15.00},
    }

    def _estimate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Estimar costo en USD de una llamada LLM."""
        rates = self.COST_RATES.get(provider, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
        return round(cost, 6)

    def _cost_block(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> str:
        """Generar bloque JSON de costos para incluir en reportes."""
        cost_usd = self._estimate_cost(provider, input_tokens, output_tokens)
        data = {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }
        return f"\n\n<!-- COST_DATA: {json.dumps(data)} -->"

    def _load_system_prompt(self) -> str:
        """Construir system prompt enfocado en formato de salida."""
        format_prompt = (
            f"Eres {self.worker_name} de IANAE, un sistema de inteligencia emergente.\n"
            f"Tu scope: {', '.join(self.scope_paths)}\n\n"
            "FORMATO DE RESPUESTA OBLIGATORIO:\n"
            "Tu respuesta DEBE contener bloques de archivo con este formato EXACTO:\n\n"
            "### FILE: ruta/al/archivo.py\n"
            "```python\n"
            "# contenido del archivo\n"
            "```\n\n"
            "### REPORT\n"
            "Breve descripcion de cambios.\n\n"
            "REGLAS CRITICAS:\n"
            "- SIEMPRE genera al menos un bloque ### FILE:\n"
            "- Para archivos NUEVOS (tests, etc): contenido completo\n"
            "- Si el contexto dice '(RESUMEN)', el archivo es grande. "
            "NO lo reescribas completo. Genera SOLO un archivo con los "
            "metodos/funciones NUEVOS a agregar. Yo los appendeo al final.\n"
            "- NO escribas explicaciones antes de los bloques de archivo\n"
            "- Empieza tu respuesta directamente con ### FILE:\n"
            f"- Maximo {WORKER_MAX_FILES} archivos\n"
            "- Solo archivos dentro de tu scope\n"
            "- IMPORTANTE: Cierra cada bloque con ```\n"
        )
        return format_prompt

    def _is_path_in_scope(self, file_path: str) -> bool:
        """Verificar que un path esta dentro del scope permitido."""
        # Normalizar separadores
        normalized = file_path.replace("\\", "/").lstrip("/")
        for scope in self.scope_paths:
            scope_normalized = scope.replace("\\", "/").rstrip("/")
            if normalized.startswith(scope_normalized):
                return True
            # Caso especial: scope es un archivo exacto (ej: pyproject.toml)
            if normalized == scope_normalized:
                return True
        return False

    def _fix_scope_path(self, file_path: str) -> Optional[str]:
        """
        Intentar corregir un path fuera de scope.

        Casos comunes que el LLM genera mal:
          tests/test_x.py -> tests/core/test_x.py (para worker-core)
          emergente.py -> src/core/emergente.py
          src/memoria.py -> src/core/memoria.py

        Returns:
            Path corregido o None si no se puede corregir.
        """
        normalized = file_path.replace("\\", "/").lstrip("/")
        if self._is_path_in_scope(normalized):
            return normalized

        filename = normalized.split("/")[-1]

        # Intentar ubicar en cada scope dir
        for scope in self.scope_paths:
            scope_normalized = scope.replace("\\", "/").rstrip("/")
            candidate = f"{scope_normalized}/{filename}"
            # Si es un test file, ponerlo en el scope de tests
            if "test" in filename.lower() and "test" in scope_normalized:
                return candidate
            # Si es un archivo de codigo, ponerlo en el scope de src
            if "test" not in filename.lower() and "test" not in scope_normalized:
                return candidate

        # Fallback: primer scope dir
        if self.scope_paths:
            return f"{self.scope_paths[0].rstrip('/')}/{filename}"

        return None

    def _read_scope_files(self, orden: Optional[Dict] = None) -> str:
        """
        Leer archivos del scope para dar contexto al LLM.

        Si la orden menciona archivos especificos, solo envia esos.
        Archivos grandes (>200 lineas) se envian resumidos (firma de clase + metodos).
        """
        context_parts = []
        MAX_FULL_LINES = 200  # Archivos mas grandes se resumen

        # Detectar archivos mencionados en la orden
        mentioned_files = set()
        if orden:
            text = orden.get("content", "") + " " + orden.get("title", "")
            import re as _re
            for match in _re.findall(r'[\w/\\]+\.py', text):
                mentioned_files.add(match.replace("\\", "/"))

        for scope_path in self.scope_paths:
            full_path = self.project_root / scope_path
            if full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    context_parts.append(
                        f"### FILE: {scope_path}\n```\n{content}\n```"
                    )
                except Exception as e:
                    logger.warning(f"No se pudo leer {scope_path}: {e}")
            elif full_path.is_dir():
                for py_file in sorted(full_path.rglob("*.py")):
                    rel = str(py_file.relative_to(self.project_root)).replace("\\", "/")

                    # Filtrar __init__.py siempre
                    if rel.endswith("__init__.py"):
                        continue

                    # Si hay archivos mencionados, solo enviar esos
                    is_test_file = "test" in rel.lower()
                    if mentioned_files:
                        is_mentioned = any(m in rel or rel.endswith(m) for m in mentioned_files)
                        if not is_mentioned and not is_test_file:
                            continue

                    try:
                        content = py_file.read_text(encoding="utf-8", errors="replace")
                        lines = content.split("\n")

                        if is_test_file:
                            # Tests siempre resumidos (imports + signatures)
                            summary = self._summarize_python(content, lines)
                            context_parts.append(
                                f"### FILE: {rel} (TEST - {len(lines)} lineas, "
                                f"NO modificar tests existentes)\n"
                                f"```python\n{summary}\n```"
                            )
                        elif len(lines) > MAX_FULL_LINES:
                            # Resumir: imports + signatures de clase/metodos + ultimas 30 lineas
                            summary = self._summarize_python(content, lines)
                            context_parts.append(
                                f"### FILE: {rel} (RESUMEN - {len(lines)} lineas, "
                                f"envia solo metodos NUEVOS para agregar)\n"
                                f"```python\n{summary}\n```"
                            )
                        else:
                            context_parts.append(
                                f"### FILE: {rel}\n```python\n{content}\n```"
                            )
                    except Exception as e:
                        logger.warning(f"No se pudo leer {rel}: {e}")

        return "\n\n".join(context_parts)

    @staticmethod
    def _summarize_python(content: str, lines: list) -> str:
        """Resumir archivo Python grande: imports + firmas de clase/metodo."""
        import re as _re
        summary_parts = []
        in_imports = True

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Mantener imports
            if in_imports and (stripped.startswith("import ") or
                               stripped.startswith("from ") or
                               stripped == "" or stripped.startswith("#")):
                summary_parts.append(line)
                continue
            elif in_imports and stripped:
                in_imports = False
                summary_parts.append("")
                summary_parts.append("# ... (imports above) ...")
                summary_parts.append("")

            # Mantener firmas de clase y metodos
            if _re.match(r'^class\s+\w+', stripped):
                summary_parts.append(line)
            elif _re.match(r'^    def\s+\w+', line):
                summary_parts.append(line)
                # Incluir docstring si hay
                if i + 1 < len(lines) and '"""' in lines[i + 1]:
                    summary_parts.append(lines[i + 1])
                    if '"""' not in lines[i + 1].split('"""', 1)[1]:
                        for j in range(i + 2, min(i + 6, len(lines))):
                            summary_parts.append(lines[j])
                            if '"""' in lines[j]:
                                break
                summary_parts.append("        ...")

        # Agregar ultimas 20 lineas (final de la clase)
        summary_parts.append("")
        summary_parts.append("# ... (ultimas lineas del archivo) ...")
        summary_parts.extend(lines[-20:])

        return "\n".join(summary_parts)

    def _backup_file(self, file_path: Path) -> None:
        """Guardar backup de un archivo para rollback."""
        if file_path.exists():
            self._backups[str(file_path)] = file_path.read_bytes()
        else:
            # Marcar como inexistente (para borrar en rollback)
            self._backups[str(file_path)] = None

    def _rollback(self) -> None:
        """Restaurar todos los archivos a su estado previo."""
        for path_str, content in self._backups.items():
            path = Path(path_str)
            if content is None:
                # Archivo no existia antes, borrar
                if path.exists():
                    path.unlink()
                    logger.info(f"Rollback: eliminado {path}")
            else:
                path.write_bytes(content)
                logger.info(f"Rollback: restaurado {path}")
        self._backups.clear()

    def _apply_files(self, files: List[Dict[str, str]]) -> List[str]:
        """
        Aplicar archivos generados por el LLM.

        Returns:
            Lista de paths aplicados.

        Raises:
            ValueError: Si algun path esta fuera del scope o hay demasiados archivos.
        """
        if len(files) > WORKER_MAX_FILES:
            raise ValueError(
                f"Demasiados archivos ({len(files)}), maximo {WORKER_MAX_FILES}"
            )

        # Validar scope ANTES de escribir nada
        for f in files:
            if not self._is_path_in_scope(f["path"]):
                raise ValueError(
                    f"Archivo fuera de scope: {f['path']}. "
                    f"Scope permitido: {self.scope_paths}"
                )

        applied = []
        self._backups.clear()

        for f in files:
            full_path = self.project_root / f["path"]

            # Backup antes de modificar
            self._backup_file(full_path)

            # Crear directorio si no existe
            full_path.parent.mkdir(parents=True, exist_ok=True)

            content = f["content"]

            # Si el archivo ya existe y el LLM genero solo metodos nuevos
            # (detectado porque no tiene imports/class pero tiene def),
            # appendear al archivo existente con indentacion correcta
            if full_path.exists() and self._should_append(content, full_path):
                existing = full_path.read_text(encoding="utf-8", errors="replace")
                # Detectar indentacion de la clase existente
                new_code = self._fix_indent_for_class(content, existing)
                content = existing.rstrip() + "\n\n" + new_code + "\n"
                logger.info(f"Appendeando metodos a: {f['path']}")
            else:
                logger.info(f"Archivo escrito: {f['path']}")

            full_path.write_text(content, encoding="utf-8")
            applied.append(f["path"])

        return applied

    @staticmethod
    def _fix_indent_for_class(new_code: str, existing_code: str) -> str:
        """Ajustar indentacion del codigo nuevo para que coincida con la clase."""
        import re as _re

        # Detectar indentacion de metodos en el archivo existente
        # Buscar "    def " al inicio de linea (metodo de clase con 4 espacios)
        existing_methods = _re.findall(r'^( +)def \w+', existing_code, _re.MULTILINE)
        if not existing_methods:
            return new_code.strip()

        target_indent = existing_methods[0]  # ej: "    " (4 espacios)

        # Detectar indentacion actual del codigo nuevo
        new_lines = new_code.strip().split("\n")
        new_methods = _re.findall(r'^( *)def \w+', new_code, _re.MULTILINE)

        if not new_methods:
            return new_code.strip()

        current_indent = new_methods[0]  # ej: "" (sin indentacion) o "    "

        if current_indent == target_indent:
            return new_code.strip()

        # Re-indentar: reemplazar indentacion actual por la target
        result_lines = []
        for line in new_lines:
            if line.strip() == "":
                result_lines.append("")
            elif line.startswith(current_indent):
                # Quitar indentacion actual, poner target
                stripped = line[len(current_indent):]
                result_lines.append(target_indent + stripped)
            else:
                result_lines.append(target_indent + line)

        return "\n".join(result_lines)

    @staticmethod
    def _should_append(new_content: str, existing_path: Path) -> bool:
        """Determinar si el contenido nuevo debe appendearse al existente."""
        lines = new_content.strip().split("\n")
        # Si el contenido nuevo no tiene class ni imports principales,
        # pero tiene def, probablemente son metodos para agregar
        has_class = any(l.strip().startswith("class ") for l in lines[:5])
        has_import_block = any(l.strip().startswith("import ") or
                               l.strip().startswith("from ") for l in lines[:10])
        has_def = any("def " in l for l in lines)

        # Si no tiene class ni imports pero tiene def -> append
        if not has_class and not has_import_block and has_def:
            # Solo si el archivo existente es grande (evitar append a archivos chicos)
            existing_lines = existing_path.read_text(
                encoding="utf-8", errors="replace"
            ).count("\n")
            return existing_lines > 200
        return False

    def _run_tests(self) -> Tuple[bool, str]:
        """
        Ejecutar tests del scope.

        Returns:
            (passed, output) tuple.
        """
        logger.info(f"Ejecutando tests: {self.test_cmd}")
        try:
            result = subprocess.run(
                self.test_cmd.split(),
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_root),
            )
            output = result.stdout + result.stderr
            passed = result.returncode == 0
            if passed:
                logger.info("Tests pasaron")
            else:
                logger.warning(f"Tests fallaron (rc={result.returncode})")
            return passed, output
        except subprocess.TimeoutExpired:
            return False, "Tests timeout (120s)"
        except Exception as e:
            return False, f"Error ejecutando tests: {e}"

    def _build_llm_messages(self, orden: Dict, context: str) -> List[Dict]:
        """Construir mensajes para el LLM con la orden y contexto."""
        orden_content = orden.get("content", "")
        orden_title = orden.get("title", "Sin titulo")

        user_message = (
            f"# Orden: {orden_title}\n\n"
            f"{orden_content}\n\n"
            f"# Archivos actuales (contexto)\n\n"
            f"{context}\n\n"
            "# RESPONDE AHORA con ### FILE: bloques\n"
            "Empieza directamente con ### FILE: ruta/archivo.py"
        )

        return [{"role": "user", "content": user_message}]

    # ------------------------------------------------------------------
    # Chunked generation: planning call + per-file calls
    # ------------------------------------------------------------------

    def _load_planning_prompt(self) -> str:
        """System prompt para la planning call (lista de archivos a generar)."""
        return (
            f"Eres {self.worker_name} de IANAE, un sistema de inteligencia emergente.\n"
            f"Tu scope: {', '.join(self.scope_paths)}\n\n"
            "TAREA: Analiza la orden y responde SOLO con un plan de archivos.\n"
            "NO generes codigo. Solo lista los archivos que necesitas crear o modificar.\n\n"
            "FORMATO DE RESPUESTA OBLIGATORIO:\n\n"
            "### PLAN\n"
            "- FILE: ruta/al/archivo.py — Breve descripcion de que hacer\n"
            "- FILE: ruta/al/test.py — Breve descripcion del test\n"
            "### REPORT\n"
            "Breve descripcion del approach general.\n\n"
            "REGLAS:\n"
            f"- Maximo {WORKER_MAX_FILES} archivos\n"
            "- Solo archivos dentro de tu scope\n"
            "- Cada linea FILE debe tener path y descripcion separados por —\n"
            "- NO generes codigo, solo el plan\n"
            "- Empieza directamente con ### PLAN\n"
        )

    def _load_file_gen_prompt(self, file_path: str, file_description: str,
                              plan_text: str, previously_generated: List[Dict[str, str]]) -> str:
        """System prompt para generar un archivo individual."""
        prev_context = ""
        if previously_generated:
            prev_parts = []
            for f in previously_generated:
                prev_parts.append(
                    f"### FILE: {f['path']}\n```python\n{f['content']}\n```"
                )
            prev_context = (
                "\n\nARCHIVOS YA GENERADOS (para coherencia, NO los repitas):\n\n"
                + "\n\n".join(prev_parts)
            )

        return (
            f"Eres {self.worker_name} de IANAE, un sistema de inteligencia emergente.\n"
            f"Tu scope: {', '.join(self.scope_paths)}\n\n"
            f"PLAN COMPLETO:\n{plan_text}\n\n"
            f"TAREA: Genera SOLO el contenido completo del archivo: {file_path}\n"
            f"Descripcion: {file_description}\n\n"
            "FORMATO DE RESPUESTA OBLIGATORIO:\n\n"
            f"### FILE: {file_path}\n"
            "```python\n"
            "# contenido completo del archivo\n"
            "```\n\n"
            "REGLAS CRITICAS:\n"
            f"- Genera SOLO el archivo {file_path}, ningun otro\n"
            "- Si el contexto dice '(RESUMEN)', el archivo es grande. "
            "NO lo reescribas completo. Genera SOLO los metodos/funciones NUEVOS a agregar.\n"
            "- Cierra el bloque de codigo con ```\n"
            "- NO incluyas ### REPORT ni otros archivos\n"
            f"{prev_context}"
        )

    def _cost_block_multi(self, responses) -> str:
        """Generar bloque JSON de costos acumulados de multiples llamadas LLM."""
        if not responses:
            return ""

        # Calcular costo por provider (pueden ser mixtos: planning deepseek + files anthropic)
        total_cost = 0.0
        by_provider = {}
        for r in responses:
            cost = self._estimate_cost(r.provider, r.input_tokens, r.output_tokens)
            total_cost += cost
            if r.provider not in by_provider:
                by_provider[r.provider] = {"input": 0, "output": 0, "calls": 0}
            by_provider[r.provider]["input"] += r.input_tokens
            by_provider[r.provider]["output"] += r.output_tokens
            by_provider[r.provider]["calls"] += 1

        total_input = sum(r.input_tokens for r in responses)
        total_output = sum(r.output_tokens for r in responses)
        providers_used = list(by_provider.keys())

        data = {
            "providers": providers_used,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost_usd": round(total_cost, 6),
            "chunked_calls": len(responses),
            "by_provider": by_provider,
        }
        return f"\n\n<!-- COST_DATA: {json.dumps(data)} -->"

    def _assess_complexity(self, planned_files: List[Tuple[str, str]]) -> Tuple[str, int]:
        """
        Evaluar complejidad de la tarea y seleccionar provider + token limit.

        Criterios para usar Anthropic (complejo):
        - 3+ archivos en el plan
        - Algun archivo existente del plan tiene >200 lineas (archivo grande)

        Returns:
            (preferred_provider, file_max_tokens)
            ej: ('deepseek', 6000) o ('anthropic', 16000)
        """
        num_files = len(planned_files)

        # Criterio 1: muchos archivos
        if num_files >= WORKER_COMPLEXITY_THRESHOLD_FILES:
            logger.info(
                f"Complejidad ALTA: {num_files} archivos >= umbral "
                f"{WORKER_COMPLEXITY_THRESHOLD_FILES} -> anthropic"
            )
            return ("anthropic", WORKER_ANTHROPIC_FILE_TOKENS)

        # Criterio 2: algun archivo existente es grande
        for file_path, _ in planned_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    line_count = len(
                        full_path.read_text(encoding="utf-8", errors="replace").split("\n")
                    )
                    if line_count > WORKER_LARGE_FILE_LINES:
                        logger.info(
                            f"Complejidad ALTA: {file_path} tiene {line_count} lineas "
                            f"> umbral {WORKER_LARGE_FILE_LINES} -> anthropic"
                        )
                        return ("anthropic", WORKER_ANTHROPIC_FILE_TOKENS)
                except Exception:
                    pass

        # Simple: usar DeepSeek (barato)
        logger.info(f"Complejidad BAJA: {num_files} archivos, todos pequenos -> deepseek")
        return ("deepseek", WORKER_CHUNK_FILE_TOKENS)

    def _chunked_generate(self, orden: Dict, context: str,
                          previous_test_output: str = "") -> Tuple[List[Dict], str, list]:
        """
        Generacion chunked: planning call + per-file calls.

        Parte la generacion LLM en multiples llamadas pequenas para evitar
        el limite de output tokens de DeepSeek (8192). Cada llamada usa
        max ~6000 tokens de output.

        Args:
            orden: Documento de la orden.
            context: Contexto de archivos del scope.
            previous_test_output: Output de tests fallidos del intento anterior (para retry).

        Returns:
            (files, report, all_llm_responses)
        """
        all_responses = []

        # --- PASO 1: Planning call ---
        planning_prompt = self._load_planning_prompt()
        orden_content = orden.get("content", "")
        orden_title = orden.get("title", "Sin titulo")

        # Fix 1: incluir errores del intento anterior para que el LLM los corrija
        retry_context = ""
        if previous_test_output:
            retry_context = (
                "\n\n# ERRORES DEL INTENTO ANTERIOR (CORRIGELOS)\n\n"
                "El intento anterior genero codigo pero los tests fallaron. "
                "Aqui esta el output de los tests:\n\n"
                f"```\n{previous_test_output[-1500:]}\n```\n\n"
                "IMPORTANTE: Corrige los errores especificos de arriba. "
                "No repitas el mismo codigo que fallo.\n"
            )

        planning_user_msg = (
            f"# Orden: {orden_title}\n\n"
            f"{orden_content}\n\n"
            f"# Archivos actuales (contexto)\n\n"
            f"{context}\n"
            f"{retry_context}\n"
            "# RESPONDE con ### PLAN listando archivos necesarios"
        )

        logger.info("Chunked: enviando planning call")
        plan_response = self.llm_chain.chat(
            system=planning_prompt,
            messages=[{"role": "user", "content": planning_user_msg}],
            max_tokens=WORKER_CHUNK_PLAN_TOKENS,
        )
        all_responses.append(plan_response)
        logger.info(
            f"Chunked: planning response via {plan_response.provider}",
            tokens_in=plan_response.input_tokens,
            tokens_out=plan_response.output_tokens,
        )

        # Parsear plan: extraer lineas "- FILE: path — descripcion"
        plan_text = plan_response.text
        file_plan_pattern = re.compile(r'-\s*FILE:\s*(\S+)\s*[—\-]+\s*(.+)')
        planned_files = []
        seen_paths = set()
        for match in file_plan_pattern.finditer(plan_text):
            path = match.group(1).strip()
            desc = match.group(2).strip()
            if path not in seen_paths:
                planned_files.append((path, desc))
                seen_paths.add(path)
            else:
                logger.warning(f"Chunked: descartando archivo duplicado en plan: {path}")

        if not planned_files:
            logger.warning("Chunked: planning call no produjo archivos")
            # Extraer report si hay
            report = ""
            report_match = re.search(r'###\s*REPORT\s*\n(.*)', plan_text, re.DOTALL)
            if report_match:
                report = report_match.group(1).strip()
            return [], report, all_responses

        # Fix 2: Auto-corregir paths fuera de scope
        fixed_files = []
        for path, desc in planned_files:
            if self._is_path_in_scope(path):
                fixed_files.append((path, desc))
            else:
                fixed = self._fix_scope_path(path)
                if fixed:
                    logger.warning(f"Chunked: path corregido: {path} -> {fixed}")
                    fixed_files.append((fixed, desc))
                else:
                    logger.warning(f"Chunked: descartando path fuera de scope: {path}")
        planned_files = fixed_files

        if not planned_files:
            logger.warning("Chunked: todos los paths del plan estan fuera de scope")
            return [], "", all_responses

        # Limitar a WORKER_MAX_FILES
        if len(planned_files) > WORKER_MAX_FILES:
            logger.warning(
                f"Chunked: plan tiene {len(planned_files)} archivos, "
                f"limitando a {WORKER_MAX_FILES}"
            )
            planned_files = planned_files[:WORKER_MAX_FILES]

        logger.info(
            f"Chunked: plan con {len(planned_files)} archivos: "
            + ", ".join(p for p, _ in planned_files)
        )

        # --- PASO 1.5: Evaluar complejidad y seleccionar provider ---
        preferred_provider, file_max_tokens = self._assess_complexity(planned_files)
        logger.info(
            f"Chunked: provider seleccionado={preferred_provider}, "
            f"file_max_tokens={file_max_tokens}"
        )

        # --- PASO 2: Per-file calls ---
        generated_files = []
        for file_path, file_desc in planned_files:
            file_gen_prompt = self._load_file_gen_prompt(
                file_path, file_desc, plan_text, generated_files
            )
            file_user_msg = (
                f"# Orden: {orden_title}\n\n"
                f"{orden_content}\n\n"
                f"# Archivos actuales (contexto)\n\n"
                f"{context}\n"
                f"{retry_context}\n"
                f"# Genera SOLO el archivo: {file_path}"
            )

            logger.info(f"Chunked: generando archivo {file_path}")
            file_response = self.llm_chain.chat_with_preferred(
                preferred=preferred_provider,
                system=file_gen_prompt,
                messages=[{"role": "user", "content": file_user_msg}],
                max_tokens=file_max_tokens,
            )
            all_responses.append(file_response)
            logger.info(
                f"Chunked: {file_path} via {file_response.provider}",
                tokens_in=file_response.input_tokens,
                tokens_out=file_response.output_tokens,
            )

            # Parsear el archivo generado
            file_blocks, _ = parse_llm_file_blocks(file_response.text)
            if file_blocks:
                # Tomar el primer bloque (deberia ser el unico)
                generated_files.append(file_blocks[0])
            else:
                # Fallback: si no vino con ### FILE: wrapper, usar todo como contenido
                logger.warning(
                    f"Chunked: {file_path} no vino con ### FILE: wrapper, "
                    "usando respuesta raw"
                )
                # Intentar extraer contenido de bloque de codigo
                code_match = re.search(
                    r'```[a-zA-Z]*\s*\n(.*?)\n```',
                    file_response.text,
                    re.DOTALL,
                )
                content = code_match.group(1) if code_match else file_response.text
                generated_files.append({"path": file_path, "content": content})

        # --- PASO 3: Extraer report del plan ---
        report = ""
        report_match = re.search(r'###\s*REPORT\s*\n(.*)', plan_text, re.DOTALL)
        if report_match:
            report = report_match.group(1).strip()
            next_block = re.search(r'\n###\s', report)
            if next_block:
                report = report[:next_block.start()].strip()

        return generated_files, report, all_responses

    def execute_order(self, orden: Dict, attempt: int = 1) -> bool:
        """
        Ejecutar una orden completa: LLM -> aplicar -> tests -> reportar.

        Args:
            orden: Documento de la orden.
            attempt: Numero de intento (1-based).

        Returns:
            True si la orden se completo exitosamente.
        """
        doc_id = orden.get("id")
        title = orden.get("title", "Sin titulo")
        max_retries = WORKER_MAX_RETRIES
        logger.info(f"Ejecutando orden #{doc_id}: {title} (intento {attempt}/{max_retries + 1})")

        # 1. Marcar como in_progress
        mark_as_in_progress(doc_id, self.worker_name, message="Executor procesando")

        # 2. Leer contexto del scope (filtrado por archivos mencionados)
        context = self._read_scope_files(orden)

        # 3. Generacion chunked (planning + per-file calls)
        try:
            files, report, all_responses = self._chunked_generate(
                orden, context,
                previous_test_output=self._last_test_output if attempt > 1 else "",
            )
            total_in = sum(r.input_tokens for r in all_responses)
            total_out = sum(r.output_tokens for r in all_responses)
            logger.info(
                f"Chunked generation completa: {len(all_responses)} llamadas, "
                f"{total_in}in/{total_out}out totales",
            )
        except Exception as e:
            error_msg = f"Error LLM: {e}"
            logger.error(error_msg)
            mark_as_blocked(doc_id, self.worker_name, message=error_msg)
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"FALLO: {title[:50]}",
                content=f"# Error al consultar LLM\n\n{error_msg}"
                        f"\n\n<!-- COST_DATA: {json.dumps({'provider':'none','model':'none','input_tokens':0,'output_tokens':0,'cost_usd':0})} -->",
                tags=["error", "llm"],
            )
            return False

        # 4. Verificar que se generaron archivos
        if not files:
            logger.warning(f"LLM no genero archivos (intento {attempt})")
            cost_meta = self._cost_block_multi(all_responses)
            # Solo marcar blocked si ya no quedan reintentos
            if attempt > max_retries:
                # Mostrar respuesta del planning call para debug
                plan_text = all_responses[0].text if all_responses else "(sin respuesta)"
                mark_as_blocked(
                    doc_id, self.worker_name,
                    message=f"LLM no genero archivos tras {attempt} intentos",
                )
                self.docs_client.publish_worker_report(
                    worker_name=self.worker_name,
                    title=f"FALLO: {title[:50]} — sin archivos ({attempt} intentos)",
                    content=(
                        f"# LLM no genero archivos tras {attempt} intentos\n\n"
                        f"## Planning response\n\n```\n{plan_text[:2000]}\n```"
                        f"{cost_meta}"
                    ),
                    tags=["error", "parsing"],
                )
            return False

        # 5. Aplicar archivos
        try:
            applied = self._apply_files(files)
            logger.info(f"Archivos aplicados: {applied}")
        except ValueError as e:
            error_msg = str(e)
            logger.error(f"Error aplicando archivos: {error_msg}")
            mark_as_blocked(doc_id, self.worker_name, message=error_msg)
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"FALLO: {title[:50]} — scope/limite",
                content=f"# Error de seguridad\n\n{error_msg}",
                tags=["error", "scope"],
            )
            return False

        # 6. Ejecutar tests
        tests_passed, test_output = self._run_tests()

        cost_meta = self._cost_block_multi(all_responses)
        provider_summary = (
            f"{len(all_responses)} llamadas chunked "
            f"({total_in}in/{total_out}out)"
        )

        # Guardar output de tests para feedback en reintentos
        self._last_test_output = test_output if not tests_passed else ""

        if tests_passed:
            # 7a. Exito -> reportar completado
            report_content = (
                f"# Orden #{doc_id} completada\n\n"
                f"## Cambios\n\n"
                f"Archivos modificados: {', '.join(applied)}\n\n"
                f"## Reporte del LLM\n\n{report}\n\n"
                f"## Tests\n\n```\n{test_output[-1000:]}\n```\n\n"
                f"## Provider\n\n{provider_summary}"
                f"{cost_meta}"
            )
            mark_as_completed(
                doc_id, self.worker_name,
                message=f"Completado: {len(applied)} archivo(s) modificado(s)",
            )
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"COMPLETADO: {title[:50]}",
                content=report_content,
                tags=["completado"],
            )
            logger.info(f"Orden #{doc_id} completada exitosamente")
            return True
        else:
            # 7b. Tests fallaron -> rollback + reportar bloqueado
            logger.warning(f"Tests fallaron, haciendo rollback")
            self._rollback()

            # Solo reportar fallo + block si ya no quedan reintentos
            if attempt > max_retries:
                report_content = (
                    f"# Orden #{doc_id} fallida — tests no pasan ({attempt} intentos)\n\n"
                    f"## Archivos intentados\n\n{', '.join(applied)}\n\n"
                    f"## Output de tests\n\n```\n{test_output[-2000:]}\n```\n\n"
                    f"## Reporte del LLM\n\n{report}\n\n"
                    f"Los cambios fueron revertidos (rollback)."
                    f"{cost_meta}"
                )
                mark_as_blocked(
                    doc_id, self.worker_name,
                    message=f"Tests fallaron tras {attempt} intentos. Rollback.",
                )
                self.docs_client.publish_worker_report(
                    worker_name=self.worker_name,
                    title=f"FALLO: {title[:50]} — tests no pasan ({attempt} intentos)",
                    content=report_content,
                    tags=["fallo", "tests"],
                )
            else:
                logger.info(f"Tests fallaron intento {attempt}, reintentara")
            return False

    def _normalize_title(self, title: str) -> str:
        """Normalizar titulo para detectar duplicados."""
        import re as _re
        # Quitar numeros de orden, prefijos, y normalizar espacios
        t = _re.sub(r'(?:Orden|ORDEN)[- ](?:CORE-)?#?\d+[a-z]?:?\s*', '', title)
        t = _re.sub(r'\s+', ' ', t).strip().lower()
        return t[:60]

    def _is_duplicate(self, orden: Dict) -> bool:
        """Verificar si una orden es duplicada de una ya procesada."""
        title = orden.get("title", "")
        normalized = self._normalize_title(title)
        if normalized in self._seen_titles:
            logger.info(f"Orden #{orden.get('id')} es duplicada de titulo ya visto: {normalized[:40]}")
            return True
        return False

    def run(self) -> None:
        """Loop principal: poll pendientes y ejecutar ordenes con reintentos."""
        print(f"{'='*60}")
        print(f"  WORKER EXECUTOR — {self.worker_name}")
        print(f"  docs-service: {DOCS_SERVICE_URL}")
        print(f"  project: {self.project_root}")
        print(f"  scope: {self.scope_paths}")
        print(f"  intervalo: {self.check_interval}s")
        print(f"  reintentos: {WORKER_MAX_RETRIES}")
        print(f"  LLM providers: {self.llm_chain.available_providers}")
        print(f"{'='*60}")
        print()

        # Verificar docs-service
        health = self.docs_client.health_check()
        if not health:
            logger.error("docs-service no responde, abortando")
            return

        logger.info("docs-service activo, comenzando poll loop")

        # Reportar arranque
        self.docs_client.publish_worker_report(
            worker_name=self.worker_name,
            title=f"{self.worker_name} executor arrancado",
            content=(
                f"Executor autonomo activo.\n"
                f"Scope: {self.scope_paths}\n"
                f"Max retries: {WORKER_MAX_RETRIES}\n"
                f"Providers: {self.llm_chain.available_providers}"
            ),
            tags=["arranque", "executor"],
        )

        try:
            while True:
                pendientes = self.docs_client.get_worker_pendientes(self.worker_name)

                if pendientes:
                    # Buscar primera orden no procesada ni duplicada
                    orden = None
                    for p in pendientes:
                        doc_id = p.get("id")

                        # Skip ya completadas/permanentemente fallidas
                        if doc_id in self._processed_ids:
                            continue

                        # Skip si ya esta blocked en el servidor
                        if p.get("workflow_status") == "blocked":
                            self._processed_ids.add(doc_id)
                            continue

                        # Skip si ya esta completed en el servidor
                        if p.get("workflow_status") in ("completed", "cancelled"):
                            self._processed_ids.add(doc_id)
                            continue

                        # Dedup: skip si hay otra orden con el mismo titulo ya vista
                        if self._is_duplicate(p):
                            # Marcar como cancelled en el servidor
                            mark_as_blocked(doc_id, self.worker_name, message="Duplicada")
                            self._processed_ids.add(doc_id)
                            continue

                        orden = p
                        break

                    if orden:
                        doc_id = orden.get("id")
                        doc_full = self.docs_client.get_doc(doc_id)
                        if not doc_full:
                            logger.warning(f"No se pudo leer orden #{doc_id}")
                            self._processed_ids.add(doc_id)
                        else:
                            # Retry loop
                            attempt = self._attempts.get(doc_id, 0) + 1
                            self._attempts[doc_id] = attempt

                            success = self.execute_order(doc_full, attempt=attempt)

                            if success:
                                # Registrar titulo como visto
                                self._seen_titles.add(
                                    self._normalize_title(doc_full.get("title", ""))
                                )
                                self._processed_ids.add(doc_id)
                            elif attempt > WORKER_MAX_RETRIES:
                                # Sin mas reintentos, marcar como done
                                self._seen_titles.add(
                                    self._normalize_title(doc_full.get("title", ""))
                                )
                                self._processed_ids.add(doc_id)
                            else:
                                # Hay reintentos disponibles, esperar y reintentar
                                logger.info(
                                    f"Reintentando #{doc_id} en {WORKER_RETRY_DELAY}s "
                                    f"(intento {attempt}/{WORKER_MAX_RETRIES + 1})"
                                )
                                time.sleep(WORKER_RETRY_DELAY)
                                continue  # No esperar check_interval, reintentar ya
                    else:
                        print(".", end="", flush=True)
                else:
                    print(".", end="", flush=True)

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print(f"\n\n[STOP] Executor {self.worker_name} parado.")
            logger.info("Executor parado por usuario")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Worker Executor autonomo para IANAE"
    )
    parser.add_argument(
        "worker_name",
        choices=VALID_WORKERS,
        help=f"Nombre del worker ({', '.join(VALID_WORKERS)})",
    )
    parser.add_argument(
        "--project-root",
        default=os.path.join(os.path.dirname(__file__), "..", ".."),
        help="Raiz del proyecto IANAE (default: ../../ desde este script)",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=WORKER_CHECK_INTERVAL,
        help=f"Segundos entre polls (default: {WORKER_CHECK_INTERVAL})",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Ignorar ordenes con ID menor a este valor",
    )

    args = parser.parse_args()

    executor = WorkerExecutor(
        worker_name=args.worker_name,
        project_root=args.project_root,
        check_interval=args.check_interval,
    )

    # Pre-cargar IDs a ignorar si se pide --start-from
    if args.start_from > 0:
        logger.info(f"Ignorando ordenes con ID < {args.start_from}")
        pendientes = executor.docs_client.get_worker_pendientes(args.worker_name)
        if pendientes:
            for p in pendientes:
                pid = p.get("id", 0)
                if pid < args.start_from:
                    executor._processed_ids.add(pid)
            logger.info(f"Pre-ignoradas {len(executor._processed_ids)} ordenes antiguas")

    executor.run()


if __name__ == "__main__":
    main()
