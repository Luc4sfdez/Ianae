"""
Endpoint de notificaciones para el daemon.
GET /api/v1/notifications/since?t={iso_timestamp}
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from ...database import get_connection

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/since")
async def get_docs_since(t: str = Query(..., description="ISO timestamp")):
    """Documentos nuevos o modificados desde el timestamp dado."""
    try:
        # Validar formato
        since = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"Timestamp inválido: {t}")

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT * FROM documents
            WHERE (created_at > ? OR updated_at > ?)
            AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            (t, t)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return {"results": results, "since": t, "count": len(results)}
    finally:
        conn.close()
