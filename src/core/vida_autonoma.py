"""
Ciclo Autonomo de IANAE — Fase 4: IANAE Vive Sola.

VidaAutonoma compone (sin modificar) ConceptosLucas, PensamientoLucas,
InsightsEngine, Consolidador y RecoveryManager para ejecutar un bucle
continuo de curiosidad dirigida, exploracion, reflexion e integracion.
"""
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TEMPLATES = {
    "gap": [
        "Que conceptos de {categoria} podrian fortalecerse?",
        "Como conectar {concepto} con areas mas activas?",
    ],
    "revitalizar": [
        "Por que {concepto} ha perdido activacion?",
        "Que nuevas conexiones podrian revitalizar {concepto}?",
    ],
    "puente": [
        "Que comunidades conecta {concepto}?",
        "Que pasaria si se fortalecen las conexiones de {concepto}?",
    ],
    "prediccion": [
        "Cual es el potencial no explorado de {concepto}?",
        "Como se relaciona {concepto} con los conceptos mas activos?",
    ],
    "serendipia": [
        "Que descubrimientos inesperados surgen de {concepto}?",
    ],
}

TIPOS_CURIOSIDAD = {"gap", "revitalizar", "puente", "prediccion", "serendipia"}


class VidaAutonoma:
    """Bucle autonomo de vida: curiosidad -> explorar -> reflexionar -> integrar."""

    def __init__(
        self,
        sistema,
        pensamiento,
        insights,
        intervalo_base: float = 2.0,
        diario_path: str = "data/diario_ianae.jsonl",
        consolidar_cada: int = 20,
        snapshot_dir: str = "data/snapshots",
        pensamiento_profundo=None,
        memoria_viva=None,
        pulso_streaming=None,
    ):
        self.sistema = sistema
        self.pensamiento = pensamiento
        self.insights = insights
        self.intervalo_base = intervalo_base
        self.diario_path = diario_path
        self.consolidar_cada = consolidar_cada
        self.snapshot_dir = snapshot_dir

        # Fase 9/10/11: subsistemas opcionales
        self.pensamiento_profundo = pensamiento_profundo
        self.memoria_viva = memoria_viva
        self.pulso_streaming = pulso_streaming

        self._corriendo = False
        self._ciclo_actual = 0

        # Ajustes externos de curiosidad (circuito cerrado con Consciencia)
        self._ajustes_curiosidad: Dict[str, float] = {}

        # Lazy: se crean solo si vivir() arranca
        self._consolidador = None
        self._recovery = None

    # ------------------------------------------------------------------
    # Publico
    # ------------------------------------------------------------------

    def vivir(self, max_ciclos: Optional[int] = None) -> List[Dict]:
        """Bucle principal. max_ciclos=None → infinito."""
        from src.core.consolidador import Consolidador
        from src.core.recovery import RecoveryManager

        self._consolidador = Consolidador(
            self.sistema,
            snapshot_dir=self.snapshot_dir,
            ciclos_por_consolidacion=3,
        )
        self._recovery = RecoveryManager(
            self.sistema,
            snapshot_dir=self.snapshot_dir,
        )

        self._corriendo = True
        resultados: List[Dict] = []

        while self._corriendo:
            if max_ciclos is not None and self._ciclo_actual >= max_ciclos:
                break

            if self._recovery.shutdown_requested:
                self._recovery.guardar_snapshot(motivo="shutdown")
                break

            resultado = self.ejecutar_ciclo()
            resultados.append(resultado)

            # Consolidacion periodica
            if self._ciclo_actual % self.consolidar_cada == 0 and self._ciclo_actual > 0:
                try:
                    self._consolidador.consolidar()
                except Exception:
                    logger.exception("Error en consolidacion ciclo %d", self._ciclo_actual)

            # Auto-save
            if self._recovery is not None:
                self._recovery.check_auto_save()

            # Descanso adaptativo
            pausa = self._descansar(resultado.get("reflexion", {}))
            if pausa > 0 and self._corriendo:
                time.sleep(pausa)

        return resultados

    def ejecutar_ciclo(self) -> Dict[str, Any]:
        """Un ciclo completo (testeable sin bucle)."""
        self._ciclo_actual += 1
        ts = time.time()

        # Fase 11: streaming ciclo_inicio
        if self.pulso_streaming is not None:
            try:
                self.pulso_streaming.emitir("ciclo_inicio", {"ciclo": self._ciclo_actual})
            except Exception:
                pass

        curiosidad = self._curiosidad()

        if self.pulso_streaming is not None:
            try:
                self.pulso_streaming.emitir("curiosidad_elegida", {
                    "concepto": curiosidad.get("concepto", ""),
                    "tipo": curiosidad.get("tipo", ""),
                })
            except Exception:
                pass

        pregunta = self._preguntar(curiosidad)
        respuesta = self._explorar(curiosidad)

        if self.pulso_streaming is not None:
            try:
                self.pulso_streaming.emitir("exploracion_completa", {
                    "concepto": curiosidad.get("concepto", ""),
                    "coherencia": respuesta.get("coherencia", 0.0),
                })
            except Exception:
                pass

        reflexion = self._reflexionar(respuesta)

        if self.pulso_streaming is not None:
            try:
                self.pulso_streaming.emitir("reflexion", {
                    "score": reflexion.get("score", 0),
                    "veredicto": reflexion.get("veredicto", ""),
                })
            except Exception:
                pass

        integracion = self._integrar(reflexion, respuesta)

        if self.pulso_streaming is not None:
            try:
                self.pulso_streaming.emitir("integracion", {
                    "auto_mod": integracion.get("auto_mod", False),
                    "genesis": integracion.get("genesis", 0),
                })
            except Exception:
                pass

        # Fase 9: simbolico en diario
        simbolico = respuesta.get("simbolico", {})

        if self.pulso_streaming is not None and simbolico:
            try:
                self.pulso_streaming.emitir("simbolico_arbol", {
                    "coherencia_simbolica": simbolico.get("coherencia_simbolica", 0),
                    "nodos_totales": simbolico.get("nodos_totales", 0),
                })
            except Exception:
                pass

        # Fase 10: almacenar en memoria viva
        if self.memoria_viva is not None:
            try:
                self.memoria_viva.almacenar_descubrimiento(
                    concepto=curiosidad.get("concepto", ""),
                    tipo=curiosidad.get("tipo", ""),
                    score=reflexion.get("score", 0.0),
                    veredicto=reflexion.get("veredicto", "rutinario"),
                    ciclo=self._ciclo_actual,
                    conexiones_nuevas=respuesta.get("conexiones_nuevas", 0),
                    simbolico=simbolico if simbolico else None,
                )
            except Exception:
                pass

            # Consolidar cada 10 ciclos
            if self._ciclo_actual % 10 == 0:
                try:
                    consolidado = self.memoria_viva.consolidar()
                    if self.pulso_streaming is not None:
                        self.pulso_streaming.emitir("memoria_consolidacion", consolidado)
                except Exception:
                    pass

        entrada_diario = {
            "ciclo": self._ciclo_actual,
            "timestamp": ts,
            "curiosidad": curiosidad,
            "pregunta": pregunta,
            "descubrimientos": {
                "conexiones_nuevas": respuesta.get("conexiones_nuevas", 0),
                "coherencia": respuesta.get("coherencia", 0.0),
                "convergencia": respuesta.get("convergencia", False),
            },
            "reflexion": reflexion,
            "integracion": integracion,
            "simbolico": simbolico,
        }
        self._registrar_diario(entrada_diario)

        return entrada_diario

    def detener(self) -> None:
        """Para el bucle desde fuera."""
        self._corriendo = False

    def estado(self) -> Dict[str, Any]:
        """Resumen del estado actual."""
        return {
            "ciclo_actual": self._ciclo_actual,
            "corriendo": self._corriendo,
            "conceptos": len(self.sistema.conceptos),
            "intervalo_base": self.intervalo_base,
        }

    def leer_diario(self, ultimos: int = 10) -> List[Dict]:
        """Lee ultimas N entradas del diario."""
        if not os.path.exists(self.diario_path):
            return []
        lineas: List[Dict] = []
        with open(self.diario_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        lineas.append(json.loads(linea))
                    except json.JSONDecodeError:
                        continue
        return lineas[-ultimos:]

    # ------------------------------------------------------------------
    # Curiosidad dirigida
    # ------------------------------------------------------------------

    def _curiosidad(self) -> Dict[str, Any]:
        """Decide QUE pensar, dirigido por insights."""
        conceptos_sistema = list(self.sistema.conceptos.keys())
        if not conceptos_sistema:
            return self._curiosidad_fallback()

        candidatos: List[Dict[str, Any]] = []

        try:
            predictivo = self.insights.analisis_predictivo()
        except Exception:
            predictivo = {"gaps_conocimiento": [], "tendencias": [], "proximas_tecnologias": []}

        try:
            patrones = self.insights.detectar_patrones()
        except Exception:
            patrones = {"puentes": []}

        # Gaps
        for gap in predictivo.get("gaps_conocimiento", []):
            concepto = gap.get("categoria", "")
            # Buscar un concepto real de esa categoria
            miembros = self.sistema.categorias.get(concepto, [])
            if miembros:
                elegido = random.choice(miembros)
                candidatos.append({
                    "tipo": "gap",
                    "concepto": elegido,
                    "motivacion": f"Gap en categoria {concepto}",
                    "prioridad": float(gap.get("deficit", 0.5)),
                    "categoria": concepto,
                })

        # Revitalizar (tendencias descendentes)
        for tend in predictivo.get("tendencias", []):
            if tend.get("direccion") == "descendente":
                c = tend.get("concepto", "")
                if c in self.sistema.conceptos:
                    freq = float(tend.get("frecuencia", 0.5))
                    candidatos.append({
                        "tipo": "revitalizar",
                        "concepto": c,
                        "motivacion": f"{c} pierde activacion (freq={freq:.2f})",
                        "prioridad": 1.0 - freq,
                    })

        # Puentes
        for puente in patrones.get("puentes", []):
            c = puente.get("concepto", "")
            if c in self.sistema.conceptos:
                candidatos.append({
                    "tipo": "puente",
                    "concepto": c,
                    "motivacion": f"{c} es puente (centralidad={puente.get('centralidad', 0):.2f})",
                    "prioridad": float(puente.get("centralidad", 0.5)),
                })

        # Predicciones
        for pred in predictivo.get("proximas_tecnologias", []):
            c = pred.get("concepto", "")
            if c in self.sistema.conceptos:
                candidatos.append({
                    "tipo": "prediccion",
                    "concepto": c,
                    "motivacion": f"Potencial no explorado de {c}",
                    "prioridad": float(pred.get("score", pred.get("score_prediccion", 0.5))),
                })

        # Serendipia (15% probabilidad)
        if random.random() < 0.15 or not candidatos:
            elegido = random.choice(conceptos_sistema)
            candidatos.append({
                "tipo": "serendipia",
                "concepto": elegido,
                "motivacion": f"Exploracion aleatoria de {elegido}",
                "prioridad": 0.5,
            })

        # Fase 10: Memory deja vu
        if self.memoria_viva is not None:
            for c in candidatos:
                try:
                    dv = self.memoria_viva.detectar_deja_vu(c["concepto"])
                    c["prioridad"] *= dv["factor_ajuste"]
                except Exception:
                    pass

        # Elegir con ruido + ajustes externos (circuito cerrado)
        for c in candidatos:
            factor = self._ajustes_curiosidad.get(c["tipo"], 1.0)
            c["prioridad"] = max(0.0, c["prioridad"] * factor + random.uniform(-0.1, 0.1))

        mejor = max(candidatos, key=lambda x: x["prioridad"])
        return mejor

    def _curiosidad_fallback(self) -> Dict[str, Any]:
        """Fallback cuando el grafo esta vacio."""
        return {
            "tipo": "serendipia",
            "concepto": "desconocido",
            "motivacion": "Grafo vacio, exploracion basica",
            "prioridad": 0.1,
        }

    # ------------------------------------------------------------------
    # Preguntar
    # ------------------------------------------------------------------

    def _preguntar(self, curiosidad: Dict[str, Any]) -> str:
        """Formula pregunta desde templates."""
        tipo = curiosidad.get("tipo", "serendipia")
        concepto = curiosidad.get("concepto", "desconocido")
        categoria = curiosidad.get("categoria", "general")

        plantillas = TEMPLATES.get(tipo, TEMPLATES["serendipia"])
        plantilla = random.choice(plantillas)
        return plantilla.format(concepto=concepto, categoria=categoria)

    # ------------------------------------------------------------------
    # Explorar
    # ------------------------------------------------------------------

    def _explorar(self, curiosidad: Dict[str, Any]) -> Dict[str, Any]:
        """Propaga + pensamiento recursivo."""
        concepto = curiosidad.get("concepto", "")

        if concepto not in self.sistema.conceptos:
            return {
                "activaciones": {},
                "coherencia": 0.0,
                "convergencia": False,
                "conexiones_nuevas": 0,
            }

        # Propagar
        try:
            resultados_act = self.sistema.activar(concepto, pasos=3)
            activaciones = resultados_act[-1] if resultados_act else {}
        except Exception:
            activaciones = {}

        # Pensar recursivo
        try:
            pensado = self.pensamiento.pensar_recursivo(concepto, max_ciclos=3)
        except Exception:
            pensado = {"coherencia_final": 0.0, "convergencia": False, "activaciones_finales": {}}

        # Conexiones inesperadas
        conexiones_nuevas = 0
        try:
            act_final = pensado.get("activaciones_finales", activaciones)
            if act_final:
                inesperadas = self.pensamiento._detectar_conexiones_inesperadas(act_final)
                conexiones_nuevas = len(inesperadas)
        except Exception:
            pass

        # Recomendaciones
        try:
            self.insights.generar_recomendaciones(concepto=concepto)
        except Exception:
            pass

        # Fase 9: Pensamiento profundo
        simbolico = {}
        if self.pensamiento_profundo is not None and concepto in self.sistema.conceptos:
            try:
                simbolico = self.pensamiento_profundo.profundizar(
                    concepto,
                    pensado.get("activaciones_finales", activaciones),
                )
            except Exception:
                pass

        return {
            "activaciones": pensado.get("activaciones_finales", activaciones),
            "coherencia": float(pensado.get("coherencia_final", 0.0)),
            "convergencia": bool(pensado.get("convergencia", False)),
            "conexiones_nuevas": conexiones_nuevas,
            "simbolico": simbolico,
        }

    # ------------------------------------------------------------------
    # Reflexionar
    # ------------------------------------------------------------------

    def _reflexionar(self, respuesta: Dict[str, Any]) -> Dict[str, Any]:
        """Score 0-1 de lo descubierto."""
        coherencia = float(respuesta.get("coherencia", 0.0))
        conexiones = int(respuesta.get("conexiones_nuevas", 0))
        convergencia = bool(respuesta.get("convergencia", False))

        novedad = min(1.0, conexiones / 3.0) if conexiones > 0 else 0.0
        score = novedad * 0.3 + coherencia * 0.4 + (0.3 if convergencia else 0.0)

        # Fase 9: bonus simbolico (hasta +0.1)
        coherencia_simb = float(respuesta.get("simbolico", {}).get("coherencia_simbolica", 0.0))
        if coherencia_simb > 0:
            score += coherencia_simb * 0.1

        score = round(min(1.0, max(0.0, score)), 4)

        if score > 0.7:
            veredicto = "revelador"
        elif score > 0.4:
            veredicto = "interesante"
        else:
            veredicto = "rutinario"

        return {"score": score, "veredicto": veredicto}

    # ------------------------------------------------------------------
    # Integrar
    # ------------------------------------------------------------------

    def _integrar(self, reflexion: Dict[str, Any], respuesta: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-modifica, genesis, aprendizaje segun score."""
        score = reflexion.get("score", 0.0)
        conexiones = int(respuesta.get("conexiones_nuevas", 0))

        hizo_auto_mod = False
        genesis_creados = 0
        hizo_aprendizaje = False

        # Auto-modificar si score alto
        if score > 0.5:
            try:
                self.sistema.auto_modificar(fuerza=0.1)
                hizo_auto_mod = True
            except Exception:
                pass

        # Genesis si hay novedad
        if conexiones > 0:
            try:
                nuevos = self.sistema.ciclo_genesis(max_nuevos=1)
                genesis_creados = len(nuevos) if nuevos else 0
            except Exception:
                pass

        # Siempre aprender
        try:
            self.sistema.aprender_de_experiencia()
            hizo_aprendizaje = True
        except Exception:
            pass

        return {
            "auto_mod": hizo_auto_mod,
            "genesis": genesis_creados,
            "aprendizaje": hizo_aprendizaje,
        }

    # ------------------------------------------------------------------
    # Diario
    # ------------------------------------------------------------------

    def _registrar_diario(self, entrada: Dict[str, Any]) -> None:
        """Append a .jsonl."""
        directorio = os.path.dirname(self.diario_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
        with open(self.diario_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")

    # ------------------------------------------------------------------
    # Descanso adaptativo
    # ------------------------------------------------------------------

    def _descansar(self, reflexion: Dict[str, Any]) -> float:
        """Retorna segundos de pausa segun veredicto."""
        veredicto = reflexion.get("veredicto", "rutinario")
        factores = {"revelador": 0.5, "interesante": 1.0, "rutinario": 2.0}
        factor = factores.get(veredicto, 1.0)
        return self.intervalo_base * factor
