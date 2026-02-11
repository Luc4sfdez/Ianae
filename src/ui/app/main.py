"""
Orchestra Dashboard - FastAPI Backend (Advanced)
Puerto: 25501
Consume: docs-service (localhost:25500)
Integra: IANAE core (nucleo.py, emergente.py)
Orden #24: Dashboard Avanzado con D3.js, WebSocket, Experimentos
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from pydantic import BaseModel
import requests
import asyncio
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional
import os
from pathlib import Path

# Añadir src/ al path para importar IANAE core y NLP
SRC_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(SRC_PATH / "core"))

import nucleo as _nucleo_module
sys.modules['nucleo_lucas'] = _nucleo_module  # Alias para emergente.py

from nucleo import ConceptosLucas, crear_universo_lucas
from emergente import PensamientoLucas

# NLP Pipeline (optional - funciona con o sin spaCy/transformers)
_nlp_pipeline = None
try:
    from nlp.pipeline import PipelineNLP
    _nlp_available = True
except ImportError:
    _nlp_available = False

app = FastAPI(title="Orchestra Dashboard", version="2.0.0")

# Configuración
DOCS_SERVICE_URL = "http://localhost:25500"
DAEMON_LOG_PATH = Path(__file__).parent.parent.parent.parent / "orchestra" / "daemon" / "logs" / "arquitecto.log"
SNAPSHOTS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Static files y templates
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ==================== IANAE System (singleton) ====================

_ianae_system: Optional[ConceptosLucas] = None
_ianae_pensamiento: Optional[PensamientoLucas] = None

def get_ianae():
    """Obtiene o inicializa el sistema IANAE"""
    global _ianae_system, _ianae_pensamiento, _nlp_pipeline
    if _ianae_system is None:
        _ianae_system = crear_universo_lucas()
        _ianae_system.crear_relaciones_lucas()
        _ianae_pensamiento = PensamientoLucas(_ianae_system)
        # Inicializar NLP pipeline conectado al sistema
        if _nlp_available and _nlp_pipeline is None:
            try:
                _nlp_pipeline = PipelineNLP(sistema_ianae=_ianae_system, modo_nlp="auto")
            except Exception as e:
                print(f"[UI] NLP pipeline no disponible: {e}")
    return _ianae_system, _ianae_pensamiento

# ==================== WebSocket Manager ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

ws_manager = ConnectionManager()

# ==================== Pydantic Models ====================

class TextInput(BaseModel):
    text: str
    profundidad: int = 3
    temperatura: float = 0.2

class ExperimentInput(BaseModel):
    params: dict = {}

# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """Estado de servicios (docs-service y daemon)"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    # Verificar docs-service
    try:
        response = requests.get(f"{DOCS_SERVICE_URL}/health", timeout=2)
        if response.status_code == 200:
            status["services"]["docs_service"] = {
                "status": "online",
                "port": 25500,
                "uptime": "unknown"
            }
        else:
            status["services"]["docs_service"] = {
                "status": "error",
                "port": 25500,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        status["services"]["docs_service"] = {
            "status": "offline",
            "port": 25500,
            "error": str(e)
        }

    # Verificar daemon (por logs)
    daemon_status = get_daemon_status()
    status["services"]["daemon"] = daemon_status

    # Métricas API Anthropic
    api_metrics = get_api_metrics_from_log()
    status["api_metrics"] = api_metrics

    return status

@app.get("/api/documents")
async def get_documents(
    limit: int = 50,
    category: Optional[str] = None,
    author: Optional[str] = None,
    status: Optional[str] = None,
    worker: Optional[str] = None
):
    """Lista de documentos con filtros opcionales"""
    try:
        # Construir query params
        params = {"limit": limit}

        response = requests.get(f"{DOCS_SERVICE_URL}/api/v1/docs", params=params, timeout=5)
        response.raise_for_status()

        data = response.json()
        docs = data.get("docs", []) if isinstance(data, dict) else []

        # Filtrar localmente (docs-service no tiene todos los filtros)
        if category:
            docs = [d for d in docs if d.get("category") == category]
        if author:
            docs = [d for d in docs if d.get("author") == author]
        if status:
            docs = [d for d in docs if d.get("status") == status]
        if worker:
            # Filtrar por tag (worker-core, worker-ui, etc.)
            docs = [d for d in docs if worker in str(d.get("tags", ""))]

        # Añadir tiempo relativo
        for doc in docs:
            doc["relative_time"] = get_relative_time(doc.get("created_at"))

        return {
            "documents": docs,
            "count": len(docs),
            "timestamp": datetime.now().isoformat()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"docs-service unavailable: {str(e)}")

@app.get("/api/workers")
async def get_workers_status():
    """Estado de cada worker"""
    workers = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]
    workers_status = []

    for worker in workers:
        try:
            response = requests.get(
                f"{DOCS_SERVICE_URL}/api/v1/worker/{worker}/pendientes",
                timeout=2
            )
            pendientes = response.json() if response.status_code == 200 else []

            # Obtener última actividad
            all_docs_response = requests.get(f"{DOCS_SERVICE_URL}/api/v1/docs?limit=100", timeout=2)
            all_docs_data = all_docs_response.json() if all_docs_response.status_code == 200 else {}
            all_docs = all_docs_data.get("docs", []) if isinstance(all_docs_data, dict) else []

            # Filtrar documentos del worker
            worker_docs = [d for d in all_docs if worker in str(d.get("tags", "")) or d.get("author") == worker]

            last_activity = None
            reportes_publicados = 0

            if worker_docs:
                # Encontrar último documento
                worker_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                last_activity = worker_docs[0].get("created_at")
                # Contar reportes
                reportes_publicados = len([d for d in worker_docs if d.get("category") == "reportes"])

            # Determinar estado
            if last_activity:
                minutes_ago = get_minutes_since(last_activity)
                if minutes_ago < 15:
                    status_emoji = "🟢"
                    status_text = "Activo"
                elif len(pendientes) > 0:
                    status_emoji = "🟡"
                    status_text = "Iniciando"
                else:
                    status_emoji = "🔴"
                    status_text = "Inactivo"
            else:
                status_emoji = "🔴"
                status_text = "Sin arrancar"

            workers_status.append({
                "name": worker,
                "pendientes": len(pendientes),
                "ultima_actividad": last_activity,
                "relative_time": get_relative_time(last_activity) if last_activity else "nunca",
                "reportes_publicados": reportes_publicados,
                "status": status_text,
                "status_emoji": status_emoji
            })

        except Exception as e:
            workers_status.append({
                "name": worker,
                "error": str(e),
                "status": "Error",
                "status_emoji": "⚠️"
            })

    return {
        "workers": workers_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/activity")
async def get_activity(limit: int = 50):
    """Timeline de actividad reciente"""
    try:
        response = requests.get(f"{DOCS_SERVICE_URL}/api/v1/docs?limit={limit}", timeout=5)
        response.raise_for_status()

        data = response.json()
        docs = data.get("docs", []) if isinstance(data, dict) else []

        # Formatear para timeline
        activity = []
        for doc in docs:
            # Extraer tipo del título
            title = doc.get("title", "")
            if title.startswith("ORDEN:"):
                tipo = "ORDEN"
                color = "blue"
            elif title.startswith("REPORTE:"):
                tipo = "REPORTE"
                color = "green"
            elif title.startswith("DUDA:"):
                tipo = "DUDA"
                color = "yellow"
            elif title.startswith("RESPUESTA"):
                tipo = "RESPUESTA"
                color = "purple"
            elif title.startswith("ESCALADO"):
                tipo = "ESCALADO"
                color = "red"
            else:
                tipo = "INFO"
                color = "gray"

            activity.append({
                "id": doc.get("id"),
                "timestamp": doc.get("created_at"),
                "relative_time": get_relative_time(doc.get("created_at")),
                "tipo": tipo,
                "color": color,
                "author": doc.get("author"),
                "title": title.replace(f"{tipo}:", "").strip()[:80],
                "full_title": title,
                "tags": doc.get("tags", "")
            })

        return {
            "activity": activity,
            "count": len(activity),
            "timestamp": datetime.now().isoformat()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"docs-service unavailable: {str(e)}")

@app.get("/api/metrics")
async def get_metrics():
    """Métricas agregadas del sistema (consume docs-service)"""
    try:
        # Obtener métricas completas del docs-service
        response = requests.get(f"{DOCS_SERVICE_URL}/api/v1/metrics/system", timeout=5)
        response.raise_for_status()

        metrics = response.json()

        # Añadir métricas de API Anthropic
        api_metrics = get_api_metrics_from_log()
        metrics["api"] = api_metrics

        # Calcular workers activos/inactivos desde métricas existentes
        workers_metrics = metrics.get("workers", {})
        activos = 0
        inactivos = 0
        for worker, data in workers_metrics.items():
            if data.get("tareas_completadas", 0) > 0 or data.get("reportes_publicados", 0) > 0:
                activos += 1
            else:
                inactivos += 1

        metrics["workers_status"] = {
            "activos": activos,
            "inactivos": inactivos,
            "total": len(workers_metrics)
        }

        return metrics

    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/alerts")
async def get_alerts():
    """Obtener alertas del sistema desde docs-service"""
    try:
        response = requests.get(f"{DOCS_SERVICE_URL}/api/v1/alerts", timeout=5)
        response.raise_for_status()

        alerts_data = response.json()

        # Intentar añadir alerta de daemon (con timeout)
        try:
            daemon_status = get_daemon_status()
            if daemon_status.get("status") == "stale":
                minutes = daemon_status.get("minutes_ago", 0)
                alerts_data["alerts"].insert(0, {
                    "level": "critical" if minutes > 10 else "error",
                    "type": "daemon_inactive",
                    "message": f"Daemon sin actividad hace {minutes} minutos",
                    "timestamp": datetime.now().isoformat(),
                    "details": {"minutes_ago": minutes}
                })
                alerts_data["count"] += 1
                alerts_data["has_critical"] = True
            elif daemon_status.get("status") == "idle":
                minutes = daemon_status.get("minutes_ago", 0)
                if minutes > 2:
                    alerts_data["alerts"].insert(0, {
                        "level": "warning",
                        "type": "daemon_idle",
                        "message": f"Daemon en idle hace {minutes} minutos",
                        "timestamp": datetime.now().isoformat(),
                        "details": {"minutes_ago": minutes}
                    })
                    alerts_data["count"] += 1
        except Exception:
            # Si falla leer daemon status, no bloquear las alertas
            pass

        return alerts_data

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"docs-service unavailable: {str(e)}")

