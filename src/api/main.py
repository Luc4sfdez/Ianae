"""
API REST publica de IANAE.

Endpoints CRUD para conceptos, activacion, red y procesamiento NLP.
Standalone — separada del dashboard.

Uso:
    uvicorn src.api.main:app --port 8000
    # Docs: http://localhost:8000/docs
"""
import numpy as np
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.dashboard import dashboard_html

from src.api.models import (
    ConceptCreate, ConceptResponse, ConceptDetail,
    RelationCreate, RelationResponse,
    ActivateRequest, ActivateResponse,
    IngestRequest, IngestResponse,
    NetworkResponse, StatsResponse,
    ErrorResponse, HealthResponse,
    FeedbackRequest, FeedbackResponse,
    MetricsResponse,
    RecommendationsRequest, PatternsResponse,
    RecommendationsResponse, PredictiveResponse,
    ChatRequest, ChatResponse,
    SuenoRequest, SuenoResponse,
    ConscienciaResponse, OrganismoResponse, DiarioResponse,
    StreamStatsResponse,
)
from src.api.auth import validate_api_key, check_rate_limit
from src.core.nucleo import ConceptosLucas, crear_universo_lucas
from src.core.aprendizaje_refuerzo import AprendizajeRefuerzo

# --- NLP (optional) ---
try:
    from src.nlp.pipeline import PipelineNLP
    _nlp_available = True
except ImportError:
    _nlp_available = False


# --- State ---

_sistema: Optional[ConceptosLucas] = None
_pipeline = None
_aprendizaje: Optional[AprendizajeRefuerzo] = None


def get_sistema() -> ConceptosLucas:
    """Retorna la instancia del sistema IANAE."""
    global _sistema
    if _sistema is None:
        _sistema = crear_universo_lucas()
        _sistema.crear_relaciones_lucas()
    return _sistema


def set_sistema(sistema: ConceptosLucas):
    """Permite inyectar un sistema (para tests)."""
    global _sistema
    _sistema = sistema


def get_aprendizaje() -> AprendizajeRefuerzo:
    """Retorna la instancia de AprendizajeRefuerzo."""
    global _aprendizaje
    if _aprendizaje is None:
        _aprendizaje = AprendizajeRefuerzo()
    return _aprendizaje


def set_aprendizaje(ap: AprendizajeRefuerzo):
    """Permite inyectar instancia (para tests)."""
    global _aprendizaje
    _aprendizaje = ap


def get_pipeline():
    """Retorna el pipeline NLP (lazy init)."""
    global _pipeline
    if _pipeline is None and _nlp_available:
        _pipeline = PipelineNLP(sistema_ianae=get_sistema(), modo_nlp="auto")
    return _pipeline


# --- App ---

app = FastAPI(
    title="IANAE API",
    description="API REST para el sistema de inteligencia artificial IANAE — conceptos difusos, propagacion y NLP.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard():
    """Dashboard en vivo — IANAE vida en tiempo real."""
    return HTMLResponse(content=dashboard_html())


# --- Health ---

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    sistema = get_sistema()
    pipeline = get_pipeline()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        conceptos=len(sistema.conceptos),
        modo_nlp=pipeline.extractor.modo if pipeline else "no_disponible",
    )


# --- Concepts CRUD ---

