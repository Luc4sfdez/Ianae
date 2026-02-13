"""
Organismo IANAE — Fase 7+8: Nacimiento y Evolucion.

Clase unificada que ensambla todos los subsistemas en un organismo vivo.
Un solo despertar() arranca todo. Los suenos prometedores retroalimentan
la curiosidad. Las conversaciones persisten y alimentan el aprendizaje.
El motor de evolucion auto-ajusta parametros, persiste estado entre
reinicios, y percibe archivos nuevos del entorno.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IANAE:
    """El organismo completo. Un solo punto de entrada."""

    def __init__(
        self,
        dim_vector: int = 15,
        diario_path: str = "data/diario_ianae.jsonl",
        objetivos_path: str = "data/objetivos_ianae.json",
        conversaciones_path: str = "data/conversaciones_ianae.jsonl",
        snapshot_dir: str = "data/snapshots",
        estado_path: str = "data/estado_ianae.json",
        percepcion_dir: Optional[str] = None,
        intervalo_base: float = 2.0,
        consolidar_cada: int = 20,
    ):
        from src.core.nucleo import ConceptosLucas, crear_universo_lucas
        from src.core.emergente import PensamientoLucas
        from src.core.insights import InsightsEngine
        from src.core.vida_autonoma import VidaAutonoma
        from src.core.consciencia import Consciencia
        from src.core.suenos import MotorSuenos
        from src.core.dialogo import DialogoIANAE
        from src.core.evolucion import MotorEvolucion

        # 1. Nucleo
        self.sistema = crear_universo_lucas()
        self.sistema.crear_relaciones_lucas()

        # 2. Pensamiento
        self.pensamiento = PensamientoLucas(self.sistema)

        # 3. Insights
        self.insights = InsightsEngine(self.sistema, self.pensamiento)

        # 4. Vida autonoma
        self.vida = VidaAutonoma(
            self.sistema,
            self.pensamiento,
            self.insights,
            intervalo_base=intervalo_base,
            diario_path=diario_path,
            consolidar_cada=consolidar_cada,
            snapshot_dir=snapshot_dir,
        )

        # 5. Consciencia
        self.consciencia = Consciencia(
            self.vida,
            objetivos_path=objetivos_path,
        )

        # 6. Suenos
        self.suenos = MotorSuenos(self.sistema, self.pensamiento)

        # 7. Dialogo
        self.dialogo = DialogoIANAE(self.consciencia)

        # 8. Evolucion
        self.evolucion = MotorEvolucion(
            self,
            estado_path=estado_path,
            percepcion_dir=percepcion_dir,
        )

        # Persistencia de conversaciones
        self._conversaciones_path = conversaciones_path
        self._nacido = time.time()

    # ------------------------------------------------------------------
    # Clase alternativa: crear desde componentes existentes
    # ------------------------------------------------------------------

    @classmethod
    def desde_componentes(
        cls,
        sistema,
        diario_path: str = "data/diario_ianae.jsonl",
        objetivos_path: str = "data/objetivos_ianae.json",
        conversaciones_path: str = "data/conversaciones_ianae.jsonl",
        snapshot_dir: str = "data/snapshots",
        estado_path: str = "data/estado_ianae.json",
        percepcion_dir: Optional[str] = None,
        intervalo_base: float = 2.0,
        consolidar_cada: int = 20,
    ) -> "IANAE":
        """Crea un IANAE desde un sistema existente (para tests)."""
        from src.core.emergente import PensamientoLucas
        from src.core.insights import InsightsEngine
        from src.core.vida_autonoma import VidaAutonoma
        from src.core.consciencia import Consciencia
        from src.core.suenos import MotorSuenos
        from src.core.dialogo import DialogoIANAE
        from src.core.evolucion import MotorEvolucion

        inst = object.__new__(cls)
        inst.sistema = sistema
        inst.pensamiento = PensamientoLucas(sistema)
        inst.insights = InsightsEngine(sistema, inst.pensamiento)
        inst.vida = VidaAutonoma(
            sistema, inst.pensamiento, inst.insights,
            intervalo_base=intervalo_base,
            diario_path=diario_path,
            consolidar_cada=consolidar_cada,
            snapshot_dir=snapshot_dir,
        )
        inst.consciencia = Consciencia(inst.vida, objetivos_path=objetivos_path)
        inst.suenos = MotorSuenos(sistema, inst.pensamiento)
        inst.dialogo = DialogoIANAE(inst.consciencia)
        inst.evolucion = MotorEvolucion(
            inst, estado_path=estado_path, percepcion_dir=percepcion_dir,
        )
        inst._conversaciones_path = conversaciones_path
        inst._nacido = time.time()
        return inst

    # ------------------------------------------------------------------
    # Despertar
    # ------------------------------------------------------------------

    def despertar(self, max_ciclos: Optional[int] = None) -> List[Dict]:
        """Arranca el organismo completo. max_ciclos=None → infinito."""
        logger.info("IANAE despierta.")

        # Cargar estado previo si existe
        estado_previo = self.evolucion.cargar_estado()
        if estado_previo:
            logger.info("Estado previo restaurado (gen=%d).",
                         self.evolucion._generacion)

        resultados: List[Dict] = []

        from src.core.recovery import RecoveryManager
        recovery = RecoveryManager(self.sistema, snapshot_dir=self.vida.snapshot_dir)

        self.vida._corriendo = True
        ciclo = 0

        while self.vida._corriendo:
            if max_ciclos is not None and ciclo >= max_ciclos:
                break
            if recovery.shutdown_requested:
                recovery.guardar_snapshot(motivo="shutdown")
                break

            resultado = self.ciclo_completo()
            resultados.append(resultado)
            ciclo += 1

            recovery.check_auto_save()

            pausa = self.vida._descansar(
                resultado.get("vida", {}).get("reflexion", {})
            )
            if pausa > 0 and self.vida._corriendo:
                time.sleep(pausa)

        logger.info("IANAE duerme tras %d ciclos.", ciclo)
        return resultados

    # ------------------------------------------------------------------
    # Ciclo completo: consciencia + suenos retroalimentados
    # ------------------------------------------------------------------

    def ciclo_completo(self) -> Dict[str, Any]:
        """Un ciclo con todas las capas integradas."""
        ts = time.time()

        # 1. Percibir entorno (archivos nuevos)
        percepciones = self.evolucion.percibir()

        # 2. Inyectar suenos prometedores como curiosidad
        self._retroalimentar_suenos()

        # 3. Ciclo consciente (ya cierra circuito internamente)
        resultado_consciente = self.consciencia.ciclo_consciente()

        # 4. Sonar con lo descubierto (imaginar extensiones)
        sueno = self._sonar_desde_descubrimiento(resultado_consciente)

        # 5. Evolucionar cada 10 ciclos
        evolucion_resultado = None
        if self.vida._ciclo_actual % 10 == 0 and self.vida._ciclo_actual > 0:
            evolucion_resultado = self.evolucion.evolucionar()
            self.evolucion.guardar_estado()

        return {
            "timestamp": ts,
            **resultado_consciente,
            "sueno": sueno,
            "percepciones": percepciones,
            "evolucion": evolucion_resultado,
        }

    # ------------------------------------------------------------------
    # Hablar (con persistencia y feedback)
    # ------------------------------------------------------------------

    def hablar(self, mensaje: str) -> str:
        """IANAE responde y aprende de la conversacion."""
        resultado = self.dialogo.responder(mensaje)

        # Persistir conversacion
        self._persistir_conversacion(mensaje, resultado)

        # Retroalimentar: conceptos mencionados por Lucas son relevantes
        self._aprender_de_conversacion(resultado)

        return resultado["respuesta"]

    def preguntar(self, pregunta: str) -> Dict[str, Any]:
        """Como hablar() pero retorna dict completo."""
        resultado = self.dialogo.responder(pregunta)
        self._persistir_conversacion(pregunta, resultado)
        self._aprender_de_conversacion(resultado)
        return resultado

    # ------------------------------------------------------------------
    # Sonar (con retroalimentacion)
    # ------------------------------------------------------------------

    def imaginar(self, hipotesis: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper sobre MotorSuenos.sonar()."""
        return self.suenos.sonar(hipotesis)

    def _retroalimentar_suenos(self) -> None:
        """Inyecta suenos prometedores como boost de curiosidad."""
        prometedores = self.suenos.suenos_prometedores(umbral=0.5)
        if not prometedores:
            return

        # Ultimo sueno prometedor: boostear sus conceptos
        ultimo = prometedores[-1]
        hipotesis = ultimo.get("hipotesis", {})
        conceptos_sueno = []

        if "a" in hipotesis and "b" in hipotesis:
            conceptos_sueno = [hipotesis["a"], hipotesis["b"]]
        elif "conectar_a" in hipotesis:
            conceptos_sueno = hipotesis.get("conectar_a", [])

        # Boost: activar conceptos del sueno para que aparezcan en curiosidad
        for c in conceptos_sueno:
            if c in self.sistema.conceptos:
                try:
                    self.sistema.activar(c, pasos=1, temperatura=0.05)
                except Exception:
                    pass

    def _sonar_desde_descubrimiento(self, resultado: Dict) -> Optional[Dict]:
        """Despues de un ciclo, imagina una extension."""
        vida = resultado.get("vida", {})
        curiosidad = vida.get("curiosidad", {})
        concepto = curiosidad.get("concepto", "")
        reflexion = vida.get("reflexion", {})

        # Solo sonar si fue interesante
        if reflexion.get("veredicto") not in ("revelador", "interesante"):
            return None

        if concepto not in self.sistema.conceptos:
            return None

        # Buscar un vecino para imaginar conexion nueva
        vecinos = [v for v, _ in self.sistema.relaciones.get(concepto, [])]
        no_conectados = [
            c for c in self.sistema.conceptos
            if c != concepto and c not in vecinos
        ]

        if not no_conectados:
            return None

        import random
        candidato = random.choice(no_conectados[:5])
        return self.suenos.imaginar_conexion(concepto, candidato)

    # ------------------------------------------------------------------
    # Aprendizaje desde conversacion
    # ------------------------------------------------------------------

    def _aprender_de_conversacion(self, resultado: Dict) -> None:
        """Conceptos mencionados por Lucas son relevantes → boost."""
        conceptos = resultado.get("conceptos_detectados", [])
        for c in conceptos:
            if c in self.sistema.conceptos:
                try:
                    self.sistema.activar(c, pasos=1, temperatura=0.05)
                except Exception:
                    pass

    def _persistir_conversacion(self, mensaje: str, resultado: Dict) -> None:
        """Guarda conversacion a .jsonl."""
        directorio = os.path.dirname(self._conversaciones_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
        entrada = {
            "timestamp": time.time(),
            "mensaje": mensaje,
            "respuesta": resultado.get("respuesta", ""),
            "conceptos": resultado.get("conceptos_detectados", []),
            "coherencia": resultado.get("coherencia", 0.0),
        }
        with open(self._conversaciones_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def estado(self) -> Dict[str, Any]:
        """Estado completo del organismo."""
        return {
            "nacido": self._nacido,
            "edad_s": round(time.time() - self._nacido, 2),
            "conceptos": len(self.sistema.conceptos),
            "relaciones": self.sistema.grafo.number_of_edges(),
            "ciclo_actual": self.vida._ciclo_actual,
            "generacion": self.evolucion._generacion,
            "pulso": self.consciencia.pulso(),
            "superficie": self.consciencia.superficie(),
            "corrientes": self.consciencia.corrientes(),
            "objetivos_pendientes": len([
                o for o in self.consciencia.leer_objetivos()
                if o.get("progreso", 0) < 1.0
            ]),
            "suenos_prometedores": len(self.suenos.suenos_prometedores()),
            "conversaciones": len(self.dialogo.historial()),
            "archivos_percibidos": len(self.evolucion.archivos_percibidos()),
        }

    def leer_conversaciones(self, ultimas: int = 10) -> List[Dict]:
        """Lee ultimas N conversaciones persistidas."""
        if not os.path.exists(self._conversaciones_path):
            return []
        lineas: List[Dict] = []
        with open(self._conversaciones_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        lineas.append(json.loads(linea))
                    except json.JSONDecodeError:
                        continue
        return lineas[-ultimas:]

    def detener(self) -> None:
        """Para el organismo."""
        self.vida.detener()