# ==================== WebSocket Endpoint ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para actualizaciones en tiempo real"""
    await ws_manager.connect(websocket)
    try:
        # Enviar estado inicial de IANAE
        try:
            sistema, _ = get_ianae()
            await websocket.send_json({
                "type": "ianae_status",
                "data": {
                    "conceptos": len(sistema.conceptos),
                    "relaciones": sistema.grafo.number_of_edges(),
                    "metricas": sistema.metricas
                }
            })
        except Exception:
            pass  # Client may have disconnected already

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg.get("type") == "request_network":
                try:
                    sistema, _ = get_ianae()
                    network = build_network_data(sistema)
                    await websocket.send_json({
                        "type": "network_update",
                        "data": network
                    })
                except Exception:
                    pass  # Client may have disconnected

    except (WebSocketDisconnect, RuntimeError):
        ws_manager.disconnect(websocket)

# ==================== IANAE API Endpoints ====================

@app.get("/api/ianae/network")
async def get_ianae_network():
    """Obtiene la red de conceptos de IANAE para visualizacion D3.js"""
    try:
        sistema, _ = get_ianae()
        return build_network_data(sistema)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ianae/process-text")
async def process_text(input_data: TextInput):
    """Procesa texto activando la red IANAE. Usa pipeline NLP si disponible."""
    try:
        sistema, pensamiento = get_ianae()

        text = input_data.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Texto vacio")

        nlp_resultado = None
        conceptos_nlp = []

        # Intentar procesamiento NLP (extrae conceptos nuevos e inyecta en red)
        if _nlp_pipeline is not None:
            try:
                nlp_resultado = _nlp_pipeline.procesar(
                    text, max_conceptos=8, categoria="nlp_extraidos"
                )
                conceptos_nlp = [c["nombre"] for c in nlp_resultado.get("conceptos", [])]
            except Exception as e:
                print(f"[UI] NLP pipeline error (fallback a matching): {e}")

        # Buscar concepto existente mas cercano al texto (para activacion)
        conceptos_encontrados = []
        text_lower = text.lower()
        for nombre in sistema.conceptos:
            if nombre.lower() in text_lower or text_lower in nombre.lower():
                conceptos_encontrados.append(nombre)

        if not conceptos_encontrados:
            for nombre in sistema.conceptos:
                for palabra in text_lower.split():
                    if len(palabra) > 2 and palabra in nombre.lower():
                        conceptos_encontrados.append(nombre)
                        break

        # Incluir conceptos NLP recien inyectados
        for cn in conceptos_nlp:
            if cn in sistema.conceptos and cn not in conceptos_encontrados:
                conceptos_encontrados.append(cn)

        if not conceptos_encontrados:
            conceptos_encontrados = [list(sistema.conceptos.keys())[0]]

        # Activar el concepto principal
        concepto_principal = conceptos_encontrados[0]
        resultado = sistema.activar(
            concepto_principal,
            pasos=input_data.profundidad,
            temperatura=input_data.temperatura
        )

        if not resultado:
            return {"error": "No se pudo activar", "concepto": concepto_principal}

        activaciones = resultado[-1]
        activos = [
            {"concepto": c, "activacion": round(a, 4)}
            for c, a in sorted(activaciones.items(), key=lambda x: x[1], reverse=True)
            if a > 0.05
        ]

        mods = sistema.auto_modificar(fuerza=0.1)
        network = build_network_data(sistema, activaciones)

        response_data = {
            "concepto_activado": concepto_principal,
            "conceptos_encontrados": conceptos_encontrados,
            "conceptos_nlp_extraidos": conceptos_nlp,
            "nlp_modo": _nlp_pipeline.extractor.modo if _nlp_pipeline else "no_disponible",
            "activaciones": activos[:15],
            "modificaciones_hebbianas": mods,
            "network": network,
            "metricas": sistema.metricas,
            "timestamp": datetime.now().isoformat()
        }

        # Broadcast via WebSocket
        await ws_manager.broadcast({
            "type": "activation",
            "data": {
                "concepto": concepto_principal,
                "activaciones": activos[:10],
                "network": network
            }
        })

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ianae/experiment/{name}")
async def run_experiment(name: str, input_data: ExperimentInput):
    """Ejecuta un experimento IANAE"""
    try:
        sistema, pensamiento = get_ianae()
        params = input_data.params

        if name == "explorar_proyecto":
            proyecto = params.get("proyecto", "Tacografos")
            profundidad = params.get("profundidad", 3)
            if proyecto not in sistema.conceptos:
                raise HTTPException(status_code=400, detail=f"Proyecto '{proyecto}' no existe")
            resultado_texto = sistema.explorar_proyecto(proyecto, profundidad=profundidad)
            activaciones = sistema.historial_activaciones[-1]["resultado"] if sistema.historial_activaciones else {}

        elif name == "convergencia_proyectos":
            proyectos = params.get("proyectos", ["Tacografos", "VBA2Python", "RAG_System"])
            for p in proyectos:
                if p not in sistema.conceptos:
                    raise HTTPException(status_code=400, detail=f"Proyecto '{p}' no existe")
            resultado_texto = pensamiento.experimento_convergencia_proyectos(proyectos)
            activaciones = pensamiento.historial_pensamientos[-1].get("activaciones_convergentes", {}) if pensamiento.historial_pensamientos else {}

        elif name == "detectar_emergencias":
            umbral = params.get("umbral", 0.3)
            # Ejecutar algunos ciclos para generar historial
            if len(sistema.historial_activaciones) < 3:
                sistema.ciclo_vital(num_ciclos=5, auto_mod=True)
            resultado_texto = sistema.detectar_emergencias(umbral_emergencia=umbral)
            activaciones = sistema.historial_activaciones[-1]["resultado"] if sistema.historial_activaciones else {}

        elif name == "ciclo_vital":
            num_ciclos = params.get("num_ciclos", 10)
            num_ciclos = min(num_ciclos, 50)
            resultados_ciclo = sistema.ciclo_vital(num_ciclos=num_ciclos, auto_mod=True)
            resultado_texto = f"Ejecutados {len(resultados_ciclo)} ciclos vitales.\n"
            resultado_texto += f"Metricas actualizadas: edad={sistema.metricas['edad']}, "
            resultado_texto += f"auto_mods={sistema.metricas['auto_modificaciones']}, "
            resultado_texto += f"ciclos={sistema.metricas['ciclos_pensamiento']}"
            activaciones = resultados_ciclo[-1]["activacion_final"] if resultados_ciclo else {}

        else:
            raise HTTPException(status_code=400, detail=f"Experimento '{name}' no existe. Disponibles: explorar_proyecto, convergencia_proyectos, detectar_emergencias, ciclo_vital")

        network = build_network_data(sistema, activaciones)

        response_data = {
            "experiment": name,
            "resultado": resultado_texto,
            "network": network,
            "metricas": sistema.metricas,
            "timestamp": datetime.now().isoformat()
        }

        # Broadcast resultado via WebSocket
        await ws_manager.broadcast({
            "type": "experiment_result",
            "data": {
                "experiment": name,
                "network": network,
                "metricas": sistema.metricas
            }
        })

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ianae/metricas")
async def get_ianae_metricas():
    """Metricas del sistema IANAE"""
    try:
        sistema, _ = get_ianae()
        return {
            "metricas": sistema.metricas,
            "conceptos_total": len(sistema.conceptos),
            "relaciones_total": sistema.grafo.number_of_edges(),
            "categorias": {k: len(v) for k, v in sistema.categorias.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ianae/snapshot/save")
async def save_snapshot(name: str = "auto"):
    """Guarda un snapshot del estado actual de IANAE"""
    try:
        sistema, _ = get_ianae()
        filename = f"snapshot_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = SNAPSHOTS_DIR / filename
        if sistema.guardar(str(filepath)):
            return {"saved": True, "filename": filename, "path": str(filepath)}
        raise HTTPException(status_code=500, detail="Error guardando snapshot")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ianae/snapshot/load")
async def load_snapshot(filename: str):
    """Carga un snapshot guardado"""
    global _ianae_system, _ianae_pensamiento
    try:
        filepath = SNAPSHOTS_DIR / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Snapshot '{filename}' no encontrado")
        loaded = ConceptosLucas.cargar(str(filepath))
        if loaded is None:
            raise HTTPException(status_code=500, detail="Error cargando snapshot")
        _ianae_system = loaded
        _ianae_pensamiento = PensamientoLucas(_ianae_system)

        await ws_manager.broadcast({
            "type": "snapshot_loaded",
            "data": build_network_data(_ianae_system)
        })

        return {"loaded": True, "filename": filename, "conceptos": len(_ianae_system.conceptos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ianae/snapshots")
async def list_snapshots():
    """Lista snapshots disponibles"""
    try:
        snapshots = []
        for f in sorted(SNAPSHOTS_DIR.glob("snapshot_*.json"), reverse=True):
            stat = f.stat()
            snapshots.append({
                "filename": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return {"snapshots": snapshots, "count": len(snapshots)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Network Data Builder ====================

def build_network_data(sistema: ConceptosLucas, activaciones: dict = None) -> dict:
    """Construye datos de red para D3.js"""
    colores = {
        'tecnologias': '#FF6B6B',
        'proyectos': '#4ECDC4',
        'lucas_personal': '#45B7D1',
        'conceptos_ianae': '#96CEB4',
        'herramientas': '#FFEAA7',
        'emergentes': '#DDA0DD',
        'nlp_extraidos': '#F472B6'
    }

    nodes = []
    for nombre, datos in sistema.conceptos.items():
        cat = datos['categoria']
        activacion = activaciones.get(nombre, 0) if activaciones else 0
        nodes.append({
            "id": nombre,
            "category": cat,
            "color": colores.get(cat, '#888888'),
            "activaciones": datos['activaciones'],
            "fuerza": datos['fuerza'],
            "activacion_actual": round(activacion, 4),
            "conexiones": datos['conexiones_proyecto'],
            "size": 8 + (activacion * 30) if activacion > 0 else 6 + min(datos['activaciones'], 20)
        })

    links = []
    seen = set()
    for u, v, d in sistema.grafo.edges(data=True):
        key = tuple(sorted([u, v]))
        if key not in seen:
            seen.add(key)
            links.append({
                "source": u,
                "target": v,
                "weight": round(d['weight'], 3)
            })

    return {
        "nodes": nodes,
        "links": links,
        "metricas": sistema.metricas,
        "categorias": {k: len(v) for k, v in sistema.categorias.items()},
        "timestamp": datetime.now().isoformat()
    }

# ==================== Helper Functions ====================

def get_daemon_status() -> Dict:
    """Obtener estado del daemon desde logs"""
    try:
        if not DAEMON_LOG_PATH.exists():
            return {
                "status": "unknown",
                "error": "Log file not found"
            }

        # Leer últimas líneas del log
        with open(DAEMON_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if not lines:
                return {"status": "unknown", "error": "Empty log"}

            # Buscar última línea con timestamp
            last_line = None
            for line in reversed(lines[-50:]):  # Últimas 50 líneas
                if "[INFO]" in line or "[WARNING]" in line or "[ERROR]" in line:
                    last_line = line
                    break

            if not last_line:
                return {"status": "unknown", "error": "No recent activity"}

            # Extraer timestamp
            try:
                timestamp_str = last_line.split(" ")[0] + " " + last_line.split(" ")[1].split(",")[0]
                last_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                minutes_ago = (datetime.now() - last_time).total_seconds() / 60

                if minutes_ago < 2:
                    status = "online"
                elif minutes_ago < 10:
                    status = "idle"
                else:
                    status = "stale"

                return {
                    "status": status,
                    "last_activity": last_time.isoformat(),
                    "minutes_ago": int(minutes_ago)
                }

            except Exception as e:
                return {"status": "unknown", "error": f"Parse error: {str(e)}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_api_metrics_from_log() -> Dict:
    """Extraer métricas de API del log del daemon"""
    try:
        if not DAEMON_LOG_PATH.exists():
            return {"calls_today": 0, "calls_total": 0, "cost_estimate": 0.0}

        with open(DAEMON_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Buscar líneas con "API #X"
        import re
        api_calls = re.findall(r"API #(\d+)", content)

        if api_calls:
            calls_today = int(api_calls[-1])  # Último contador
            calls_total = calls_today  # Por ahora igual (resetea diario)
            cost_estimate = calls_today * 0.02  # Estimado: $0.02 por llamada

            return {
                "calls_today": calls_today,
                "calls_total": calls_total,
                "cost_estimate": round(cost_estimate, 2)
            }

        return {"calls_today": 0, "calls_total": 0, "cost_estimate": 0.0}

    except Exception:
        return {"calls_today": 0, "calls_total": 0, "cost_estimate": 0.0}

def get_relative_time(timestamp_str: Optional[str]) -> str:
    """Convertir timestamp ISO a formato relativo"""
    if not timestamp_str:
        return "nunca"

    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        delta = now - timestamp

        seconds = delta.total_seconds()
        if seconds < 60:
            return "ahora"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"hace {minutes} min"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"hace {hours}h"
        else:
            days = int(seconds / 86400)
            return f"hace {days}d"

    except Exception:
        return "desconocido"

def get_minutes_since(timestamp_str: str) -> int:
    """Calcular minutos desde timestamp"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        delta = now - timestamp
        return int(delta.total_seconds() / 60)
    except Exception:
        return 999999  # Muy viejo

if __name__ == "__main__":
    import uvicorn
    # Configurar encoding UTF-8 para Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    uvicorn.run(app, host="0.0.0.0", port=25501)
