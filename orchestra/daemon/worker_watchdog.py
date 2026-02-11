"""
Watchdog para workers de IANAE.
Corre en background en la terminal del worker.
Consulta pendientes cada 30s y muestra órdenes nuevas.

Uso:
  python worker_watchdog.py worker-core

El worker (Claude Code) ve las órdenes en la terminal y las ejecuta
SIN intervención de Lucas.
"""

import requests
import time
import sys
import os
from datetime import datetime

# Configuración
DOCS_SERVICE_URL = "http://localhost:25500"
CHECK_INTERVAL = 30  # segundos

# Workers válidos
VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]


def get_pendientes(worker_name):
    """Obtener pendientes del worker."""
    try:
        r = requests.get(
            f"{DOCS_SERVICE_URL}/api/v1/worker/{worker_name}/pendientes",
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("pendientes", [])
    except:
        return []


def get_doc_full(doc_id):
    """Obtener documento completo."""
    try:
        r = requests.get(f"{DOCS_SERVICE_URL}/api/v1/docs/{doc_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None


def main():
    if len(sys.argv) < 2:
        print("Uso: python worker_watchdog.py WORKER_NAME")
        print(f"Workers validos: {', '.join(VALID_WORKERS)}")
        return

    worker_name = sys.argv[1]
    if worker_name not in VALID_WORKERS:
        print(f"Worker no valido: {worker_name}")
        print(f"Workers validos: {', '.join(VALID_WORKERS)}")
        return

    print(f"{'='*60}")
    print(f"  WATCHDOG — {worker_name}")
    print(f"  docs-service: {DOCS_SERVICE_URL}")
    print(f"  Intervalo: {CHECK_INTERVAL}s")
    print(f"{'='*60}")
    print()

    # Verificar docs-service
    try:
        r = requests.get(f"{DOCS_SERVICE_URL}/health", timeout=5)
        print(f"[OK] docs-service activo")
    except:
        print("[ERROR] docs-service no responde")
        return

    seen_ids = set()  # IDs ya mostrados (evitar repetir)

    # Lectura inicial — marcar los que ya existen como vistos
    initial = get_pendientes(worker_name)
    for p in initial:
        seen_ids.add(p.get("id"))
    print(f"[OK] {len(initial)} pendiente(s) previo(s) (ya marcados como vistos)")
    print(f"\n[WATCHDOG] Vigilando nuevas ordenes para {worker_name}...\n")

    try:
        while True:
            pendientes = get_pendientes(worker_name)

            for p in pendientes:
                doc_id = p.get("id")
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)

                    # NUEVA ORDEN DETECTADA
                    print(f"\n{'='*60}")
                    print(f"  NUEVA ORDEN PARA {worker_name.upper()}")
                    print(f"  {datetime.now().strftime('%H:%M:%S')}")
                    print(f"{'='*60}")
                    print(f"  Titulo: {p.get('title', '?')}")
                    print(f"  ID: {doc_id}")

                    # Obtener contenido completo
                    doc = get_doc_full(doc_id)
                    if doc:
                        content = doc.get("content", "")
                        print(f"\n--- CONTENIDO ---")
                        try:
                            print(content)
                        except UnicodeEncodeError:
                            # Fallback para Windows con encoding limitado
                            print(content.encode('ascii', 'replace').decode('ascii'))
                        print(f"--- FIN CONTENIDO ---\n")

                        # Mostrar instrucción para el worker
                        print(f"[ACCION] Lee la orden anterior y ejecutala.")
                        print(f"[ACCION] Al terminar, reporta con:")
                        print(f"  python worker_report.py {worker_name} \"Titulo del reporte\" reporte.md")
                        print()

                    else:
                        print(f"  (No se pudo leer contenido completo)")
                        print(f"  Lee con: curl {DOCS_SERVICE_URL}/api/v1/docs/{doc_id}")
                        print()

            # Punto silencioso
            print(".", end="", flush=True)
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n[STOP] Watchdog {worker_name} parado.")


if __name__ == "__main__":
    main()
