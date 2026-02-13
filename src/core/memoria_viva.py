"""
Memoria Viva — Fase 10: Memoria persistente entre ciclos.

Compone 2 instancias de MemoriaAsociativaV2 (sin modificarla):
- Episodica: ciclos vividos (clave = "ciclo:{concepto}:{tipo}")
- Semantica: relaciones descubiertas (clave = "relacion:{a}:{b}")

Provee deja vu, novedad y consolidacion a VidaAutonoma.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoriaViva:
    """Memoria viva de dos capas: episodica + semantica."""

    def __init__(
        self,
        capacidad_episodica: int = 200,
        capacidad_semantica: int = 300,
        decaimiento: float = 0.95,
    ):
        from src.core.memoria_v2 import MemoriaAsociativaV2

        self._episodica = MemoriaAsociativaV2(
            capacidad=capacidad_episodica, decaimiento=decaimiento
        )
        self._semantica = MemoriaAsociativaV2(
            capacidad=capacidad_semantica, decaimiento=decaimiento
        )

    # ------------------------------------------------------------------
    # Almacenar
    # ------------------------------------------------------------------

    def recordar_ciclo(
        self,
        concepto: str,
        tipo: str,
        score: float,
        veredicto: str,
        ciclo: int,
    ) -> None:
        """Almacena resultado de un ciclo de vida."""
        clave = f"ciclo:{concepto}:{tipo}"
        valor = {
            "concepto": concepto,
            "tipo": tipo,
            "score": score,
            "veredicto": veredicto,
            "ciclo": ciclo,
        }
        self._episodica.almacenar(clave, valor, fuerza=min(1.0, score + 0.3))

    def recordar_relacion(
        self,
        a: str,
        b: str,
        fuerza: float,
        contexto: str = "",
    ) -> None:
        """Almacena relacion descubierta (orden canonico)."""
        ca, cb = sorted([a, b])
        clave = f"relacion:{ca}:{cb}"
        valor = {
            "a": ca,
            "b": cb,
            "fuerza": fuerza,
            "contexto": contexto,
        }
        self._semantica.almacenar(clave, valor, fuerza=min(1.0, fuerza))

    # ------------------------------------------------------------------
    # Consultar
    # ------------------------------------------------------------------

    def detectar_deja_vu(self, concepto: str) -> Dict[str, Any]:
        """Revisa si un concepto fue explorado recientemente.

        Returns:
            {deja_vu: bool, recuerdos: list, factor_ajuste: float}
        """
        similares = self._episodica.buscar_similares(f"ciclo:{concepto}", top_k=5)

        if not similares:
            return {"deja_vu": False, "recuerdos": [], "factor_ajuste": 1.3}

        fuerza_max = max(f for _, f in similares)

        if fuerza_max > 0.7:
            factor = 0.5  # deja vu fuerte → penalizar
        elif fuerza_max > 0.3:
            factor = 0.8  # visto pero debil
        else:
            factor = 1.3  # apenas recordado → bonus novedad

        return {
            "deja_vu": True,
            "recuerdos": [{"clave": k, "fuerza": round(f, 4)} for k, f in similares],
            "factor_ajuste": factor,
        }

    def conceptos_novedosos(
        self, candidatos: List[str], top_k: int = 5
    ) -> List[str]:
        """Ordena candidatos por novedad (menos en memoria primero)."""
        scored: List[tuple] = []
        for c in candidatos:
            similares = self._episodica.buscar_similares(f"ciclo:{c}", top_k=1)
            fuerza = similares[0][1] if similares else 0.0
            scored.append((c, fuerza))

        scored.sort(key=lambda x: x[1])
        return [c for c, _ in scored[:top_k]]

    # ------------------------------------------------------------------
    # Post-ciclo
    # ------------------------------------------------------------------

    def almacenar_descubrimiento(
        self,
        concepto: str,
        tipo: str,
        score: float,
        veredicto: str,
        ciclo: int,
        conexiones_nuevas: int = 0,
        simbolico: Optional[Dict] = None,
    ) -> None:
        """Guarda ciclo completo + insight simbolico si existe."""
        self.recordar_ciclo(concepto, tipo, score, veredicto, ciclo)

        # Si hay coherencia simbolica alta, recordar como relacion
        if simbolico and simbolico.get("coherencia_simbolica", 0) > 0.4:
            hibrido = simbolico.get("hibrido", {})
            conceptos_activados = hibrido.get("conceptos_activados", [])
            for otro in conceptos_activados[:3]:
                if otro != concepto:
                    self.recordar_relacion(
                        concepto,
                        otro,
                        fuerza=simbolico["coherencia_simbolica"],
                        contexto=f"ciclo:{ciclo}",
                    )

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------

    def consolidar(self) -> Dict[str, int]:
        """Limpia memorias decaidas."""
        ep = self._episodica.consolidar()
        sem = self._semantica.consolidar()
        return {"episodicas_eliminadas": ep, "semanticas_eliminadas": sem}

    def estadisticas(self) -> Dict[str, Any]:
        """Stats de ambas capas."""
        ep = self._episodica.estadisticas()
        sem = self._semantica.estadisticas()
        return {
            "episodica": ep,
            "semantica": sem,
            "total_memorias": ep["total"] + sem["total"],
            "total_activas": ep["activas"] + sem["activas"],
        }

    # ------------------------------------------------------------------
    # Exportar / Importar — persistencia completa
    # ------------------------------------------------------------------

    def exportar(self) -> Dict[str, Any]:
        """Exporta ambas capas para persistencia."""
        raw_ep = self._episodica.exportar()
        raw_sem = self._semantica.exportar()
        # Convertir tuplas a listas para JSON
        ep = {k: [v[0], v[1], v[2]] for k, v in raw_ep.items()}
        sem = {k: [v[0], v[1], v[2]] for k, v in raw_sem.items()}
        return {"episodica": ep, "semantica": sem}

    def importar(self, datos: Dict[str, Any]) -> None:
        """Restaura ambas capas desde datos exportados."""
        raw_ep = datos.get("episodica", {})
        raw_sem = datos.get("semantica", {})
        # Reconstruir tuplas
        ep = {k: (v[0], v[1], v[2]) for k, v in raw_ep.items()}
        sem = {k: (v[0], v[1], v[2]) for k, v in raw_sem.items()}
        self._episodica.importar(ep)
        self._semantica.importar(sem)
