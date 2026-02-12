"""
docs-service para IANAE - Puerto 25500
Sistema de documentación y comunicación entre workers y daemon.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import json
import re

from .database import init_db, get_connection
from .api.v1.notifications import router as notifications_router
from .api.v1.snapshot import router as snapshot_router


# Inicializar DB
init_db()

# App
app = FastAPI(title="docs-service IANAE", version="1.0.0")

# CORS para acceso desde web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio de archivos estáticos
STATIC_DIR = Path(__file__).parent / "static"

# Registrar routers
app.include_router(notifications_router)
app.include_router(snapshot_router)


# Modelos
class DocCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    author: str
    tags: List[str] = []
    priority: str = "media"
    status: str = "pending"


class WorkerReport(BaseModel):
    title: str
    content: str
    tags: List[str] = []


# Endpoints básicos
@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "docs-service-ianae", "port": 25500}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "docs-service IANAE",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/api/v1/docs",
            "search": "/api/v1/search",
            "notifications": "/api/v1/notifications/since?t={timestamp}",
            "snapshot": "/api/v1/context/snapshot",
            "worker_pendientes": "/api/v1/worker/{name}/pendientes",
            "worker_reporte": "POST /api/v1/worker/{name}/reporte"
        }
    }


@app.get("/api/v1/docs")
async def list_docs(limit: int = 50, category: Optional[str] = None):
    """Listar documentos."""
    conn = get_connection()
    try:
        if category:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE category = ? AND deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (category, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        docs = [dict(row) for row in cursor.fetchall()]
        return {"docs": docs, "count": len(docs)}
    finally:
        conn.close()


@app.post("/api/v1/docs")
async def create_doc(doc: DocCreate):
    """Crear documento. Detecta duplicados por titulo+categoria en ultimas 24h."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(doc.tags) if isinstance(doc.tags, list) else doc.tags

        # Anti-duplicado: buscar doc con mismo titulo+categoria en las ultimas 24h
        if doc.category == "especificaciones":
            # Normalizar titulo para comparar (quitar numeros de orden)
            norm_title = re.sub(r'(?:Orden|ORDEN)[- ](?:CORE-)?#?\d+[a-z]?:?\s*', '', doc.title).strip()
            cursor = conn.execute(
                """
                SELECT id, title, workflow_status FROM documents
                WHERE category = ? AND deleted_at IS NULL
                AND datetime(created_at) > datetime('now', '-24 hours')
                ORDER BY created_at DESC LIMIT 50
                """,
                (doc.category,)
            )
            recent = [dict(row) for row in cursor.fetchall()]
            for existing in recent:
                existing_norm = re.sub(r'(?:Orden|ORDEN)[- ](?:CORE-)?#?\d+[a-z]?:?\s*', '', existing["title"]).strip()
                if existing_norm.lower()[:60] == norm_title.lower()[:60]:
                    # Duplicado detectado, retornar el existente
                    print(f"[DEDUP] Orden duplicada detectada: '{doc.title[:50]}' = #{existing['id']}")
                    cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (existing["id"],))
                    return dict(cursor.fetchone())

        cursor = conn.execute(
            """
            INSERT INTO documents (title, content, category, author, tags, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc.title, doc.content, doc.category, doc.author, tags_json, doc.priority, doc.status, now, now)
        )
        conn.commit()
        doc_id = cursor.lastrowid

        # Leer documento creado
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        created = dict(cursor.fetchone())
        return created
    finally:
        conn.close()


@app.get("/api/v1/docs/{doc_id}")
async def get_doc(doc_id: int):
    """Obtener documento por ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND deleted_at IS NULL",
            (doc_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Documento no encontrado")
        return dict(row)
    finally:
        conn.close()


@app.put("/api/v1/docs/{doc_id}")
async def update_doc(doc_id: int, updates: dict):
    """Actualizar documento."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()

        # Construir SET dinámicamente
        fields = []
        values = []
        for key, value in updates.items():
            if key not in ["id", "created_at"]:
                fields.append(f"{key} = ?")
                values.append(value)

        fields.append("updated_at = ?")
        values.append(now)
        values.append(doc_id)

        query = f"UPDATE documents SET {', '.join(fields)} WHERE id = ?"
        conn.execute(query, values)
        conn.commit()

        # Retornar actualizado
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()


@app.get("/api/v1/search")
async def search_docs(q: str, limit: int = 20):
    """Búsqueda FTS5."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT d.* FROM documents d
            JOIN documents_fts fts ON d.id = fts.rowid
            WHERE documents_fts MATCH ?
            AND d.deleted_at IS NULL
            ORDER BY rank LIMIT ?
            """,
            (q, limit)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return {"results": results, "count": len(results), "query": q}
    finally:
        conn.close()


@app.put("/api/v1/docs/{doc_id}/workflow-status")
async def update_workflow_status(doc_id: int, status_update: dict):
    """
    Actualizar workflow_status de un documento.

    Body: {
        "workflow_status": "pending" | "in_progress" | "completed" | "blocked" | "cancelled",
        "worker": "worker-name" (opcional),
        "progress": 0.0-1.0 (opcional),
        "message": "mensaje descriptivo" (opcional)
    }
    """
    # Validar estados permitidos
    VALID_STATUSES = ["pending", "in_progress", "completed", "blocked", "cancelled"]

    new_status = status_update.get("workflow_status")
    if not new_status:
        raise HTTPException(400, "Campo 'workflow_status' requerido")

    if new_status not in VALID_STATUSES:
        raise HTTPException(400, f"Estado inválido. Usar: {', '.join(VALID_STATUSES)}")

    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()

        # Verificar que documento existe
        cursor = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND deleted_at IS NULL",
            (doc_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(404, "Documento no encontrado")

        # Actualizar workflow_status
        conn.execute(
            """
            UPDATE documents
            SET workflow_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, now, doc_id)
        )
        conn.commit()

        # Retornar documento actualizado
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        updated_doc = dict(cursor.fetchone())

        # Log para tracking (opcional)
        worker = status_update.get("worker", "unknown")
        message = status_update.get("message", "")
        print(f"[WORKFLOW] Doc {doc_id}: {new_status} (by {worker}) - {message}")

        return {
            "success": True,
            "doc_id": doc_id,
            "workflow_status": new_status,
            "updated_at": now,
            "document": updated_doc
        }
    finally:
        conn.close()


