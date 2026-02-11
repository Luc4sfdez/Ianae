"""
Bootstrap de worker. Ejecutar al arrancar.
Uso: python worker_bootstrap.py worker-core
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient
from config import DOCS_SERVICE_URL, VALID_WORKERS


def main():
    worker_name = sys.argv[1] if len(sys.argv) > 1 else "worker-general"

    if worker_name not in VALID_WORKERS:
        print(f"[ERROR] Worker no valido: {worker_name}")
        print(f"Validos: {', '.join(VALID_WORKERS)}")
        return

    print(f"[BOOTSTRAP] {worker_name} arrancando...")

    client = DocsClient(DOCS_SERVICE_URL)
    health = client.health_check()
    if not health:
        print("[ERROR] docs-service no responde")
        return

    pendientes = client.get_worker_pendientes(worker_name)

    if pendientes:
        print(f"\n[PENDIENTES] {len(pendientes)} tarea(s):\n")
        for p in pendientes:
            print(f"  [{p.get('priority', '?')}] {p.get('title', '?')}")
            print(f"  ID: {p.get('id', '?')}")
            print()
    else:
        print("\n[OK] Sin tareas pendientes.")

    client.publish_worker_report(
        worker_name=worker_name,
        title=f"{worker_name} arrancado",
        content=f"Worker activo. Pendientes: {len(pendientes)}",
        tags=["arranque"],
    )
    print(f"[OK] Arranque reportado.")
    print(f"\n[SIGUIENTE] Arranca el watchdog en otra terminal:")
    print(f"  python worker_watchdog.py {worker_name}")


if __name__ == "__main__":
    main()
