"""
Helper para publicar reportes de worker.
Uso:
  python worker_report.py worker-core "Titulo" archivo.md
  echo "contenido" | python worker_report.py worker-core "Titulo"
  python worker_report.py worker-core "DUDA: mi pregunta" --duda
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient
from config import DOCS_SERVICE_URL
from workflow_status import mark_as_completed


def main():
    if len(sys.argv) < 3:
        print("Uso: python worker_report.py WORKER TITULO [archivo.md] [--duda]")
        return

    worker_name = sys.argv[1]
    titulo = sys.argv[2]

    # Detectar flag --duda
    is_duda = "--duda" in sys.argv
    args = [a for a in sys.argv[3:] if a != "--duda"]

    if args:
        contenido = open(args[0], encoding="utf-8").read()
    else:
        contenido = sys.stdin.read()

    tags = ["duda"] if is_duda else []

    client = DocsClient(DOCS_SERVICE_URL)
    result = client.publish_worker_report(
        worker_name=worker_name,
        title=titulo,
        content=contenido,
        tags=tags,
    )

    if result:
        tipo = "DUDA" if is_duda else "REPORTE"
        doc_id = result.get('id', '?')
        print(f"[OK] {tipo} publicado: {doc_id}")

        # Auto-marcar como completed (reportes, no dudas)
        if not is_duda and isinstance(doc_id, int):
            mark_as_completed(doc_id, worker_name, message=f"Reporte {titulo} publicado")
            print(f"[OK] workflow_status: completed")
    else:
        print("[ERROR] No se pudo publicar")


if __name__ == "__main__":
    main()