@app.get("/api/v1/worker/{worker_name}/pendientes")
async def get_worker_pendientes(worker_name: str):
    """Obtener pendientes de un worker."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT * FROM documents
            WHERE status = 'pending'
            AND tags LIKE ?
            AND deleted_at IS NULL
            ORDER BY priority DESC, created_at ASC
            """,
            (f"%{worker_name}%",)
        )
        pendientes = [dict(row) for row in cursor.fetchall()]
        return {"pendientes": pendientes, "count": len(pendientes), "worker": worker_name}
    finally:
        conn.close()


@app.post("/api/v1/worker/{worker_name}/reporte")
async def post_worker_report(worker_name: str, report: WorkerReport):
    """Publicar reporte de un worker."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps([worker_name, "reporte"] + report.tags)

        cursor = conn.execute(
            """
            INSERT INTO documents (title, content, category, author, tags, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (report.title, report.content, "reportes", worker_name, tags_json, "media", "done", now, now)
        )
        conn.commit()
        doc_id = cursor.lastrowid

        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()


@app.get("/api/v1/metrics/system")
async def get_system_metrics():
    """
    Métricas completas del sistema: daemon, workers, calidad.
    """
    conn = get_connection()
    try:
        # Obtener todos los documentos
        cursor = conn.execute(
            "SELECT * FROM documents WHERE deleted_at IS NULL ORDER BY created_at DESC"
        )
        all_docs = [dict(row) for row in cursor.fetchall()]

        # === MÉTRICAS DEL DAEMON ===
        daemon_metrics = {
            "ordenes_publicadas": len([d for d in all_docs if d.get("category") == "especificaciones" and "orden" in d.get("title", "").lower()]),
            "dudas_resueltas": len([d for d in all_docs if "duda" in str(d.get("tags", ""))]),
            "escalados": len([d for d in all_docs if "escalado" in d.get("title", "").lower()]),
            "respuestas_publicadas": len([d for d in all_docs if d.get("title", "").startswith("RESPUESTA")]),
        }

        # === MÉTRICAS POR WORKER ===
        workers = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]
        workers_metrics = {}

        for worker in workers:
            worker_docs = [d for d in all_docs if worker in str(d.get("tags", "")) or d.get("author") == worker]

            ordenes = [d for d in worker_docs if d.get("category") == "especificaciones"]
            reportes = [d for d in worker_docs if d.get("category") == "reportes"]
            completados = [d for d in worker_docs if d.get("workflow_status") == "completed"]

            # Calcular tiempo promedio (simplificado)
            tiempos = []
            for reporte in reportes:
                created = reporte.get("created_at", "")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
                        delta = (now - dt).total_seconds()
                        if delta > 0 and delta < 86400:  # Máx 24h
                            tiempos.append(delta)
                    except:
                        pass

            tiempo_promedio = int(sum(tiempos) / len(tiempos)) if tiempos else 0

            workers_metrics[worker] = {
                "ordenes_recibidas": len(ordenes),
                "reportes_publicados": len(reportes),
                "tareas_completadas": len(completados),
                "dudas_publicadas": len([d for d in worker_docs if "duda" in str(d.get("tags", ""))]),
                "tiempo_promedio_tarea": tiempo_promedio,
                "ultima_actividad": worker_docs[0].get("created_at") if worker_docs else None
            }

        # === MÉTRICAS DE CALIDAD ===
        total_ordenes = len([d for d in all_docs if d.get("category") == "especificaciones"])
        total_reportes = len([d for d in all_docs if d.get("category") == "reportes"])
        total_completados = len([d for d in all_docs if d.get("workflow_status") == "completed"])
        total_bloqueados = len([d for d in all_docs if d.get("workflow_status") == "blocked"])
        total_escalados = daemon_metrics["escalados"]

        efectividad = (total_reportes / total_ordenes * 100) if total_ordenes > 0 else 0
        autonomia = ((total_ordenes - total_escalados) / total_ordenes * 100) if total_ordenes > 0 else 0
        tasa_completacion = (total_completados / (total_ordenes + total_reportes) * 100) if (total_ordenes + total_reportes) > 0 else 0

        quality_metrics = {
            "efectividad_daemon": round(efectividad, 2),
            "autonomia_real": round(autonomia, 2),
            "tasa_completacion": round(tasa_completacion, 2),
            "total_ordenes": total_ordenes,
            "total_reportes": total_reportes,
            "total_completados": total_completados,
            "total_bloqueados": total_bloqueados,
            "total_escalados": total_escalados,
        }

        # === MÉTRICAS POR CATEGORÍA ===
        categorias = {}
        for doc in all_docs:
            cat = doc.get("category", "unknown")
            categorias[cat] = categorias.get(cat, 0) + 1

        # === MÉTRICAS POR ESTADO ===
        estados = {}
        for doc in all_docs:
            status = doc.get("workflow_status") or doc.get("status", "unknown")
            estados[status] = estados.get(status, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "daemon": daemon_metrics,
            "workers": workers_metrics,
            "quality": quality_metrics,
            "categorias": categorias,
            "estados": estados,
            "total_documentos": len(all_docs)
        }

    finally:
        conn.close()


