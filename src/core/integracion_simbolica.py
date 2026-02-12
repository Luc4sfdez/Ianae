"""
Integracion entre pensamiento difuso (ConceptosLucas) y simbolico (ThoughtTree).

Puente bidireccional: convierte entre representaciones difusas (vectores numpy)
y simbolicas (arboles de ThoughtNode).
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from src.core.pensamiento_simbolico import ThoughtNode, ThoughtTree


class IntegradorSimbolico:
    """
    Puente entre el sistema difuso (nucleo) y el simbolico (ThoughtTree).
    """

    def __init__(self, nucleo):
        """
        Args:
            nucleo: instancia de ConceptosLucas.
        """
        self.nucleo = nucleo

    def simbolico_a_difuso(self, node: ThoughtNode) -> Dict:
        """
        Convertir ThoughtNode a representacion difusa compatible con ConceptosLucas.

        Args:
            node: ThoughtNode a convertir.

        Returns:
            Dict con formato de concepto difuso.
        """
        return {
            "actual": node.vector,
            "base": node.vector.copy(),
            "activaciones": int(node.activation * 10),
            "ultima_activacion": 0,
            "categoria": "simbolico",
            "fuerza": node.coherence,
        }

    def difuso_a_simbolico(self, nombre_concepto: str) -> Optional[ThoughtNode]:
        """
        Convertir concepto difuso del nucleo a ThoughtNode.

        Args:
            nombre_concepto: nombre del concepto en el nucleo.

        Returns:
            ThoughtNode o None si no existe.
        """
        if nombre_concepto not in self.nucleo.conceptos:
            return None

        data = self.nucleo.conceptos[nombre_concepto]
        vector = data["actual"]

        # Normalizar activacion a [0, 1]
        activacion = min(1.0, data.get("activaciones", 0) / 10.0)

        return ThoughtNode(
            concept_id=nombre_concepto,
            activation=max(0.01, activacion),  # Minimo para validacion
            vector=vector if len(vector) == 15 else np.pad(
                vector, (0, 15 - len(vector))
            )[:15],
            coherence=data.get("fuerza", 0.5),
            origin="propagation",
        )

    def ejecutar_pensamiento_hibrido(self, tema: str,
                                      profundidad: int = 3) -> Dict:
        """
        Ejecutar pensamiento hibrido: difuso + simbolico.

        1. Activar propagacion difusa desde el tema.
        2. Construir arbol simbolico desde las activaciones.
        3. Podar por coherencia y evaluar.

        Args:
            tema: concepto semilla.
            profundidad: pasos de propagacion.

        Returns:
            Dict con resultados hibridos.
        """
        if tema not in self.nucleo.conceptos:
            return {
                "error": f"Concepto '{tema}' no existe",
                "modo": "hibrido",
            }

        # Fase 1: Propagacion difusa
        resultados_difusos = self.nucleo.activar(tema, pasos=profundidad)
        activaciones_finales = resultados_difusos[-1] if resultados_difusos else {}

        # Fase 2: Construir nodos simbolicos desde top activados
        top_conceptos = sorted(
            activaciones_finales.items(), key=lambda x: x[1], reverse=True
        )[:10]

        nodos_simbolicos = []
        for nombre, activacion in top_conceptos:
            if activacion > 0.05 and nombre in self.nucleo.conceptos:
                vector = self.nucleo.conceptos[nombre]["actual"]
                # Pad/trim a 15 dims para ThoughtNode
                if len(vector) != 15:
                    vector = np.pad(vector, (0, max(0, 15 - len(vector))))[:15]
                node = ThoughtNode(
                    concept_id=nombre,
                    activation=min(1.0, max(0.01, activacion)),
                    vector=vector,
                    coherence=0.5,
                    origin="propagation",
                    depth=0,
                )
                nodos_simbolicos.append(node)

        # Fase 3: Evaluar coherencia simbolica
        if len(nodos_simbolicos) >= 2:
            coherencia_media = np.mean([n.coherence for n in nodos_simbolicos])
            activacion_media = np.mean([n.activation for n in nodos_simbolicos])
        else:
            coherencia_media = 1.0
            activacion_media = 0.0

        # Representacion simbolica
        simbolico = " -> ".join(
            f"{n.concept_id}({n.activation:.2f})" for n in nodos_simbolicos[:5]
        )

        return {
            "modo": "hibrido",
            "tema": tema,
            "profundidad": profundidad,
            "activaciones_difusas": activaciones_finales,
            "nodos_simbolicos": len(nodos_simbolicos),
            "coherencia_media": float(coherencia_media),
            "activacion_media": float(activacion_media),
            "representacion_simbolica": simbolico,
            "conceptos_activados": [n.concept_id for n in nodos_simbolicos],
        }
