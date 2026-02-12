"""
Consolidador periodico para IANAE.

Ejecuta ciclos de consolidacion que:
- Corren ciclo_vital() para activar y auto-modificar
- Consolidan memoria asociativa (decay de memorias debiles)
- Decaen conceptos sin activacion reciente
- Ejecutan genesis si hay candidatos
- Guardan snapshot automatico antes de cada consolidacion
- Registran metricas de crecimiento
"""
import time
import logging
import threading
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class Consolidador:
    """
    Ejecuta consolidacion periodica del sistema IANAE.

    Combina ciclo_vital + memoria + decay + genesis en un solo ciclo.
    """

    def __init__(self, sistema, memoria=None, aprendizaje=None,
                 intervalo_min: float = 5.0,
                 ciclos_por_consolidacion: int = 3,
                 snapshot_dir: Optional[str] = None,
                 on_consolidacion: Optional[Callable] = None):
        """
        Args:
            sistema: instancia de ConceptosLucas
            memoria: instancia de MemoriaAsociativaV2 (opcional)
            aprendizaje: instancia de AprendizajeRefuerzo (opcional)
            intervalo_min: minutos entre consolidaciones
            ciclos_por_consolidacion: ciclos vitales por consolidacion
            snapshot_dir: directorio para snapshots (None = no guardar)
            on_consolidacion: callback tras cada consolidacion
        """
        self.sistema = sistema
        self.memoria = memoria
        self.aprendizaje = aprendizaje
        self.intervalo_min = intervalo_min
        self.ciclos_por_consolidacion = ciclos_por_consolidacion
        self.snapshot_dir = snapshot_dir
        self.on_consolidacion = on_consolidacion

        # Estado
        self._historial: List[Dict] = []
        self._running = False
        self._timer: Optional[threading.Timer] = None

    def consolidar(self) -> Dict:
        """
        Ejecuta un ciclo completo de consolidacion.

        Returns:
            Dict con metricas del ciclo
        """
        t_inicio = time.time()
        metricas = {
            "timestamp": t_inicio,
            "conceptos_antes": len(self.sistema.conceptos),
            "aristas_antes": self.sistema.grafo.number_of_edges(),
        }

        # 1. Snapshot antes de consolidar
        if self.snapshot_dir:
            try:
                ruta = f"{self.snapshot_dir}/pre_consolidacion_{int(t_inicio)}.json"
                self.sistema.guardar(ruta)
                metricas["snapshot"] = ruta
                logger.info("Snapshot guardado: %s", ruta)
            except Exception as e:
                logger.warning("Error guardando snapshot: %s", e)
                metricas["snapshot_error"] = str(e)

        # 2. Ciclo vital
        resultados_vital = self.sistema.ciclo_vital(
            num_ciclos=self.ciclos_por_consolidacion,
            auto_mod=True
        )
        metricas["ciclos_ejecutados"] = len(resultados_vital)

        # 3. Consolidar memoria asociativa
        memorias_eliminadas = 0
        if self.memoria:
            memorias_eliminadas = self.memoria.consolidar()
        metricas["memorias_eliminadas"] = memorias_eliminadas

        # 4. Decaer conceptos sin activacion reciente
        decaidos = self._decaer_inactivos()
        metricas["conceptos_decaidos"] = decaidos

        # 5. Genesis si hay candidatos
        nuevos_genesis = []
        try:
            nuevos_genesis = self.sistema.ciclo_genesis(max_nuevos=2)
        except Exception as e:
            logger.debug("Genesis sin candidatos: %s", e)
        metricas["genesis_creados"] = len(nuevos_genesis)
        metricas["genesis_nombres"] = nuevos_genesis

        # 6. Aprendizaje por refuerzo — fin de episodio
        if self.aprendizaje:
            self.aprendizaje.fin_episodio()

        # Metricas finales
        metricas["conceptos_despues"] = len(self.sistema.conceptos)
        metricas["aristas_despues"] = self.sistema.grafo.number_of_edges()
        metricas["conceptos_delta"] = metricas["conceptos_despues"] - metricas["conceptos_antes"]
        metricas["aristas_delta"] = metricas["aristas_despues"] - metricas["aristas_antes"]
        metricas["tiempo_s"] = round(time.time() - t_inicio, 3)

        self._historial.append(metricas)

        logger.info(
            "Consolidacion #%d: conceptos %d->%d (%+d), genesis=%d, decay=%d, %.2fs",
            len(self._historial),
            metricas["conceptos_antes"], metricas["conceptos_despues"],
            metricas["conceptos_delta"], len(nuevos_genesis),
            decaidos, metricas["tiempo_s"]
        )

        if self.on_consolidacion:
            self.on_consolidacion(metricas)

        return metricas

    def _decaer_inactivos(self, umbral_ciclos: int = 50,
                           factor_decay: float = 0.9) -> int:
        """
        Reduce la fuerza de conceptos sin activacion reciente.

        Args:
            umbral_ciclos: ciclos sin activacion para empezar a decaer
            factor_decay: factor multiplicativo de decay

        Returns:
            Numero de conceptos afectados
        """
        edad_actual = self.sistema.metricas.get("edad", 0)
        decaidos = 0

        for nombre, data in list(self.sistema.conceptos.items()):
            ultima = data.get("ultima_activacion", 0)
            inactividad = edad_actual - ultima

            if inactividad > umbral_ciclos and data.get("fuerza", 1.0) > 0.1:
                data["fuerza"] = max(0.05, data["fuerza"] * factor_decay)
                decaidos += 1

        return decaidos

    # --- Ejecucion periodica ---

    def iniciar(self):
        """Inicia consolidacion periodica en background."""
        self._running = True
        self._programar_siguiente()
        logger.info("Consolidador iniciado (cada %.1f min)", self.intervalo_min)

    def detener(self):
        """Detiene la consolidacion periodica."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Consolidador detenido")

    def _programar_siguiente(self):
        """Programa el siguiente ciclo de consolidacion."""
        if not self._running:
            return
        self._timer = threading.Timer(
            self.intervalo_min * 60,
            self._ciclo_periodico
        )
        self._timer.daemon = True
        self._timer.start()

    def _ciclo_periodico(self):
        """Ejecuta consolidacion y programa la siguiente."""
        if not self._running:
            return
        try:
            self.consolidar()
        except Exception as e:
            logger.error("Error en consolidacion periodica: %s", e)
        self._programar_siguiente()

    # --- Metricas ---

    def estadisticas(self) -> Dict:
        """Retorna estadisticas de consolidacion."""
        if not self._historial:
            return {
                "consolidaciones": 0,
                "conceptos_delta_total": 0,
                "genesis_total": 0,
                "decay_total": 0,
            }

        return {
            "consolidaciones": len(self._historial),
            "conceptos_delta_total": sum(h["conceptos_delta"] for h in self._historial),
            "genesis_total": sum(h["genesis_creados"] for h in self._historial),
            "decay_total": sum(h["conceptos_decaidos"] for h in self._historial),
            "memorias_eliminadas_total": sum(h["memorias_eliminadas"] for h in self._historial),
            "tiempo_total_s": round(sum(h["tiempo_s"] for h in self._historial), 3),
            "ultima_consolidacion": self._historial[-1]["timestamp"],
        }

    @property
    def historial(self) -> List[Dict]:
        """Historial completo de consolidaciones."""
        return list(self._historial)

    def metricas_crecimiento(self) -> Dict:
        """Calcula metricas de crecimiento del sistema."""
        if len(self._historial) < 2:
            return {"crecimiento": "insuficientes_datos"}

        primero = self._historial[0]
        ultimo = self._historial[-1]
        tiempo_total_h = (ultimo["timestamp"] - primero["timestamp"]) / 3600

        if tiempo_total_h <= 0:
            return {"crecimiento": "insuficiente_tiempo"}

        conceptos_nuevos = ultimo["conceptos_despues"] - primero["conceptos_antes"]
        aristas_nuevas = ultimo["aristas_despues"] - primero["aristas_antes"]

        return {
            "conceptos_por_hora": round(conceptos_nuevos / tiempo_total_h, 2),
            "aristas_por_hora": round(aristas_nuevas / tiempo_total_h, 2),
            "genesis_por_hora": round(
                sum(h["genesis_creados"] for h in self._historial) / tiempo_total_h, 2
            ),
            "horas_monitoreadas": round(tiempo_total_h, 2),
            "consolidaciones": len(self._historial),
        }
