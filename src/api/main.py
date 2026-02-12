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
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import (
    ConceptCreate, ConceptResponse, ConceptDetail,
    RelationCreate, RelationResponse,
    ActivateRequest, ActivateResponse,
    IngestRequest, IngestResponse,
    NetworkResponse, StatsResponse,
    ErrorResponse, HealthResponse,
)
from src.api.auth import validate_api_key, check_rate_limit
from src.core.nucleo import ConceptosLucas, crear_universo_lucas

# --- NLP (optional) ---
try:
    from src.nlp.pipeline import PipelineNLP
    _nlp_available = True
except ImportError:
    _nlp_available = False


# --- State ---

_sistema: Optional[ConceptosLucas] = None
_pipeline = None


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


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
