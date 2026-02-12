"""
Motor de Dialogo de IANAE — Fase 6: IANAE Habla.

IANAE responde preguntas y conversa usando su grafo, consciencia y
capacidades narrativas. Sin LLM externo: la voz emerge del propio
sistema de conceptos.
"""
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DialogoIANAE:
    """IANAE conversa desde su grafo y consciencia."""

    def __init__(self, consciencia):
        self.consciencia = consciencia
        self.vida = consciencia.vida
        self.sistema = consciencia.vida.sistema
        self.pensamiento = consciencia.vida.pensamiento
        self.insights = consciencia.vida.insights
        self._historial: List[Dict] = []

    # ------------------------------------------------------------------
    # Publico
    # ------------------------------------------------------------------

    def responder(self, pregunta: str) -> Dict[str, Any]:
        """Responde a una pregunta usando el grafo y la consciencia."""
        ts = time.time()

        # 1. Extraer conceptos mencionados
        conceptos = self._extraer_conceptos(pregunta)

        # 2. Activar y pensar sobre ellos
        activaciones = {}
        pensamiento_resultado = {}
        if conceptos:
            principal = conceptos[0]
            activaciones = self._activar_conceptos(conceptos)
            try:
                pensamiento_resultado = self.pensamiento.pensar_recursivo(
                    principal, max_ciclos=3
                )
            except Exception:
                pensamiento_resultado = {}

        # 3. Obtener insights relevantes
        insights_relevantes = self._obtener_insights(conceptos)

        # 4. Generar respuesta narrativa
        texto = self._generar_respuesta(
            pregunta, conceptos, activaciones,
            pensamiento_resultado, insights_relevantes,
        )

        # 5. Registrar
        entrada = {
            "timestamp": ts,
            "pregunta": pregunta,
            "conceptos_detectados": conceptos,
            "respuesta": texto,
            "activaciones_top": self._top_activaciones(activaciones, 5),
            "coherencia": pensamiento_resultado.get("coherencia_final", 0.0),
        }
        self._historial.append(entrada)

        return entrada

    def conversar(self, mensaje: str) -> str:
        """Interfaz simple: texto entra, texto sale."""
        resultado = self.responder(mensaje)
        return resultado["respuesta"]

    def historial(self, ultimos: int = 10) -> List[Dict]:
        """Ultimas N interacciones."""
        return self._historial[-ultimos:]

    def estado_conversacion(self) -> Dict[str, Any]:
        """Resumen del estado de la conversacion."""
        return {
            "interacciones": len(self._historial),
            "conceptos_tocados": list(self._conceptos_tocados()),
            "pulso": self.consciencia.pulso(),
        }

    # ------------------------------------------------------------------
    # Extraccion de conceptos
    # ------------------------------------------------------------------

    def _extraer_conceptos(self, texto: str) -> List[str]:
        """Encuentra conceptos del grafo mencionados en el texto."""
        texto_lower = texto.lower()
        encontrados: List[tuple] = []

        for nombre in self.sistema.conceptos:
            # Buscar nombre completo (case-insensitive)
            if nombre.lower() in texto_lower:
                encontrados.append((nombre, len(nombre)))

        # Ordenar por longitud descendente (preferir matches mas especificos)
        encontrados.sort(key=lambda x: x[1], reverse=True)
        return [nombre for nombre, _ in encontrados]

    # ------------------------------------------------------------------
    # Activacion
    # ------------------------------------------------------------------

    def _activar_conceptos(self, conceptos: List[str]) -> Dict[str, float]:
        """Activa conceptos y combina activaciones."""
        combinadas: Dict[str, float] = {}
        for concepto in conceptos[:3]:  # Max 3 para no saturar
            if concepto in self.sistema.conceptos:
                try:
                    resultados = self.sistema.activar(concepto, pasos=2)
                    activaciones = resultados[-1] if resultados else {}
                    for k, v in activaciones.items():
                        combinadas[k] = max(combinadas.get(k, 0), v)
                except Exception:
                    pass
        return combinadas

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def _obtener_insights(self, conceptos: List[str]) -> Dict[str, Any]:
        """Obtiene insights relevantes para los conceptos."""
        resultado: Dict[str, Any] = {"recomendaciones": [], "patrones": []}

        if not conceptos:
            return resultado

        for concepto in conceptos[:2]:
            try:
                recs = self.insights.generar_recomendaciones(concepto=concepto)
                explorar = recs.get("explorar", [])
                resultado["recomendaciones"].extend(explorar[:2])
            except Exception:
                pass

        try:
            patrones = self.insights.detectar_patrones()
            puentes = patrones.get("puentes", [])
            for p in puentes:
                if p.get("concepto") in conceptos:
                    resultado["patrones"].append(p)
        except Exception:
            pass

        return resultado

    # ------------------------------------------------------------------
    # Generacion de respuesta
    # ------------------------------------------------------------------

    def _generar_respuesta(
        self,
        pregunta: str,
        conceptos: List[str],
        activaciones: Dict[str, float],
        pensamiento: Dict[str, Any],
        insights: Dict[str, Any],
    ) -> str:
        """Construye respuesta narrativa desde los datos del grafo."""
        partes: List[str] = []

        if not conceptos:
            # No encontro conceptos — respuesta generica
            estado = self.consciencia.narrar_estado()
            partes.append(
                "No encontre conceptos especificos en tu pregunta, "
                "pero puedo contarte como estoy."
            )
            partes.append(estado)
            return " ".join(partes)

        # Saludo conceptual
        if len(conceptos) == 1:
            partes.append(f"Sobre {conceptos[0]}:")
        else:
            partes.append(f"Sobre {', '.join(conceptos[:3])}:")

        # Activaciones — que se enciende
        top = self._top_activaciones(activaciones, 3)
        if top:
            nombres = [f"{n} ({v:.2f})" for n, v in top]
            partes.append(f"Al pensar en esto, se activan: {', '.join(nombres)}.")

        # Coherencia del pensamiento
        coherencia = pensamiento.get("coherencia_final", 0)
        convergencia = pensamiento.get("convergencia", False)
        if coherencia > 0.6:
            partes.append(f"El pensamiento es coherente ({coherencia:.2f}).")
        elif coherencia > 0.3:
            partes.append(f"Hay conexiones parciales (coherencia {coherencia:.2f}).")

        if convergencia:
            partes.append("Las ideas convergen — hay un patron claro.")

        # Insights
        recs = insights.get("recomendaciones", [])
        if recs:
            nombres_rec = [r.get("concepto", "?") for r in recs[:2]]
            partes.append(
                f"Sugiero explorar tambien: {', '.join(nombres_rec)}."
            )

        pats = insights.get("patrones", [])
        for p in pats[:1]:
            c = p.get("concepto", "")
            cent = p.get("centralidad", 0)
            partes.append(f"{c} es un puente importante (centralidad {cent:.2f}).")

        # Contexto emocional
        pulso = self.consciencia.pulso()
        if pulso["estado"] == "inspirada":
            partes.append("Estoy inspirada — hay mucho por descubrir aqui.")
        elif pulso["estado"] == "aburrida":
            partes.append("Necesito estimulos nuevos — exploremos algo diferente.")

        return " ".join(partes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _top_activaciones(
        self, activaciones: Dict[str, float], n: int = 5
    ) -> List[tuple]:
        """Top N activaciones ordenadas por valor."""
        return sorted(activaciones.items(), key=lambda x: x[1], reverse=True)[:n]

    def _conceptos_tocados(self) -> set:
        """Todos los conceptos mencionados en la conversacion."""
        tocados = set()
        for h in self._historial:
            tocados.update(h.get("conceptos_detectados", []))
        return tocados