@app.get("/api/v1/concepts", response_model=list[ConceptResponse], tags=["concepts"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def list_concepts(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    limit: int = Query(50, ge=1, le=500, description="Maximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginacion"),
):
    """Lista todos los conceptos del sistema."""
    sistema = get_sistema()
    conceptos = []
    for nombre, data in sistema.conceptos.items():
        if categoria and data.get("categoria") != categoria:
            continue
        conceptos.append(ConceptResponse(
            nombre=nombre,
            categoria=data.get("categoria", "emergentes"),
            activaciones=data.get("activaciones", 0),
            fuerza=data.get("fuerza", 1.0),
            vector_dim=len(data["actual"]),
            creado=data.get("creado", 0),
        ))

    conceptos.sort(key=lambda c: c.activaciones, reverse=True)
    return conceptos[offset:offset + limit]


@app.get("/api/v1/concepts/{name}", response_model=ConceptDetail, tags=["concepts"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_concept(name: str, include_vector: bool = Query(False)):
    """Detalle de un concepto especifico."""
    sistema = get_sistema()
    if name not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{name}' no encontrado")

    data = sistema.conceptos[name]
    vecinos = []
    for vecino in sistema.grafo.neighbors(name):
        edge = sistema.grafo[name][vecino]
        vecinos.append({
            "nombre": vecino,
            "fuerza": round(edge.get("weight", 0), 4),
            "categoria": sistema.conceptos[vecino].get("categoria", ""),
        })
    vecinos.sort(key=lambda v: v["fuerza"], reverse=True)

    return ConceptDetail(
        nombre=name,
        categoria=data.get("categoria", "emergentes"),
        activaciones=data.get("activaciones", 0),
        fuerza=data.get("fuerza", 1.0),
        vector_dim=len(data["actual"]),
        creado=data.get("creado", 0),
        vecinos=vecinos,
        vector=data["actual"].tolist() if include_vector else None,
    )


@app.post("/api/v1/concepts", response_model=ConceptResponse, status_code=201,
          tags=["concepts"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def create_concept(body: ConceptCreate):
    """Crea un nuevo concepto en el sistema."""
    sistema = get_sistema()

    if body.nombre in sistema.conceptos:
        raise HTTPException(status_code=409, detail=f"Concepto '{body.nombre}' ya existe")

    atributos = None
    if body.atributos:
        if len(body.atributos) != sistema.dim_vector:
            raise HTTPException(
                status_code=422,
                detail=f"Vector debe tener {sistema.dim_vector} dimensiones, recibido {len(body.atributos)}"
            )
        atributos = np.array(body.atributos)

    sistema.añadir_concepto(
        body.nombre,
        atributos=atributos,
        incertidumbre=body.incertidumbre,
        categoria=body.categoria,
    )

    data = sistema.conceptos[body.nombre]
    return ConceptResponse(
        nombre=body.nombre,
        categoria=data.get("categoria", "emergentes"),
        activaciones=0,
        fuerza=1.0,
        vector_dim=len(data["actual"]),
        creado=data.get("creado", 0),
    )


@app.delete("/api/v1/concepts/{name}", status_code=204, tags=["concepts"],
            dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def delete_concept(name: str):
    """Elimina un concepto del sistema."""
    sistema = get_sistema()
    if name not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{name}' no encontrado")

    # Eliminar de grafo, conceptos, indice, categorias
    sistema.grafo.remove_node(name)
    del sistema.conceptos[name]

    for cat_list in sistema.categorias.values():
        if name in cat_list:
            cat_list.remove(name)


# --- Relations ---

@app.post("/api/v1/relations", response_model=RelationResponse, status_code=201,
          tags=["relations"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def create_relation(body: RelationCreate):
    """Crea una relacion entre dos conceptos."""
    sistema = get_sistema()
    if body.concepto1 not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{body.concepto1}' no encontrado")
    if body.concepto2 not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{body.concepto2}' no encontrado")

    fuerza = sistema.relacionar(body.concepto1, body.concepto2,
                                 fuerza=body.fuerza, bidireccional=body.bidireccional)
    return RelationResponse(
        concepto1=body.concepto1,
        concepto2=body.concepto2,
        fuerza=round(float(fuerza), 4),
    )


# --- Activate ---

@app.post("/api/v1/activate", response_model=ActivateResponse, tags=["propagation"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def activate_concept(body: ActivateRequest):
    """Activa un concepto y propaga por la red."""
    sistema = get_sistema()
    if body.concepto not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{body.concepto}' no encontrado")

    resultado = sistema.activar(body.concepto, pasos=body.pasos, temperatura=body.temperatura)

    # Top activados del ultimo paso
    top = []
    if resultado:
        ultimo = resultado[-1]
        for nombre, activacion in sorted(ultimo.items(), key=lambda x: x[1], reverse=True)[:10]:
            if activacion > 0.01:
                top.append({
                    "nombre": nombre,
                    "activacion": round(activacion, 4),
                    "categoria": sistema.conceptos[nombre].get("categoria", ""),
                })

    return ActivateResponse(
        concepto=body.concepto,
        pasos=body.pasos,
        activaciones=resultado,
        top_activados=top,
    )


# --- Network ---

@app.get("/api/v1/network", response_model=NetworkResponse, tags=["network"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_network():
    """Retorna el grafo completo de conceptos y relaciones."""
    sistema = get_sistema()

    conceptos = []
    for nombre, data in sistema.conceptos.items():
        conceptos.append({
            "nombre": nombre,
            "categoria": data.get("categoria", "emergentes"),
            "activaciones": data.get("activaciones", 0),
            "fuerza": data.get("fuerza", 1.0),
        })

    relaciones = []
    for c1, c2, edge_data in sistema.grafo.edges(data=True):
        relaciones.append({
            "source": c1,
            "target": c2,
            "weight": round(edge_data.get("weight", 0), 4),
        })

    categorias = {}
    for cat, miembros in sistema.categorias.items():
        categorias[cat] = len(miembros)

    return NetworkResponse(
        nodos=len(sistema.conceptos),
        aristas=sistema.grafo.number_of_edges(),
        conceptos=conceptos,
        relaciones=relaciones,
        categorias=categorias,
    )


# --- Stats ---

@app.get("/api/v1/stats", response_model=StatsResponse, tags=["system"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_stats():
    """Estadisticas del sistema."""
    sistema = get_sistema()

    categorias = {}
    for cat, miembros in sistema.categorias.items():
        categorias[cat] = len(miembros)

    metricas = {}
    for k, v in sistema.metricas.items():
        if isinstance(v, (int, float, str, bool)):
            metricas[k] = v

    return StatsResponse(
        conceptos_total=len(sistema.conceptos),
        aristas_total=sistema.grafo.number_of_edges(),
        categorias=categorias,
        metricas=metricas,
    )


# --- Ingest (NLP) ---

@app.post("/api/v1/ingest", response_model=IngestResponse, tags=["nlp"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def ingest_text(body: IngestRequest):
    """Procesa texto via NLP y extrae conceptos a la red."""
    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="NLP no disponible (instalar spacy/sentence-transformers)"
        )

    resultado = pipeline.procesar(
        body.texto,
        max_conceptos=body.max_conceptos,
        categoria=body.categoria,
        umbral_relacion=body.umbral_relacion,
    )

    relaciones = []
    for rel in resultado.get("relaciones", []):
        if isinstance(rel, (list, tuple)) and len(rel) == 3:
            relaciones.append(list(rel))

    return IngestResponse(
        conceptos_extraidos=len(resultado.get("conceptos", [])),
        relaciones_detectadas=len(relaciones),
        conceptos=resultado.get("conceptos", []),
        relaciones=relaciones,
        modo_nlp=resultado.get("modo", "basico"),
        dim_original=resultado.get("dim_original", 0),
        dim_reducida=resultado.get("dim_reducida", 15),
    )


# --- Feedback ---

@app.post("/api/v1/feedback", response_model=FeedbackResponse, tags=["feedback"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def submit_feedback(body: FeedbackRequest):
    """
    Marca un concepto como relevante o ruido.

    - relevante: fortalece el concepto y refuerza sus conexiones
    - ruido: debilita el concepto y penaliza sus conexiones
    """
    sistema = get_sistema()
    if body.concepto not in sistema.conceptos:
        raise HTTPException(status_code=404, detail=f"Concepto '{body.concepto}' no encontrado")

    data = sistema.conceptos[body.concepto]
    fuerza_antes = data.get("fuerza", 1.0)

    aprendizaje = get_aprendizaje()

    if body.tipo == "relevante":
        # Fortalecer concepto
        data["fuerza"] = min(2.0, fuerza_antes + 0.3 * body.intensidad)

        # Refuerzo positivo en conexiones via Q-learning
        for vecino in sistema.grafo.neighbors(body.concepto):
            aprendizaje.actualizar(body.concepto, vecino, recompensa=body.intensidad)

        mensaje = f"Concepto '{body.concepto}' fortalecido"

    else:  # ruido
        # Debilitar concepto
        data["fuerza"] = max(0.05, fuerza_antes - 0.4 * body.intensidad)

        # Penalizacion en conexiones
        for vecino in sistema.grafo.neighbors(body.concepto):
            aprendizaje.actualizar(body.concepto, vecino, recompensa=-body.intensidad)

        mensaje = f"Concepto '{body.concepto}' debilitado"

    fuerza_despues = data["fuerza"]

    return FeedbackResponse(
        concepto=body.concepto,
        tipo=body.tipo,
        fuerza_antes=round(fuerza_antes, 4),
        fuerza_despues=round(fuerza_despues, 4),
        mensaje=mensaje,
    )


# --- Metrics ---

def _calcular_metricas(sistema) -> dict:
    """Calcula metricas internas del sistema."""
    fuerzas = [d.get("fuerza", 1.0) for d in sistema.conceptos.values()]
    activaciones_total = sum(d.get("activaciones", 0) for d in sistema.conceptos.values())
    debiles = sum(1 for f in fuerzas if f < 0.1)

    categorias = {}
    for cat, miembros in sistema.categorias.items():
        categorias[cat] = len(miembros)

    memoria_regs = 0
    if hasattr(sistema, "memoria") and hasattr(sistema.memoria, "registros"):
        memoria_regs = len(sistema.memoria.registros)

    return {
        "conceptos_total": len(sistema.conceptos),
        "aristas_total": sistema.grafo.number_of_edges(),
        "activaciones_totales": activaciones_total,
        "edad_sistema": sistema.metricas.get("edad", 0),
        "ciclos_pensamiento": sistema.metricas.get("ciclos_pensamiento", 0),
        "categorias": categorias,
        "fuerza_media": round(sum(fuerzas) / len(fuerzas), 4) if fuerzas else 0.0,
        "fuerza_min": round(min(fuerzas), 4) if fuerzas else 0.0,
        "fuerza_max": round(max(fuerzas), 4) if fuerzas else 0.0,
        "conceptos_debiles": debiles,
        "memoria_registros": memoria_regs,
    }


@app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["system"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_metrics():
    """Metricas del sistema en formato JSON."""
    sistema = get_sistema()
    return MetricsResponse(**_calcular_metricas(sistema))


@app.get("/metrics", tags=["system"])
async def get_metrics_prometheus():
    """Metricas en formato Prometheus text exposition."""
    from fastapi.responses import PlainTextResponse

    sistema = get_sistema()
    m = _calcular_metricas(sistema)

    lines = [
        "# HELP ianae_conceptos_total Number of concepts in the system",
        "# TYPE ianae_conceptos_total gauge",
        f"ianae_conceptos_total {m['conceptos_total']}",
        "# HELP ianae_aristas_total Number of edges in the graph",
        "# TYPE ianae_aristas_total gauge",
        f"ianae_aristas_total {m['aristas_total']}",
        "# HELP ianae_activaciones_totales Total activations across all concepts",
        "# TYPE ianae_activaciones_totales counter",
        f"ianae_activaciones_totales {m['activaciones_totales']}",
        "# HELP ianae_edad_sistema System age in cycles",
        "# TYPE ianae_edad_sistema counter",
        f"ianae_edad_sistema {m['edad_sistema']}",
        "# HELP ianae_ciclos_pensamiento Thought cycles completed",
        "# TYPE ianae_ciclos_pensamiento counter",
        f"ianae_ciclos_pensamiento {m['ciclos_pensamiento']}",
        "# HELP ianae_fuerza_media Average concept strength",
        "# TYPE ianae_fuerza_media gauge",
        f"ianae_fuerza_media {m['fuerza_media']}",
        "# HELP ianae_conceptos_debiles Concepts with strength below 0.1",
        "# TYPE ianae_conceptos_debiles gauge",
        f"ianae_conceptos_debiles {m['conceptos_debiles']}",
        "# HELP ianae_memoria_registros Memory association records",
        "# TYPE ianae_memoria_registros gauge",
        f"ianae_memoria_registros {m['memoria_registros']}",
    ]

    for cat, count in m["categorias"].items():
        safe_cat = cat.replace(" ", "_").replace("-", "_")
        lines.append(f'ianae_categoria_conceptos{{categoria="{safe_cat}"}} {count}')

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")


# --- Insights ---

_insights = None


def get_insights():
    """Retorna la instancia de InsightsEngine (lazy init)."""
    global _insights
    if _insights is None:
        from src.core.insights import InsightsEngine
        _insights = InsightsEngine(get_sistema())
    return _insights


def set_insights(engine):
    """Permite inyectar InsightsEngine (para tests)."""
    global _insights
    _insights = engine


@app.get("/api/v1/insights/patrones", response_model=PatternsResponse,
         tags=["insights"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_patrones():
    """Detecta patrones estructurales: comunidades, puentes, clusters."""
    engine = get_insights()
    return PatternsResponse(**engine.detectar_patrones())


@app.post("/api/v1/insights/recomendaciones", response_model=RecommendationsResponse,
          tags=["insights"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_recomendaciones(body: RecommendationsRequest):
    """Genera recomendaciones de exploracion y conexion."""
    engine = get_insights()
    resultado = engine.generar_recomendaciones(
        concepto=body.concepto,
        max_resultados=body.max_resultados,
    )
    if body.concepto and body.concepto not in get_sistema().conceptos:
        raise HTTPException(status_code=404,
                            detail=f"Concepto '{body.concepto}' no encontrado")
    return RecommendationsResponse(**resultado)


@app.get("/api/v1/insights/predictivo", response_model=PredictiveResponse,
         tags=["insights"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_predictivo():
    """Analisis predictivo: tendencias, gaps, predicciones."""
    engine = get_insights()
    return PredictiveResponse(**engine.analisis_predictivo())


# --- Organismo (Fase 7) ---

_organismo = None


def get_organismo():
    """Retorna la instancia del organismo IANAE (lazy init desde sistema existente)."""
    global _organismo
    if _organismo is None:
        from src.core.organismo import IANAE
        _organismo = IANAE.desde_componentes(get_sistema())
    return _organismo


def set_organismo(org):
    """Permite inyectar organismo (para tests)."""
    global _organismo
    _organismo = org


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["organismo"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def chat(body: ChatRequest):
    """Habla con IANAE. Retorna respuesta desde el grafo y la consciencia."""
    org = get_organismo()
    resultado = org.preguntar(body.mensaje)
    return ChatResponse(
        respuesta=resultado.get("respuesta", ""),
        conceptos_detectados=resultado.get("conceptos_detectados", []),
        coherencia=resultado.get("coherencia", 0.0),
    )


@app.post("/api/v1/suenos/imaginar", response_model=SuenoResponse, tags=["organismo"],
          dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def imaginar(body: SuenoRequest):
    """Simula una hipotesis en sandbox sin modificar el grafo real."""
    org = get_organismo()
    hipotesis: dict = {"tipo": body.tipo}
    if body.tipo == "conexion":
        if not body.a or not body.b:
            raise HTTPException(status_code=422, detail="Conexion requiere 'a' y 'b'")
        hipotesis.update({"a": body.a, "b": body.b, "fuerza": body.fuerza})
    else:
        if not body.nombre:
            raise HTTPException(status_code=422, detail="Concepto requiere 'nombre'")
        hipotesis.update({
            "nombre": body.nombre,
            "categoria": body.categoria,
            "conectar_a": body.conectar_a,
        })
    resultado = org.imaginar(hipotesis)
    return SuenoResponse(
        tipo=resultado.get("tipo", body.tipo),
        hipotesis=resultado.get("hipotesis", hipotesis),
        evaluacion=resultado.get("evaluacion"),
        impacto=resultado.get("impacto"),
        veredicto=resultado.get("evaluacion", resultado).get("veredicto")
        if isinstance(resultado.get("evaluacion", resultado), dict) else None,
    )


@app.get("/api/v1/consciencia", response_model=ConscienciaResponse, tags=["organismo"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_consciencia():
    """Estado de consciencia: pulso, fuerzas, sesgos, crecimiento, narrativa."""
    org = get_organismo()
    c = org.consciencia
    return ConscienciaResponse(
        pulso=c.pulso(),
        superficie=c.superficie(),
        corrientes=c.corrientes(),
        sesgos=c.detectar_sesgos(),
        crecimiento=c.medir_crecimiento(),
        narrativa=c.narrar_estado(),
    )


@app.get("/api/v1/organismo", response_model=OrganismoResponse, tags=["organismo"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_organismo_estado():
    """Estado completo del organismo IANAE."""
    org = get_organismo()
    return OrganismoResponse(**org.estado())


@app.get("/api/v1/vida/diario", response_model=DiarioResponse, tags=["organismo"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def get_diario(
    ultimos: int = Query(10, ge=1, le=100, description="Ultimas N entradas"),
):
    """Lee el diario de vida de IANAE."""
    org = get_organismo()
    entradas = org.vida.leer_diario(ultimos=ultimos)
    return DiarioResponse(entradas=entradas, total=len(entradas))


@app.post("/api/v1/vida/ciclo", tags=["organismo"])
async def ejecutar_ciclo():
    """Dispara un ciclo de vida completo de IANAE."""
    org = get_organismo()
    resultado = org.ciclo_completo()
    return resultado


# --- Streaming (Fase 11) ---


@app.get("/api/v1/stream", tags=["streaming"])
async def stream_events(
    tipos: Optional[str] = Query(None, description="Tipos separados por coma"),
    desde_id: int = Query(0, ge=0, description="ID desde donde leer"),
):
    """SSE endpoint — streaming de eventos del organismo."""
    import asyncio
    import json as _json
    from fastapi.responses import StreamingResponse

    org = get_organismo()
    ps = getattr(org, "pulso_streaming", None)
    if ps is None:
        raise HTTPException(status_code=503, detail="Streaming no disponible")

    tipos_set = set(t.strip() for t in tipos.split(",")) if tipos else None

    async def event_generator():
        current_id = desde_id
        for _ in range(60):  # max 30s (60 * 0.5)
            eventos = ps.consumir(desde_id=current_id, tipos=tipos_set, max_eventos=20)
            for ev in eventos:
                current_id = ev["id"]
                yield f"id: {ev['id']}\nevent: {ev['tipo']}\ndata: {_json.dumps(ev['data'], default=str)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/stream/stats", response_model=StreamStatsResponse,
         tags=["streaming"],
         dependencies=[Depends(validate_api_key), Depends(check_rate_limit)])
async def stream_stats():
    """Estadisticas del bus de streaming."""
    org = get_organismo()
    ps = getattr(org, "pulso_streaming", None)
    if ps is None:
        return StreamStatsResponse(activo=False, eventos_en_buffer=0, ultimo_id=0, tipos={}, suscriptores=0)
    return StreamStatsResponse(**ps.estadisticas())


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
