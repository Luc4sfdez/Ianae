"""
Memoria asociativa simple para IANAE.
Almacena conceptos con contexto y peso, permitiendo búsqueda por similitud textual.
"""

from typing import Dict, List, Tuple, Any


class MemoriaAsociativa:
    """
    Memoria asociativa que almacena conceptos con contexto y peso.

    Atributos:
        _almacen (Dict[str, Tuple[str, float]]): Diccionario interno que mapea
            concepto -> (contexto, peso)
    """

    def __init__(self) -> None:
        """
        Inicializa una memoria asociativa vacía.
        """
        self._almacen: Dict[str, Tuple[str, float]] = {}

    def almacenar(self, concepto: str, contexto: str, peso: float) -> None:
        """
        Almacena o actualiza un concepto en la memoria.

        Args:
            concepto (str): Nombre o identificador del concepto.
            contexto (str): Contexto o descripción asociada.
            peso (float): Peso asociativo (mayor = más relevante).

        Notas:
            Si el concepto ya existe, se sobrescribe con los nuevos valores.
        """
        self._almacen[concepto] = (contexto, peso)

    def buscar(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Busca conceptos que contengan la query (case-insensitive substring).

        Args:
            query (str): Texto a buscar dentro de los conceptos.
            top_k (int, opcional): Número máximo de resultados a retornar.
                Por defecto 5.

        Returns:
            List[Tuple[str, float]]: Lista de tuplas (concepto, peso) ordenadas
                por peso descendente. Solo incluye conceptos cuyo nombre contiene
                la query (ignorando mayúsculas/minúsculas).
        """
        query_lower = query.lower()
        resultados = []

        for concepto, (contexto, peso) in self._almacen.items():
            if query_lower in concepto.lower():
                resultados.append((concepto, peso))

        # Ordenar por peso descendente
        resultados.sort(key=lambda x: x[1], reverse=True)

        # Limitar a top_k
        return resultados[:top_k]

    def exportar(self) -> Dict[str, Tuple[str, float]]:
        """
        Exporta una copia del estado interno de la memoria.

        Returns:
            Dict[str, Tuple[str, float]]: Copia del diccionario interno
                concepto -> (contexto, peso).
        """
        return self._almacen.copy()