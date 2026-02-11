"""
Helper para actualizar workflow_status de documentos.
Uso desde workers para reportar progreso.
"""

import requests
import sys

DOCS_SERVICE_URL = "http://localhost:25500"


def update_status(doc_id, status, worker=None, progress=None, message=None):
    """
    Actualizar workflow_status de un documento.

    Args:
        doc_id (int): ID del documento
        status (str): Nuevo estado (pending/in_progress/completed/blocked/cancelled)
        worker (str, optional): Nombre del worker
        progress (float, optional): Progreso 0.0-1.0
        message (str, optional): Mensaje descriptivo

    Returns:
        dict: Respuesta de la API

    Ejemplo:
        update_status(5, "in_progress", worker="worker-core", progress=0.5)
    """
    payload = {"workflow_status": status}

    if worker:
        payload["worker"] = worker
    if progress is not None:
        payload["progress"] = progress
    if message:
        payload["message"] = message

    try:
        response = requests.put(
            f"{DOCS_SERVICE_URL}/api/v1/docs/{doc_id}/workflow-status",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] No se pudo actualizar workflow_status: {e}")
        return None


def mark_as_in_progress(doc_id, worker, message=None):
    """Marcar documento como en progreso."""
    return update_status(doc_id, "in_progress", worker=worker, message=message or f"{worker} comenzó a trabajar")


def mark_as_completed(doc_id, worker, message=None):
    """Marcar documento como completado."""
    return update_status(doc_id, "completed", worker=worker, message=message or f"{worker} completó la tarea")


def mark_as_blocked(doc_id, worker, message):
    """Marcar documento como bloqueado."""
    return update_status(doc_id, "blocked", worker=worker, message=message)


def report_progress(doc_id, worker, progress, message=None):
    """Reportar progreso parcial (0.0 a 1.0)."""
    return update_status(
        doc_id,
        "in_progress",
        worker=worker,
        progress=progress,
        message=message or f"Progreso: {int(progress*100)}%"
    )


# CLI para uso directo
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python workflow_status.py <doc_id> <status> <worker> [mensaje]")
        print("Ejemplo: python workflow_status.py 5 in_progress worker-core 'Analizando codigo...'")
        sys.exit(1)

    doc_id = int(sys.argv[1])
    status = sys.argv[2]
    worker = sys.argv[3]
    message = sys.argv[4] if len(sys.argv) > 4 else None

    result = update_status(doc_id, status, worker, message=message)

    if result:
        print(f"[OK] Documento {doc_id} actualizado a '{status}'")
    else:
        print(f"[ERROR] No se pudo actualizar documento {doc_id}")
        sys.exit(1)
