"""
Endpoint de snapshot para el daemon.
GET /api/v1/context/snapshot
"""

from fastapi import APIRouter
from ...database import get_connection

router = APIRouter(prefix="/api/v1/context", tags=["context"])

VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]


@router.get("/snapshot")
async def get_snapshot():
    """Estado compacto del proyecto para el Arquitecto IA."""
    conn = get_connection()
    try:
        # Último doc por categoría
        categories = {}
        for row in conn.execute(
            "SELECT category, title, author, created_at FROM documents "
            "WHERE deleted_at IS NULL "
            "GROUP BY category "
            "HAVING created_at = MAX(created_at)"
        ):
            r = dict(row)
            categories[r["category"]] = r

        # Pendientes por worker
        pendientes = {}
        for worker in VALID_WORKERS:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM documents "
                "WHERE status = 'pending' AND tags LIKE ? AND deleted_at IS NULL",
                (f"%{worker}%",)
            )
            pendientes[worker] = cursor.fetchone()["count"]

        # Total docs
        total = conn.execute(
            "SELECT COUNT(*) as count FROM documents WHERE deleted_at IS NULL"
        ).fetchone()["count"]

        # Docs de alta prioridad sin resolver
        alertas_cursor = conn.execute(
            "SELECT id, title, author, created_at FROM documents "
            "WHERE priority = 'alta' AND status != 'done' AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 10"
        )
        alertas = [dict(row) for row in alertas_cursor.fetchall()]

        return {
            "ultimo_doc_por_categoria": categories,
            "pendientes_por_worker": pendientes,
            "total_docs": total,
            "alertas": alertas,
            "workers_validos": VALID_WORKERS,
        }
    finally:
        conn.close()
