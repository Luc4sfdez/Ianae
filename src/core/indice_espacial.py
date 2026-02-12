"""
Indice espacial para busqueda eficiente de conceptos similares.

Usa matrices numpy para calcular similitud coseno vectorizada
sobre todos los conceptos a la vez, evitando loops de Python.
"""
import numpy as np
from typing import List, Tuple, Optional


class IndiceEspacial:
    """
    Indice de vectores con busqueda por similitud coseno vectorizada.

    Mantiene una matriz numpy compacta que se redimensiona automaticamente.
    Busquedas son O(n) con operaciones vectorizadas numpy (rapido).
    """

    def __init__(self, dimension: int, capacidad_inicial: int = 128):
        self.dimension = dimension
        self._vectores = np.zeros((capacidad_inicial, dimension), dtype=np.float64)
        self._ids: List[str] = []
        self._id_to_idx: dict = {}
        self._n = 0

    @property
    def size(self) -> int:
        return self._n

    def _ensure_capacity(self):
        """Duplicar capacidad si se llena."""
        if self._n >= self._vectores.shape[0]:
            nueva_cap = self._vectores.shape[0] * 2
            nueva = np.zeros((nueva_cap, self.dimension), dtype=np.float64)
            nueva[:self._n] = self._vectores[:self._n]
            self._vectores = nueva

    def agregar(self, id_concepto: str, vector: np.ndarray):
        """Agregar un vector al indice. Si ya existe, lo actualiza."""
        if id_concepto in self._id_to_idx:
            self.actualizar(id_concepto, vector)
            return
        self._ensure_capacity()
        idx = self._n
        self._vectores[idx] = vector
        self._ids.append(id_concepto)
        self._id_to_idx[id_concepto] = idx
        self._n += 1

    def actualizar(self, id_concepto: str, nuevo_vector: np.ndarray):
        """Actualizar el vector de un concepto existente."""
        if id_concepto not in self._id_to_idx:
            return
        idx = self._id_to_idx[id_concepto]
        self._vectores[idx] = nuevo_vector

    def eliminar(self, id_concepto: str):
        """Eliminar un concepto del indice (swap con ultimo para O(1))."""
        if id_concepto not in self._id_to_idx:
            return
        idx = self._id_to_idx[id_concepto]
        last = self._n - 1

        if idx != last:
            # Mover el ultimo al hueco
            self._vectores[idx] = self._vectores[last]
            last_id = self._ids[last]
            self._ids[idx] = last_id
            self._id_to_idx[last_id] = idx

        self._ids.pop()
        del self._id_to_idx[id_concepto]
        self._vectores[last] = 0
        self._n -= 1

    def buscar_similares(self, vector: np.ndarray, top_k: int = 5,
                         excluir_id: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Buscar los top_k vectores mas similares por coseno (vectorizado).

        Args:
            vector: vector de consulta
            top_k: maximo resultados
            excluir_id: id a excluir de resultados (el propio concepto)

        Returns:
            Lista de (id, similitud) ordenada descendente.
        """
        if self._n == 0:
            return []

        V = self._vectores[:self._n]
        norms = np.linalg.norm(V, axis=1)
        query_norm = np.linalg.norm(vector)

        if query_norm < 1e-10:
            return []

        # Similitud coseno vectorizada
        sims = (V @ vector) / (norms * query_norm + 1e-10)

        # Excluir si hace falta
        if excluir_id and excluir_id in self._id_to_idx:
            sims[self._id_to_idx[excluir_id]] = -2.0

        # Top-k via argpartition (mas rapido que argsort completo para n grande)
        k = min(top_k, self._n)
        if k >= self._n:
            top_indices = np.argsort(sims)[::-1][:k]
        else:
            top_indices = np.argpartition(sims, -k)[-k:]
            top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]

        return [(self._ids[i], float(sims[i])) for i in top_indices if sims[i] > -2.0]

    def contiene(self, id_concepto: str) -> bool:
        return id_concepto in self._id_to_idx