@app.get("/api/v1/alerts")
async def get_system_alerts():
    """
    Detectar anomalías y problemas en el sistema.

    Retorna lista de alertas con:
    - level: "warning" | "error" | "critical"
    - type: tipo de alerta
    - message: descripción
    - timestamp: cuándo se detectó
    - details: información adicional
    """
    conn = get_connection()
    try:
        alerts = []
        now = datetime.now()

        # Obtener todos los documentos
        cursor = conn.execute(
            "SELECT * FROM documents WHERE deleted_at IS NULL ORDER BY created_at DESC"
        )
        all_docs = [dict(row) for row in cursor.fetchall()]

        # === ALERTA 1: Workers inactivos > 15 minutos ===
        workers = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]
        for worker in workers:
            worker_docs = [d for d in all_docs if worker in str(d.get("tags", "")) or d.get("author") == worker]

            if not worker_docs:
                # Worker nunca ha tenido actividad
                alerts.append({
                    "level": "warning",
                    "type": "worker_never_active",
                    "message": f"{worker}: Sin actividad registrada",
                    "timestamp": now.isoformat(),
                    "details": {"worker": worker}
                })
                continue

            # Encontrar última actividad
            last_doc = worker_docs[0]
            last_activity_str = last_doc.get("created_at")
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str.replace("Z", "+00:00"))
                    if last_activity.tzinfo:
                        now_tz = datetime.now(last_activity.tzinfo)
                    else:
                        now_tz = now
                    minutes_since = (now_tz - last_activity).total_seconds() / 60

                    if minutes_since > 15:
                        level = "error" if minutes_since > 60 else "warning"
                        alerts.append({
                            "level": level,
                            "type": "worker_inactive",
                            "message": f"{worker}: Sin actividad hace {int(minutes_since)} minutos",
                            "timestamp": now.isoformat(),
                            "details": {
                                "worker": worker,
                                "minutes_inactive": int(minutes_since),
                                "last_activity": last_activity_str
                            }
                        })
                except Exception:
                    pass

        # === ALERTA 2: Tareas bloqueadas > 1 hora ===
        blocked_docs = [d for d in all_docs if d.get("workflow_status") == "blocked"]
        for doc in blocked_docs:
            created_at_str = doc.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if created_at.tzinfo:
                        now_tz = datetime.now(created_at.tzinfo)
                    else:
                        now_tz = now
                    hours_blocked = (now_tz - created_at).total_seconds() / 3600

                    if hours_blocked > 1:
                        level = "critical" if hours_blocked > 24 else "error"
                        alerts.append({
                            "level": level,
                            "type": "task_blocked",
                            "message": f"Tarea bloqueada hace {int(hours_blocked)} horas: {doc.get('title', 'Sin título')[:50]}",
                            "timestamp": now.isoformat(),
                            "details": {
                                "doc_id": doc.get("id"),
                                "title": doc.get("title"),
                                "hours_blocked": round(hours_blocked, 1),
                                "created_at": created_at_str
                            }
                        })
                except Exception:
                    pass

        # === ALERTA 3: Tareas pendientes muy antiguas (> 24h) ===
        pending_docs = [d for d in all_docs if d.get("workflow_status") == "pending" or d.get("status") == "pending"]
        for doc in pending_docs:
            created_at_str = doc.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if created_at.tzinfo:
                        now_tz = datetime.now(created_at.tzinfo)
                    else:
                        now_tz = now
                    hours_pending = (now_tz - created_at).total_seconds() / 3600

                    if hours_pending > 24:
                        alerts.append({
                            "level": "warning",
                            "type": "task_stale",
                            "message": f"Tarea pendiente hace {int(hours_pending)} horas: {doc.get('title', 'Sin título')[:50]}",
                            "timestamp": now.isoformat(),
                            "details": {
                                "doc_id": doc.get("id"),
                                "title": doc.get("title"),
                                "hours_pending": round(hours_pending, 1),
                                "created_at": created_at_str
                            }
                        })
                except Exception:
                    pass

        # === ALERTA 4: Demasiadas dudas sin resolver ===
        dudas = [d for d in all_docs if "duda" in str(d.get("tags", "")).lower() and d.get("workflow_status") != "completed"]
        if len(dudas) > 3:
            alerts.append({
                "level": "warning",
                "type": "many_unresolved_questions",
                "message": f"{len(dudas)} dudas sin resolver en el sistema",
                "timestamp": now.isoformat(),
                "details": {
                    "count": len(dudas),
                    "dudas": [{"id": d.get("id"), "title": d.get("title")} for d in dudas[:5]]
                }
            })

        # Ordenar por nivel (critical > error > warning)
        level_priority = {"critical": 0, "error": 1, "warning": 2}
        alerts.sort(key=lambda a: level_priority.get(a["level"], 3))

        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": now.isoformat(),
            "has_critical": any(a["level"] == "critical" for a in alerts),
            "has_error": any(a["level"] == "error" for a in alerts)
        }

    finally:
        conn.close()


