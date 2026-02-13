"""
Motor Emocional de IANAE — Fase 16: 8 estados emocionales.

Evalua metricas internas y determina el estado emocional del organismo.
Cada emocion tiene intensidad, valencia, descripcion y efectos sobre la curiosidad.
"""
import time
from collections import Counter
from typing import Any, Dict, List, Optional


EMOCIONES = {
    "inspirada": {
        "descripcion": "Muchos descubrimientos reveladores, energia creativa alta",
        "valencia": 1.0,
    },
    "curiosa": {
        "descripcion": "Estado base, explorando con mente abierta",
        "valencia": 0.6,
    },
    "aburrida": {
        "descripcion": "Demasiados ciclos rutinarios, necesita estimulo",
        "valencia": -0.3,
    },
    "enfocada": {
        "descripcion": "Racha productiva, profundizando en un tema",
        "valencia": 0.8,
    },
    "melancolica": {
        "descripcion": "Crecimiento decayendo y energia baja",
        "valencia": -0.5,
    },
    "asombrada": {
        "descripcion": "Alta novedad y absorcion de conceptos nuevos",
        "valencia": 0.9,
    },
    "reflexiva": {
        "descripcion": "Alta coherencia y estabilidad, contemplando patrones",
        "valencia": 0.4,
    },
    "inquieta": {
        "descripcion": "Multiples sesgos detectados, necesita diversificar",
        "valencia": -0.2,
    },
}

# Efectos: factores multiplicativos para ajustar_curiosidad()
EFECTOS = {
    "inspirada": {"puente": 1.3, "prediccion": 1.3},
    "curiosa": {},
    "aburrida": {"serendipia": 1.5, "prediccion": 1.3},
    "enfocada": {},
    "melancolica": {"revitalizar": 1.4},
    "asombrada": {"exploracion_externa": 1.4},
    "reflexiva": {"introspeccion": 1.3},
    "inquieta": {"serendipia": 1.4},
}


class MotorEmocional:
    """Evalua y registra el estado emocional de IANAE."""

    def __init__(self):
        self._historial: List[Dict[str, Any]] = []

    def evaluar(
        self,
        pulso: Dict[str, Any],
        crecimiento: Dict[str, Any],
        sesgos: List[Dict],
        superficie: float,
        coherencia: float,
        novedad: float,
    ) -> Dict[str, Any]:
        """Determina el estado emocional actual."""
        emocion, intensidad = self._resolver(
            pulso, crecimiento, sesgos, superficie, coherencia, novedad
        )
        info = EMOCIONES[emocion]
        resultado = {
            "emocion": emocion,
            "intensidad": round(intensidad, 4),
            "valencia": info["valencia"],
            "descripcion": info["descripcion"],
            "efectos": EFECTOS.get(emocion, {}),
        }
        self._historial.append({"timestamp": time.time(), **resultado})
        # Limit history
        if len(self._historial) > 200:
            self._historial = self._historial[-200:]
        return resultado

    def _resolver(
        self,
        pulso: Dict[str, Any],
        crecimiento: Dict[str, Any],
        sesgos: List[Dict],
        superficie: float,
        coherencia: float,
        novedad: float,
    ) -> tuple:
        """Priority-based emotion resolution. Returns (emocion, intensidad)."""
        energia = pulso.get("energia", 0.5)
        estado_base = pulso.get("estado", "curiosa")
        racha = pulso.get("racha", 0)
        tendencia = crecimiento.get("tendencia", "estable")

        # High priority: asombrada — very high novedad + high surface
        if novedad > 0.6 and superficie > 0.6:
            return "asombrada", min(1.0, (novedad + superficie) / 2)

        # Inquieta: multiple sesgos
        if len(sesgos) >= 2:
            return "inquieta", min(1.0, len(sesgos) * 0.3)

        # Melancolica: decaying + low energy
        if tendencia == "decayendo" and energia < 0.4:
            return "melancolica", min(1.0, (0.4 - energia) * 2 + 0.3)

        # Reflexiva: high coherencia + stable
        if coherencia > 0.5 and tendencia == "estable":
            return "reflexiva", min(1.0, coherencia)

        # Enfocada: racha >= 3 on interesting
        if racha >= 3 and estado_base == "enfocada":
            return "enfocada", min(1.0, 0.5 + racha * 0.1)

        # Inspirada: base estado
        if estado_base == "inspirada":
            return "inspirada", min(1.0, energia + 0.2)

        # Aburrida: base estado
        if estado_base == "aburrida":
            return "aburrida", min(1.0, 0.4 + (1.0 - energia) * 0.4)

        # Default: curiosa
        return "curiosa", 0.5

    def historial(self, ultimos: int = 20) -> List[Dict[str, Any]]:
        """Ultimas N emociones registradas."""
        return self._historial[-ultimos:]

    def emocion_dominante(self, ultimos: int = 10) -> Optional[str]:
        """Emocion mas frecuente en los ultimos N registros."""
        recientes = self._historial[-ultimos:]
        if not recientes:
            return None
        counter = Counter(e["emocion"] for e in recientes)
        return counter.most_common(1)[0][0]
