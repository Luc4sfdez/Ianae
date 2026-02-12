"""
Motor de Suenos de IANAE — Fase 6: Imaginacion.

IANAE simula hipotesis en un grafo sandbox antes de actuar sobre el real.
Imagina conexiones, conceptos y escenarios; evalua su valor; decide si
perseguirlos o descartarlos. Pasa de explorar a IMAGINAR.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MotorSuenos:
    """Simula hipotesis en un sandbox sin tocar el grafo real."""

    def __init__(self, sistema, pensamiento):
        self.sistema = sistema
        self.pensamiento = pensamiento
        self._historial_suenos: List[Dict] = []

    # ------------------------------------------------------------------
    # Publico
    # ------------------------------------------------------------------

    def sonar(self, hipotesis: Dict[str, Any]) -> Dict[str, Any]:
        """Simula una hipotesis y retorna evaluacion.

        hipotesis: dict con 'tipo' ('conexion' | 'concepto') y parametros.
          - conexion: {'tipo': 'conexion', 'a': str, 'b': str, 'fuerza': float}
          - concepto: {'tipo': 'concepto', 'nombre': str, 'categoria': str,
                       'conectar_a': List[str]}
        """
        tipo = hipotesis.get("tipo")
        if tipo == "conexion":
            return self.imaginar_conexion(
                hipotesis["a"], hipotesis["b"],
                fuerza=hipotesis.get("fuerza", 0.7),
            )
        elif tipo == "concepto":
            return self.imaginar_concepto(
                hipotesis["nombre"],
                hipotesis.get("categoria", "emergentes"),
                hipotesis.get("conectar_a", []),
            )
        return {"error": f"Tipo de hipotesis desconocido: {tipo}"}

    def imaginar_conexion(
        self, concepto_a: str, concepto_b: str, fuerza: float = 0.7
    ) -> Dict[str, Any]:
        """Que pasaria si A y B estuvieran conectados?"""
        ts = time.time()

        if concepto_a not in self.sistema.conceptos:
            return self._sueno_fallido(f"'{concepto_a}' no existe en el sistema")
        if concepto_b not in self.sistema.conceptos:
            return self._sueno_fallido(f"'{concepto_b}' no existe en el sistema")

        # Medir estado actual (sin la conexion)
        baseline_a = self._medir_activacion(concepto_a)
        baseline_b = self._medir_activacion(concepto_b)

        # Crear sandbox y aplicar hipotesis
        sandbox = self._crear_sandbox()
        sandbox.relacionar(concepto_a, concepto_b, fuerza=fuerza)

        # Medir en sandbox
        sandbox_a = self._medir_activacion_en(sandbox, concepto_a)
        sandbox_b = self._medir_activacion_en(sandbox, concepto_b)

        # Evaluar
        evaluacion = self._evaluar_sueno(
            baseline_a, baseline_b, sandbox_a, sandbox_b
        )

        resultado = {
            "tipo": "conexion",
            "hipotesis": {"a": concepto_a, "b": concepto_b, "fuerza": fuerza},
            "baseline": {"a": baseline_a, "b": baseline_b},
            "simulacion": {"a": sandbox_a, "b": sandbox_b},
            "evaluacion": evaluacion,
            "timestamp": ts,
        }

        self._historial_suenos.append(resultado)
        return resultado

    def imaginar_concepto(
        self,
        nombre: str,
        categoria: str = "emergentes",
        conectar_a: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Que pasaria si existiera un nuevo concepto?"""
        ts = time.time()
        conectar_a = conectar_a or []

        # Verificar que los conceptos destino existen
        existentes = [c for c in conectar_a if c in self.sistema.conceptos]
        if not existentes:
            return self._sueno_fallido("Ningun concepto destino existe en el sistema")

        # Baseline: medir vecinos antes
        baselines = {}
        for c in existentes:
            baselines[c] = self._medir_activacion(c)

        # Sandbox
        sandbox = self._crear_sandbox()
        sandbox.añadir_concepto(nombre, categoria=categoria)
        for c in existentes:
            sandbox.relacionar(nombre, c, fuerza=0.7)

        # Simular activacion del nuevo concepto
        sandbox_activaciones = {}
        try:
            resultados = sandbox.activar(nombre, pasos=3)
            sandbox_activaciones = resultados[-1] if resultados else {}
        except Exception:
            pass

        # Medir vecinos despues
        sandbox_vecinos = {}
        for c in existentes:
            sandbox_vecinos[c] = self._medir_activacion_en(sandbox, c)

        # Evaluar impacto
        impacto_total = 0.0
        for c in existentes:
            base = baselines[c]
            post = sandbox_vecinos[c]
            delta_coh = post.get("coherencia", 0) - base.get("coherencia", 0)
            delta_act = post.get("activacion_max", 0) - base.get("activacion_max", 0)
            impacto_total += delta_coh + delta_act

        impacto_normalizado = min(1.0, max(0.0, impacto_total / max(len(existentes), 1)))

        if impacto_normalizado > 0.3:
            veredicto = "prometedor"
        elif impacto_normalizado > 0.1:
            veredicto = "posible"
        else:
            veredicto = "descartable"

        resultado = {
            "tipo": "concepto",
            "hipotesis": {
                "nombre": nombre,
                "categoria": categoria,
                "conectar_a": existentes,
            },
            "activaciones_nuevo": sandbox_activaciones,
            "impacto": round(impacto_normalizado, 4),
            "veredicto": veredicto,
            "timestamp": ts,
        }

        self._historial_suenos.append(resultado)
        return resultado

    def suenos_prometedores(self, umbral: float = 0.3) -> List[Dict]:
        """Retorna suenos que valieron la pena."""
        resultados = []
        for s in self._historial_suenos:
            ev = s.get("evaluacion", {})
            impacto = ev.get("impacto", s.get("impacto", 0))
            if impacto >= umbral:
                resultados.append(s)
        return resultados

    def historial(self, ultimos: int = 10) -> List[Dict]:
        """Ultimos N suenos."""
        return self._historial_suenos[-ultimos:]

    # ------------------------------------------------------------------
    # Sandbox
    # ------------------------------------------------------------------

    def _crear_sandbox(self):
        """Crea copia del sistema para simulacion segura."""
        from src.core.nucleo import ConceptosLucas

        sandbox = ConceptosLucas(
            dim_vector=self.sistema.dim_vector,
            incertidumbre_base=0.0,
        )

        # Copiar conceptos
        for nombre, datos in self.sistema.conceptos.items():
            sandbox.añadir_concepto(
                nombre,
                atributos=datos["actual"].copy(),
                categoria=datos.get("categoria", "emergentes"),
            )

        # Copiar relaciones
        for origen, vecinos in self.sistema.relaciones.items():
            for destino, fuerza in vecinos:
                if destino in sandbox.conceptos and origen in sandbox.conceptos:
                    # Evitar duplicados: solo una direccion
                    ya_existe = any(
                        d == destino for d, _ in sandbox.relaciones.get(origen, [])
                    )
                    if not ya_existe:
                        sandbox.relacionar(origen, destino, fuerza=fuerza, bidireccional=False)

        return sandbox

    # ------------------------------------------------------------------
    # Medicion
    # ------------------------------------------------------------------

    def _medir_activacion(self, concepto: str) -> Dict[str, Any]:
        """Mide activacion de un concepto en el sistema real."""
        return self._medir_activacion_en(self.sistema, concepto)

    def _medir_activacion_en(self, sistema, concepto: str) -> Dict[str, Any]:
        """Mide activacion de un concepto en un sistema dado."""
        if concepto not in sistema.conceptos:
            return {"activacion_max": 0.0, "coherencia": 0.0, "alcance": 0}

        try:
            resultados = sistema.activar(concepto, pasos=2, temperatura=0.1)
            activaciones = resultados[-1] if resultados else {}
        except Exception:
            return {"activacion_max": 0.0, "coherencia": 0.0, "alcance": 0}

        if not activaciones:
            return {"activacion_max": 0.0, "coherencia": 0.0, "alcance": 0}

        valores = list(activaciones.values())
        activacion_max = max(valores) if valores else 0.0
        alcance = sum(1 for v in valores if v > 0.1)

        # Coherencia: desviacion estandar inversa (mas uniforme = mas coherente)
        if len(valores) > 1:
            std = float(np.std(valores))
            coherencia = max(0.0, 1.0 - std * 2)
        else:
            coherencia = 0.5

        return {
            "activacion_max": round(float(activacion_max), 4),
            "coherencia": round(coherencia, 4),
            "alcance": alcance,
        }

    # ------------------------------------------------------------------
    # Evaluacion
    # ------------------------------------------------------------------

    def _evaluar_sueno(
        self,
        baseline_a: Dict, baseline_b: Dict,
        sandbox_a: Dict, sandbox_b: Dict,
    ) -> Dict[str, Any]:
        """Compara sandbox vs baseline para evaluar el valor del sueno."""
        delta_coh_a = sandbox_a.get("coherencia", 0) - baseline_a.get("coherencia", 0)
        delta_coh_b = sandbox_b.get("coherencia", 0) - baseline_b.get("coherencia", 0)
        delta_alc_a = sandbox_a.get("alcance", 0) - baseline_a.get("alcance", 0)
        delta_alc_b = sandbox_b.get("alcance", 0) - baseline_b.get("alcance", 0)

        impacto_coherencia = (delta_coh_a + delta_coh_b) / 2
        impacto_alcance = (delta_alc_a + delta_alc_b) / 2

        impacto = impacto_coherencia * 0.6 + min(1.0, impacto_alcance / 3) * 0.4
        impacto = round(min(1.0, max(0.0, impacto + 0.5)), 4)  # Centrar en 0.5

        if impacto > 0.6:
            veredicto = "perseguir"
        elif impacto > 0.4:
            veredicto = "considerar"
        else:
            veredicto = "descartar"

        return {
            "impacto": impacto,
            "delta_coherencia": round((delta_coh_a + delta_coh_b) / 2, 4),
            "delta_alcance": round((delta_alc_a + delta_alc_b) / 2, 4),
            "veredicto": veredicto,
        }

    def _sueno_fallido(self, razon: str) -> Dict[str, Any]:
        """Retorna resultado de sueno que no pudo ejecutarse."""
        return {
            "tipo": "fallido",
            "razon": razon,
            "evaluacion": {"impacto": 0.0, "veredicto": "descartar"},
        }
