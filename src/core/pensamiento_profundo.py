"""
Pensamiento Profundo — Fase 9: Razonamiento simbolico conectado al organismo.

Compone ThoughtTree + IntegradorSimbolico (sin modificarlos) para dar a
VidaAutonoma la capacidad de construir arboles de pensamiento, podarlos
y evaluar coherencia simbolica despues de cada exploracion.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PensamientoProfundo:
    """Razonamiento profundo: arboles + integracion simbolica."""

    def __init__(self, nucleo):
        self.nucleo = nucleo
        self._ultimo_arbol = None

    def profundizar(self, concepto: str, activaciones: Optional[Dict] = None) -> Dict[str, Any]:
        """Construye arbol simbolico, poda, evalua coherencia.

        Llamado DESPUES de _explorar() en VidaAutonoma.
        """
        from src.core.pensamiento_simbolico import ThoughtTree
        from src.core.integracion_simbolica import IntegradorSimbolico

        if concepto not in self.nucleo.conceptos:
            return self._resultado_vacio()

        try:
            arbol = ThoughtTree(concepto, self.nucleo)
        except Exception:
            logger.debug("ThoughtTree fallo para '%s'", concepto)
            return self._resultado_vacio()

        nodos_antes = len(arbol.get_all_nodes())

        try:
            arbol.prune(min_coherence=0.3)
        except Exception:
            pass

        nodos_despues = len(arbol.get_all_nodes())

        try:
            coherencia = arbol.evaluate_coherence()
        except Exception:
            coherencia = 0.0

        try:
            representacion = arbol.to_symbolic()
        except Exception:
            representacion = "ErrorSymbolic"

        try:
            stats = arbol.depth_stats()
        except Exception:
            stats = {}

        # Profundidad maxima
        profundidad_max = max(stats.keys()) if stats else 0

        # Hibrido
        integrador = IntegradorSimbolico(self.nucleo)
        try:
            hibrido = integrador.ejecutar_pensamiento_hibrido(concepto)
        except Exception:
            hibrido = {}

        self._ultimo_arbol = arbol

        return {
            "coherencia_simbolica": float(coherencia),
            "profundidad_max": int(profundidad_max),
            "nodos_totales": nodos_despues,
            "nodos_podados": max(0, nodos_antes - nodos_despues),
            "representacion_simbolica": representacion,
            "depth_stats": stats,
            "hibrido": hibrido,
        }

    @property
    def ultimo_arbol(self):
        """Ultimo arbol construido (para cross-system use)."""
        return self._ultimo_arbol

    @staticmethod
    def _resultado_vacio() -> Dict[str, Any]:
        return {
            "coherencia_simbolica": 0.0,
            "profundidad_max": 0,
            "nodos_totales": 0,
            "nodos_podados": 0,
            "representacion_simbolica": "",
            "depth_stats": {},
            "hibrido": {},
        }
