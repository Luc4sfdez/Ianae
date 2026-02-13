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


class MetricsResponse(BaseModel):
    conceptos_total: int
    aristas_total: int
    activaciones_totales: int
    edad_sistema: int
    ciclos_pensamiento: int
    categorias: Dict[str, int]
    fuerza_media: float
    fuerza_min: float
    fuerza_max: float
    conceptos_debiles: int
    memoria_registros: int


class HealthResponse(BaseModel):
    status: str
    version: str
    conceptos: int
    modo_nlp: str


# --- Insights Models ---

class RecommendationsRequest(BaseModel):
    concepto: Optional[str] = Field(None, description="Concepto base (None = global)")
    max_resultados: int = Field(5, ge=1, le=20, description="Maximo de resultados")


class PatternsResponse(BaseModel):
    comunidades: List[List[str]]
    puentes: List[Dict[str, Any]]
    clusters_densos: List[Dict[str, Any]]
    conceptos_aislados: List[str]
    patrones_emergentes: str
    candidatos_genesis: List[Dict[str, Any]]
    narrativa: str


class RecommendationsResponse(BaseModel):
    explorar: List[Dict[str, Any]]
    conectar: List[Dict[str, Any]]
    automatizar: Optional[str] = None
    convergencias: Optional[str] = None
    narrativa: str


class PredictiveResponse(BaseModel):
    tendencias: List[Dict[str, Any]]
    gaps_conocimiento: List[Dict[str, Any]]
    proximas_tecnologias: List[Dict[str, Any]]
    patrones_personales: Optional[str] = None
    narrativa: str


# --- Organismo Models (Fase 7) ---

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=5000, description="Mensaje para IANAE")


class ChatResponse(BaseModel):
    respuesta: str
    conceptos_detectados: List[str]
    coherencia: float


class SuenoRequest(BaseModel):
    tipo: str = Field(..., pattern="^(conexion|concepto)$", description="Tipo de hipotesis")
    a: Optional[str] = Field(None, description="Concepto A (para conexion)")
    b: Optional[str] = Field(None, description="Concepto B (para conexion)")
    fuerza: float = Field(0.7, ge=0, le=1, description="Fuerza de la conexion imaginada")
    nombre: Optional[str] = Field(None, description="Nombre del concepto (para concepto)")
    categoria: str = Field("emergentes", description="Categoria del concepto imaginado")
    conectar_a: List[str] = Field(default_factory=list, description="Conceptos a conectar")


class SuenoResponse(BaseModel):
    tipo: str
    hipotesis: Dict[str, Any]
    evaluacion: Optional[Dict[str, Any]] = None
    impacto: Optional[float] = None
    veredicto: Optional[str] = None


class ConscienciaResponse(BaseModel):
    pulso: Dict[str, Any]
    superficie: float
    corrientes: Dict[str, Any]
    sesgos: List[Dict[str, Any]]
    crecimiento: Dict[str, Any]
    narrativa: str


class OrganismoResponse(BaseModel):
    nacido: float
    edad_s: float
    conceptos: int
    relaciones: int
    ciclo_actual: int
    generacion: int = 0
    pulso: Dict[str, Any]
    superficie: float
    corrientes: Dict[str, Any]
    objetivos_pendientes: int
    suenos_prometedores: int
    conversaciones: int
    archivos_percibidos: int = 0
    memoria_viva: Optional[Dict] = None
    introspeccion: Optional[Dict] = None


class StreamStatsResponse(BaseModel):
    activo: bool
    eventos_en_buffer: int
    ultimo_id: int
    tipos: Dict[str, int]
    suscriptores: int


class DiarioResponse(BaseModel):
    entradas: List[Dict[str, Any]]
    total: int


# --- Conocimiento Externo (Fase 13) ---

class ConocimientoConfigRequest(BaseModel):
    habilitado: Optional[bool] = Field(None, description="Habilitar/deshabilitar")
    probabilidad_externa: Optional[float] = Field(None, ge=0, le=1, description="Probabilidad de exploracion externa")
    max_conceptos_por_ciclo: Optional[int] = Field(None, ge=1, le=20, description="Max conceptos absorbidos por ciclo")
    umbral_relevancia: Optional[float] = Field(None, ge=0, le=1, description="Umbral minimo de relevancia")


class ExploracionExternaRequest(BaseModel):
    concepto: str = Field(..., min_length=1, max_length=200, description="Concepto a explorar")
    fuente: Optional[str] = Field(None, description="Fuente especifica: wikipedia, rss, web, archivos")


class RSSFeedRequest(BaseModel):
    url: str = Field(..., min_length=5, description="URL del feed RSS/Atom")


# --- Introspeccion (Fase 14) ---

class IntrospeccionResponse(BaseModel):
    modulos: int
    clases: int
    metodos: int
    funciones: int
    lineas: int
    quien_soy: str
    modulos_detalle: List[Dict[str, Any]] = Field(default_factory=list)
