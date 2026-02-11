from typing import TypedDict, List, Dict, Tuple
import numpy.typing as npt
from numpy import float64

class ConceptoData(TypedDict):
    base: npt.NDArray[float64]
    actual: npt.NDArray[float64] 
    historial: List[npt.NDArray[float64]]
    creado: int
    activaciones: int
    ultima_activacion: int
    fuerza: float

class MetricasData(TypedDict):
    edad: int
    conceptos_creados: int
    conexiones_formadas: int
    ciclos_pensamiento: int
    auto_modificaciones: int

class ActivacionHistorial(TypedDict):
    inicio: str
    resultado: Dict[str, float]
    pasos: int

# Tipos para los parámetros y retornos de ConceptosDifusos
ConceptosType = Dict[str, ConceptoData]
RelacionesType = Dict[str, List[Tuple[str, float]]]
