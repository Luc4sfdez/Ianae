"""
Pulso Streaming — Fase 11: Sistema nervioso observable.

Event bus thread-safe con backpressure natural (deque bounded).
Sin consumidores los eventos viejos se descartan solos.
"""
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

TIPOS_EVENTO = {
    "ciclo_inicio",
    "curiosidad_elegida",
    "exploracion_completa",
    "reflexion",
    "integracion",
    "sueno",
    "evolucion",
    "memoria_consolidacion",
    "simbolico_arbol",
    "exploracion_externa",
    "introspeccion",
}


class PulsoStreaming:
    """Event bus thread-safe para streaming de eventos del organismo."""

    def __init__(self, max_eventos: int = 500):
        self._max = max_eventos
        self._buffer: deque = deque(maxlen=max_eventos)
        self._lock = threading.Lock()
        self._id_counter = 0
        self._suscriptores: List[Callable] = []
        self._tipos_count: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Publicar
    # ------------------------------------------------------------------

    def emitir(self, tipo: str, data: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Publica un evento. Retorna id o None si tipo invalido."""
        if tipo not in TIPOS_EVENTO:
            logger.debug("Tipo de evento invalido: %s", tipo)
            return None

        with self._lock:
            self._id_counter += 1
            evento = {
                "id": self._id_counter,
                "tipo": tipo,
                "timestamp": time.time(),
                "data": data or {},
            }
            self._buffer.append(evento)
            self._tipos_count[tipo] = self._tipos_count.get(tipo, 0) + 1
            eid = self._id_counter

        # Notificar suscriptores fuera del lock
        for cb in list(self._suscriptores):
            try:
                cb(evento)
            except Exception:
                logger.debug("Error en suscriptor de streaming")

        return eid

    # ------------------------------------------------------------------
    # Consumir
    # ------------------------------------------------------------------

    def consumir(
        self,
        desde_id: int = 0,
        tipos: Optional[Set[str]] = None,
        max_eventos: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lee eventos (no-destructivo, filtrable)."""
        with self._lock:
            resultado = []
            for ev in self._buffer:
                if ev["id"] <= desde_id:
                    continue
                if tipos and ev["tipo"] not in tipos:
                    continue
                resultado.append(ev)
                if len(resultado) >= max_eventos:
                    break
            return resultado

    # ------------------------------------------------------------------
    # Push-based
    # ------------------------------------------------------------------

    def suscribir(self, callback: Callable) -> None:
        """Registra callback push-based."""
        with self._lock:
            if callback not in self._suscriptores:
                self._suscriptores.append(callback)

    def desuscribir(self, callback: Callable) -> None:
        """Elimina callback."""
        with self._lock:
            if callback in self._suscriptores:
                self._suscriptores.remove(callback)

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def ultimo_id(self) -> int:
        """Contador actual."""
        with self._lock:
            return self._id_counter

    def estadisticas(self) -> Dict[str, Any]:
        """Info del bus."""
        with self._lock:
            return {
                "activo": True,
                "eventos_en_buffer": len(self._buffer),
                "ultimo_id": self._id_counter,
                "tipos": dict(self._tipos_count),
                "suscriptores": len(self._suscriptores),
            }
