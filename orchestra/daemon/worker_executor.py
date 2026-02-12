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
    WORKER_SCOPES,
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

        # IDs de ordenes ya procesadas (evita loop infinito)
        self._processed_ids: set = set()

        logger.info(
            f"WorkerExecutor inicializado",
            worker=worker_name,
            project_root=str(self.project_root),
            scope=self.scope_paths,
            test_cmd=self.test_cmd,
            providers=self.llm_chain.available_providers,
        )

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

                    # Filtrar: solo archivos mencionados o principales (no tests)
                    if mentioned_files:
                        is_mentioned = any(m in rel or rel.endswith(m) for m in mentioned_files)
                        if not is_mentioned:
                            continue
                    else:
                        if "test" in rel.lower() or rel.endswith("__init__.py"):
                            continue

                    try:
                        content = py_file.read_text(encoding="utf-8", errors="replace")
                        lines = content.split("\n")

                        if len(lines) > MAX_FULL_LINES:
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

    def execute_order(self, orden: Dict) -> bool:
        """
        Ejecutar una orden completa: LLM -> aplicar -> tests -> reportar.

        Returns:
            True si la orden se completo exitosamente.
        """
        doc_id = orden.get("id")
        title = orden.get("title", "Sin titulo")
        logger.info(f"Ejecutando orden #{doc_id}: {title}")

        # 1. Marcar como in_progress
        mark_as_in_progress(doc_id, self.worker_name, message="Executor procesando")

        # 2. Leer contexto del scope (filtrado por archivos mencionados)
        context = self._read_scope_files(orden)

        # 3. Llamar al LLM
        try:
            messages = self._build_llm_messages(orden, context)
            llm_response = self.llm_chain.chat(
                system=self.system_prompt,
                messages=messages,
                max_tokens=WORKER_MAX_TOKENS,
            )
            logger.info(
                f"LLM respondio via {llm_response.provider}",
                tokens_in=llm_response.input_tokens,
                tokens_out=llm_response.output_tokens,
            )
        except Exception as e:
            error_msg = f"Error LLM: {e}"
            logger.error(error_msg)
            mark_as_blocked(doc_id, self.worker_name, message=error_msg)
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"FALLO: {title[:50]}",
                content=f"# Error al consultar LLM\n\n{error_msg}",
                tags=["error", "llm"],
            )
            return False

        # 4. Parsear respuesta
        files, report = parse_llm_file_blocks(llm_response.text)

        if not files:
            logger.warning("LLM no genero archivos")
            mark_as_blocked(
                doc_id, self.worker_name,
                message="LLM no genero bloques de archivo validos",
            )
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"FALLO: {title[:50]} — sin archivos",
                content=(
                    f"# LLM no genero archivos\n\n"
                    f"## Respuesta raw\n\n```\n{llm_response.text[:2000]}\n```"
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

        if tests_passed:
            # 7a. Exito -> reportar completado
            report_content = (
                f"# Orden #{doc_id} completada\n\n"
                f"## Cambios\n\n"
                f"Archivos modificados: {', '.join(applied)}\n\n"
                f"## Reporte del LLM\n\n{report}\n\n"
                f"## Tests\n\n```\n{test_output[-1000:]}\n```\n\n"
                f"## Provider\n\n{llm_response.provider} "
                f"({llm_response.input_tokens}in/{llm_response.output_tokens}out)"
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

            report_content = (
                f"# Orden #{doc_id} fallida — tests no pasan\n\n"
                f"## Archivos intentados\n\n{', '.join(applied)}\n\n"
                f"## Output de tests\n\n```\n{test_output[-2000:]}\n```\n\n"
                f"## Reporte del LLM\n\n{report}\n\n"
                f"Los cambios fueron revertidos (rollback)."
            )
            mark_as_blocked(
                doc_id, self.worker_name,
                message=f"Tests fallaron. Rollback aplicado.",
            )
            self.docs_client.publish_worker_report(
                worker_name=self.worker_name,
                title=f"FALLO: {title[:50]} — tests no pasan",
                content=report_content,
                tags=["fallo", "tests"],
            )
            return False

    def run(self) -> None:
        """Loop principal: poll pendientes y ejecutar ordenes."""
        print(f"{'='*60}")
        print(f"  WORKER EXECUTOR — {self.worker_name}")
        print(f"  docs-service: {DOCS_SERVICE_URL}")
        print(f"  project: {self.project_root}")
        print(f"  scope: {self.scope_paths}")
        print(f"  intervalo: {self.check_interval}s")
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
            content=f"Executor autonomo activo. Scope: {self.scope_paths}",
            tags=["arranque", "executor"],
        )

        try:
            while True:
                pendientes = self.docs_client.get_worker_pendientes(self.worker_name)

                if pendientes:
                    # Buscar primera orden no procesada
                    orden = None
                    for p in pendientes:
                        if p.get("id") not in self._processed_ids:
                            orden = p
                            break

                    if orden:
                        doc_id = orden.get("id")
                        doc_full = self.docs_client.get_doc(doc_id)
                        if doc_full:
                            self.execute_order(doc_full)
                            self._processed_ids.add(doc_id)
                        else:
                            logger.warning(f"No se pudo leer orden #{doc_id}")
                            self._processed_ids.add(doc_id)
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
