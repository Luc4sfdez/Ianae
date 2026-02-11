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

        logger.info(
            f"WorkerExecutor inicializado",
            worker=worker_name,
            project_root=str(self.project_root),
            scope=self.scope_paths,
            test_cmd=self.test_cmd,
            providers=self.llm_chain.available_providers,
        )

    def _load_system_prompt(self) -> str:
        """Cargar system prompt del worker desde prompts/."""
        # Mapear worker-core -> worker_core.md
        prompt_name = self.worker_name.replace("-", "_")
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", f"{prompt_name}.md"
        )
        try:
            with open(prompt_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt no encontrado: {prompt_path}, usando default")
            return (
                f"Eres {self.worker_name} de IANAE. "
                f"Tu scope es: {', '.join(self.scope_paths)}. "
                f"Responde con bloques ### FILE: path y ### REPORT."
            )

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

    def _read_scope_files(self) -> str:
        """Leer archivos del scope para dar contexto al LLM."""
        context_parts = []
        for scope_path in self.scope_paths:
            full_path = self.project_root / scope_path
            if full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    context_parts.append(
                        f"### FILE: {scope_path}\n```\n{content}\n```"
                    )
                except Exception as e:
                    logger.warning(f"No se pudo leer {scope_path}: {e}")
            elif full_path.is_dir():
                # Leer archivos .py del directorio (no recursivo profundo)
                for py_file in sorted(full_path.rglob("*.py")):
                    rel = py_file.relative_to(self.project_root)
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        context_parts.append(
                            f"### FILE: {rel}\n```python\n{content}\n```"
                        )
                    except Exception as e:
                        logger.warning(f"No se pudo leer {rel}: {e}")

        return "\n\n".join(context_parts)

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

            # Escribir archivo
            full_path.write_text(f["content"], encoding="utf-8")
            applied.append(f["path"])
            logger.info(f"Archivo escrito: {f['path']}")

        return applied

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
        instruction = (
            "Responde SOLO con bloques de archivo y un reporte. Formato:\n\n"
            "### FILE: ruta/al/archivo.py\n"
            "```python\n"
            "# contenido completo del archivo\n"
            "```\n\n"
            "### REPORT\n"
            "Descripcion de los cambios realizados.\n\n"
            "REGLAS:\n"
            "- Incluye el contenido COMPLETO de cada archivo (no fragmentos)\n"
            "- Solo modifica archivos dentro de tu scope\n"
            f"- Maximo {WORKER_MAX_FILES} archivos por respuesta\n"
            "- Asegurate de que el codigo pase los tests existentes\n"
        )

        orden_content = orden.get("content", "")
        orden_title = orden.get("title", "Sin titulo")

        user_message = (
            f"# Orden: {orden_title}\n\n"
            f"{orden_content}\n\n"
            f"# Archivos actuales del scope\n\n"
            f"{context}\n\n"
            f"# Instrucciones de formato\n\n"
            f"{instruction}"
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

        # 2. Leer contexto del scope
        context = self._read_scope_files()

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
                    # Tomar la primera orden pendiente
                    orden = pendientes[0]
                    doc_id = orden.get("id")

                    # Obtener documento completo
                    doc_full = self.docs_client.get_doc(doc_id)
                    if doc_full:
                        self.execute_order(doc_full)
                    else:
                        logger.warning(f"No se pudo leer orden #{doc_id}")
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

    args = parser.parse_args()

    executor = WorkerExecutor(
        worker_name=args.worker_name,
        project_root=args.project_root,
        check_interval=args.check_interval,
    )
    executor.run()


if __name__ == "__main__":
    main()