@app.get("/api/v1/metrics/costs")
async def get_cost_metrics():
    """
    Metricas de costos LLM extraidas de reportes de workers.
    Parsea bloques <!-- COST_DATA: {...} --> y tambien el formato legacy
    "Provider\\n\\nprovider (Xin/Yout)".
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM documents WHERE category = 'reportes' AND deleted_at IS NULL ORDER BY created_at DESC"
        )
        reports = [dict(row) for row in cursor.fetchall()]

        # Cost rates per 1M tokens
        RATES = {
            "deepseek": {"input": 0.27, "output": 1.10},
            "qwen": {"input": 0.80, "output": 2.00},
            "anthropic": {"input": 3.00, "output": 15.00},
        }

        calls = []
        total_cost = 0.0
        by_provider = {}
        total_input_tokens = 0
        total_output_tokens = 0

        for report in reports:
            content = report.get("content", "")
            cost_data = None

            # Try structured format first
            m = re.search(r'<!-- COST_DATA: ({.*?}) -->', content)
            if m:
                try:
                    cost_data = json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass

            # Fallback: parse legacy format "## Provider\n\nprovider (Xin/Yout)"
            if not cost_data:
                m2 = re.search(r'## Provider\s*\n\s*(\w+)\s*\((\d+)in/(\d+)out\)', content)
                if m2:
                    provider = m2.group(1)
                    inp = int(m2.group(2))
                    outp = int(m2.group(3))
                    rates = RATES.get(provider, {"input": 3.0, "output": 15.0})
                    cost = (inp * rates["input"] + outp * rates["output"]) / 1_000_000
                    cost_data = {
                        "provider": provider,
                        "model": "unknown",
                        "input_tokens": inp,
                        "output_tokens": outp,
                        "cost_usd": round(cost, 6),
                    }

            if cost_data and cost_data.get("provider") != "none":
                # Extract files from report
                files_modified = []
                fm = re.search(r'Archivos (?:modificados|intentados):\s*(.+?)(?:\n|$)', content)
                if fm:
                    files_modified = [f.strip() for f in fm.group(1).split(",") if f.strip()]

                is_success = "COMPLETADO" in report.get("title", "")
                call_info = {
                    "doc_id": report.get("id"),
                    "order_title": report.get("title", ""),
                    "timestamp": report.get("created_at"),
                    "provider": cost_data.get("provider", "unknown"),
                    "model": cost_data.get("model", "unknown"),
                    "input_tokens": cost_data.get("input_tokens", 0),
                    "output_tokens": cost_data.get("output_tokens", 0),
                    "cost_usd": cost_data.get("cost_usd", 0),
                    "success": is_success,
                    "files": files_modified,
                }
                calls.append(call_info)

                cost_val = cost_data.get("cost_usd", 0)
                total_cost += cost_val
                total_input_tokens += cost_data.get("input_tokens", 0)
                total_output_tokens += cost_data.get("output_tokens", 0)

                prov = cost_data.get("provider", "unknown")
                if prov not in by_provider:
                    by_provider[prov] = {"calls": 0, "cost_usd": 0, "input_tokens": 0, "output_tokens": 0}
                by_provider[prov]["calls"] += 1
                by_provider[prov]["cost_usd"] = round(by_provider[prov]["cost_usd"] + cost_val, 6)
                by_provider[prov]["input_tokens"] += cost_data.get("input_tokens", 0)
                by_provider[prov]["output_tokens"] += cost_data.get("output_tokens", 0)

        successes = sum(1 for c in calls if c["success"])
        failures = sum(1 for c in calls if not c["success"])

        return {
            "total_cost_usd": round(total_cost, 4),
            "total_calls": len(calls),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / len(calls) * 100, 1) if calls else 0,
            "by_provider": by_provider,
            "calls": calls,
            "rates_per_1m": RATES,
        }
    finally:
        conn.close()


@app.get("/api/v1/metrics/code")
async def get_code_metrics():
    """
    Metricas de codigo real generado: archivos creados/modificados exitosamente.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM documents WHERE category = 'reportes' AND deleted_at IS NULL ORDER BY created_at DESC"
        )
        reports = [dict(row) for row in cursor.fetchall()]

        files_created = {}  # path -> {success: bool, orders: [], last_modified: str}
        successful_orders = []
        failed_orders = []

        for report in reports:
            content = report.get("content", "")
            title = report.get("title", "")
            is_success = "COMPLETADO" in title

            # Extract files
            fm = re.search(r'Archivos (?:modificados|intentados):\s*(.+?)(?:\n|$)', content)
            if fm:
                file_list = [f.strip() for f in fm.group(1).split(",") if f.strip()]
            else:
                file_list = []

            order_info = {
                "doc_id": report.get("id"),
                "title": title,
                "timestamp": report.get("created_at"),
                "files": file_list,
                "success": is_success,
                "author": report.get("author"),
            }

            if is_success:
                successful_orders.append(order_info)
                for f in file_list:
                    if f not in files_created:
                        files_created[f] = {"success": True, "orders": [], "last_modified": report.get("created_at")}
                    files_created[f]["orders"].append(report.get("id"))
            else:
                failed_orders.append(order_info)

        return {
            "files_generated": files_created,
            "total_files": len(files_created),
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "total_successful": len(successful_orders),
            "total_failed": len(failed_orders),
        }
    finally:
        conn.close()


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Web UI para ver hilos de conversacion entre workers."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    raise HTTPException(404, "UI no encontrada")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=25500)
