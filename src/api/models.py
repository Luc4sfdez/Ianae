"""Pydantic models para la API REST de IANAE."""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# --- Request Models ---

class ConceptCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del concepto")
    categoria: str = Field("emergentes", max_length=50, description="Categoria del concepto")
    atributos: Optional[List[float]] = Field(None, description="Vector de atributos (dim_vector)")
    incertidumbre: Optional[float] = Field(None, ge=0, le=1, description="Incertidumbre base")


class RelationCreate(BaseModel):
    concepto1: str = Field(..., min_length=1, description="Primer concepto")
    concepto2: str = Field(..., min_length=1, description="Segundo concepto")
    fuerza: Optional[float] = Field(None, ge=0, le=1, description="Fuerza de la relacion")
    bidireccional: bool = Field(True, description="Si la relacion es bidireccional")


class ActivateRequest(BaseModel):
    concepto: str = Field(..., min_length=1, description="Concepto a activar")
    pasos: int = Field(3, ge=1, le=20, description="Pasos de propagacion")
    temperatura: float = Field(0.1, ge=0, le=1, description="Temperatura de propagacion")


class IngestRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=50000, description="Texto a procesar")
    max_conceptos: int = Field(10, ge=1, le=50, description="Maximo de conceptos a extraer")
    categoria: str = Field("nlp_extraidos", description="Categoria para conceptos nuevos")
    umbral_relacion: float = Field(0.2, ge=0, le=1, description="Umbral minimo para relaciones")


# --- Response Models ---

class ConceptResponse(BaseModel):
    nombre: str
    categoria: str
    activaciones: int
    fuerza: float
    vector_dim: int
    creado: int


class ConceptDetail(ConceptResponse):
    vecinos: List[Dict[str, Any]] = Field(default_factory=list)
    vector: Optional[List[float]] = None


class RelationResponse(BaseModel):
    concepto1: str
    concepto2: str
    fuerza: float


class ActivateResponse(BaseModel):
    concepto: str
    pasos: int
    activaciones: List[Dict[str, float]]
    top_activados: List[Dict[str, Any]]


class IngestResponse(BaseModel):
    conceptos_extraidos: int
    relaciones_detectadas: int
    conceptos: List[Dict[str, Any]]
    relaciones: List[List[Any]]
    modo_nlp: str
    dim_original: int
    dim_reducida: int


class NetworkResponse(BaseModel):
    nodos: int
    aristas: int
    conceptos: List[Dict[str, Any]]
    relaciones: List[Dict[str, Any]]
    categorias: Dict[str, int]


class StatsResponse(BaseModel):
    conceptos_total: int
    aristas_total: int
    categorias: Dict[str, int]
    metricas: Dict[str, Any]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class FeedbackRequest(BaseModel):
    concepto: str = Field(..., min_length=1, description="Concepto a evaluar")
    tipo: str = Field(..., pattern="^(relevante|ruido)$", description="Tipo: 'relevante' o 'ruido'")
    intensidad: float = Field(0.5, ge=0, le=1, description="Intensidad del feedback")


class FeedbackResponse(BaseModel):
    concepto: str
    tipo: str
    fuerza_antes: float
    fuerza_despues: float
    mensaje: str


class HealthResponse(BaseModel):
    status: str
    version: str
    conceptos: int
    modo_nlp: str
