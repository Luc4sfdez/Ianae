"""
Aprendizaje por refuerzo simple para IANAE.

Q-learning con epsilon-greedy para optimizar pesos de propagacion
entre conceptos basandose en la utilidad de las activaciones.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional


class AprendizajeRefuerzo:
    """
    Sistema Q-learning para ajustar dinamicamente pesos de propagacion.

    Mantiene una Q-table sobre pares (concepto_origen, concepto_destino)
    y ajusta los pesos segun recompensas observadas tras cada propagacion.
    """

    def __init__(self, alpha: float = 0.1, gamma: float = 0.9,
                 epsilon: float = 0.2, epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01):
        """
        Args:
            alpha: tasa de aprendizaje Q-learning.
            gamma: factor de descuento.
            epsilon: probabilidad de exploracion inicial.
            epsilon_decay: factor de decaimiento de epsilon por episodio.
            epsilon_min: epsilon minimo.
        """
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        # Q-table: (origen, destino) -> q_value
        self.q_table: Dict[Tuple[str, str], float] = {}

        # Historial de recompensas
        self.historial_recompensas: List[float] = []
        self.episodios = 0

    def get_q(self, origen: str, destino: str) -> float:
        """Obtener Q-value para un par."""
        return self.q_table.get((origen, destino), 0.0)

    def seleccionar_accion(self, origen: str, vecinos: List[str]) -> str:
        """
        Seleccionar siguiente concepto con epsilon-greedy.

        Args:
            origen: concepto actual.
            vecinos: lista de conceptos destino posibles.

        Returns:
            Concepto seleccionado.
        """
        if not vecinos:
            return origen

        if np.random.random() < self.epsilon:
            # Exploracion: elegir aleatorio
            return vecinos[np.random.randint(len(vecinos))]

        # Explotacion: elegir el de mayor Q-value
        q_values = [self.get_q(origen, v) for v in vecinos]
        max_q = max(q_values)
        # Si hay empate, elegir aleatorio entre los mejores
        mejores = [v for v, q in zip(vecinos, q_values) if q == max_q]
        return mejores[np.random.randint(len(mejores))]

    def actualizar(self, origen: str, destino: str, recompensa: float,
                   siguientes_vecinos: Optional[List[str]] = None):
        """
        Actualizar Q-value con la ecuacion de Q-learning.

        Q(s,a) = Q(s,a) + alpha * (r + gamma * max_Q(s',a') - Q(s,a))

        Args:
            origen: concepto origen (estado).
            destino: concepto destino (accion).
            recompensa: recompensa observada.
            siguientes_vecinos: vecinos del destino para calcular max futuro.
        """
        q_actual = self.get_q(origen, destino)

        # Mejor Q futuro desde el destino
        max_q_futuro = 0.0
        if siguientes_vecinos:
            max_q_futuro = max(
                (self.get_q(destino, v) for v in siguientes_vecinos),
                default=0.0
            )

        # Q-learning update
        q_nuevo = q_actual + self.alpha * (
            recompensa + self.gamma * max_q_futuro - q_actual
        )
        self.q_table[(origen, destino)] = q_nuevo

    def calcular_recompensa(self, activaciones: Dict[str, float],
                            conceptos_utiles: int,
                            diversidad: float) -> float:
        """
        Calcular recompensa para una propagacion.

        Args:
            activaciones: dict concepto -> nivel de activacion.
            conceptos_utiles: numero de conceptos con activacion > 0.2.
            diversidad: ratio de categorias distintas activadas.

        Returns:
            Recompensa en rango [-1, 1].
        """
        # Recompensa positiva por conceptos utiles (no demasiados, no pocos)
        optimo = 5
        utilidad = 1.0 - abs(conceptos_utiles - optimo) / max(optimo, 1)

        # Recompensa por diversidad (categorias cruzadas)
        diversidad_bonus = diversidad * 0.5

        # Penalizacion por dispersion excesiva (muchos conceptos debiles)
        if activaciones:
            valores = list(activaciones.values())
            media = np.mean(valores)
            penalizacion = -0.3 if media < 0.05 else 0.0
        else:
            penalizacion = -0.5

        recompensa = np.clip(utilidad + diversidad_bonus + penalizacion, -1.0, 1.0)
        self.historial_recompensas.append(float(recompensa))
        return float(recompensa)

    def fin_episodio(self):
        """Registrar fin de episodio y decaer epsilon."""
        self.episodios += 1
        self.epsilon = max(
            self.epsilon_min,
            self.epsilon * self.epsilon_decay
        )

    def aprender_de_propagacion(self, origen: str,
                                resultados_propagacion: List[Dict[str, float]],
                                relaciones: Dict[str, List[Tuple[str, float]]]):
        """
        Aplicar Q-learning a una propagacion completa.

        Args:
            origen: concepto inicial de la propagacion.
            resultados_propagacion: lista de dicts activacion por paso.
            relaciones: dict concepto -> [(vecino, peso), ...].
        """
        if len(resultados_propagacion) < 2:
            return

        ultimo = resultados_propagacion[-1]
        conceptos_utiles = sum(1 for v in ultimo.values() if v > 0.2)
        categorias = set()  # Se llenaria con data real
        diversidad = min(1.0, len(categorias) / max(conceptos_utiles, 1))

        recompensa = self.calcular_recompensa(ultimo, conceptos_utiles, diversidad)

        # Actualizar Q para cada transicion observada
        for paso_idx in range(len(resultados_propagacion) - 1):
            paso_actual = resultados_propagacion[paso_idx]
            paso_siguiente = resultados_propagacion[paso_idx + 1]

            for concepto, act in paso_actual.items():
                if act > 0.1:
                    vecinos = [v for v, _ in relaciones.get(concepto, [])]
                    activados_sig = [
                        c for c, a in paso_siguiente.items()
                        if a > 0.1 and c != concepto
                    ]
                    for dest in activados_sig:
                        if dest in vecinos:
                            self.actualizar(concepto, dest, recompensa, vecinos)

        self.fin_episodio()

    def sugerir_ajustes_pesos(self, relaciones: Dict[str, List[Tuple[str, float]]],
                               umbral_q: float = 0.3) -> List[Tuple[str, str, float]]:
        """
        Sugerir ajustes de peso basados en Q-values.

        Returns:
            Lista de (origen, destino, delta_peso) para relaciones con Q alto.
        """
        ajustes = []
        for (origen, destino), q_val in self.q_table.items():
            if abs(q_val) > umbral_q:
                # Q positivo -> reforzar, Q negativo -> debilitar
                delta = 0.05 * np.sign(q_val) * min(abs(q_val), 1.0)
                ajustes.append((origen, destino, float(delta)))
        return ajustes

    def estadisticas(self) -> Dict:
        """Estadisticas del sistema de aprendizaje."""
        recompensas = self.historial_recompensas
        return {
            "episodios": self.episodios,
            "epsilon": round(self.epsilon, 4),
            "q_entries": len(self.q_table),
            "recompensa_media": round(np.mean(recompensas), 4) if recompensas else 0.0,
            "recompensa_ultima": round(recompensas[-1], 4) if recompensas else 0.0,
        }
