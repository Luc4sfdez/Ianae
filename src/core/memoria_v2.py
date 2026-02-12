"""
Módulo de memoria asociativa V2 para IANAE.
Implementa almacenamiento con decaimiento de fuerza y capacidad máxima.
"""

import time
import numpy as np
from typing import Any, Dict, List, Optional, Tuple


class MemoriaAsociativaV2:
    """
    Memoria asociativa que almacena pares clave-valor con fuerza asociativa.
    
    La fuerza decae con el tiempo y se pueden buscar claves similares por patrón.
    """
    
    def __init__(self, capacidad: int = 100, decaimiento: float = 0.95):
        """
        Inicializa la memoria asociativa.
        
        Args:
            capacidad: Número máximo de memorias que se pueden almacenar.
            decaimiento: Factor de decaimiento de la fuerza (0-1).
        """
        self.capacidad = capacidad
        self.decaimiento = decaimiento
        self._memorias: Dict[str, Tuple[Any, float, float]] = {}
        # Estructura: clave -> (valor, fuerza, timestamp)
        
    def almacenar(self, clave: str, valor: Any, fuerza: float = 1.0) -> None:
        """
        Almacena un par clave-valor con una fuerza asociativa.
        
        Args:
            clave: Identificador de la memoria.
            valor: Valor a almacenar.
            fuerza: Fuerza asociativa inicial (0-1).
        """
        # Aplicar decaimiento si la clave ya existe
        if clave in self._memorias:
            valor_antiguo, fuerza_antigua, timestamp_antiguo = self._memorias[clave]
            tiempo_transcurrido = time.time() - timestamp_antiguo
            fuerza_decaimiento = fuerza_antigua * (self.decaimiento ** tiempo_transcurrido)
            # Combinar fuerzas (máximo 1.0)
            fuerza = min(1.0, fuerza + fuerza_decaimiento)
        
        # Verificar capacidad
        if len(self._memorias) >= self.capacidad and clave not in self._memorias:
            # Eliminar la memoria más débil
            self._eliminar_mas_debil()
        
        # Almacenar nueva memoria
        self._memorias[clave] = (valor, fuerza, time.time())
    
    def buscar(self, clave: str) -> Optional[Any]:
        """
        Busca una memoria por clave exacta.
        
        Args:
            clave: Clave exacta a buscar.
            
        Returns:
            El valor asociado si existe y la fuerza > 0.1, None en caso contrario.
        """
        if clave not in self._memorias:
            return None
        
        valor, fuerza, timestamp = self._memorias[clave]
        
        # Aplicar decaimiento
        tiempo_transcurrido = time.time() - timestamp
        fuerza_actual = fuerza * (self.decaimiento ** tiempo_transcurrido)
        
        # Actualizar fuerza en almacenamiento
        self._memorias[clave] = (valor, fuerza_actual, timestamp)
        
        # Retornar valor solo si la fuerza es significativa
        if fuerza_actual > 0.1:
            return valor
        return None
    
    def buscar_similares(self, patron: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Busca memorias cuyas claves contengan el patrón.
        
        Args:
            patron: Patrón de búsqueda (subcadena).
            top_k: Número máximo de resultados a retornar.
            
        Returns:
            Lista de tuplas (clave, fuerza) ordenada por fuerza descendente.
        """
        resultados = []
        tiempo_actual = time.time()
        
        for clave, (valor, fuerza, timestamp) in self._memorias.items():
            # Aplicar decaimiento
            tiempo_transcurrido = tiempo_actual - timestamp
            fuerza_actual = fuerza * (self.decaimiento ** tiempo_transcurrido)
            
            # Actualizar fuerza en almacenamiento
            self._memorias[clave] = (valor, fuerza_actual, timestamp)
            
            # Verificar si el patrón está en la clave (case-insensitive)
            if patron.lower() in clave.lower() and fuerza_actual > 0.1:
                resultados.append((clave, fuerza_actual))
        
        # Ordenar por fuerza descendente y limitar a top_k
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[:top_k]
    
    def consolidar(self) -> int:
        """
        Elimina memorias con fuerza < 0.1.
        
        Returns:
            Número de memorias eliminadas.
        """
        claves_a_eliminar = []
        tiempo_actual = time.time()
        
        for clave, (valor, fuerza, timestamp) in self._memorias.items():
            # Aplicar decaimiento
            tiempo_transcurrido = tiempo_actual - timestamp
            fuerza_actual = fuerza * (self.decaimiento ** tiempo_transcurrido)
            
            if fuerza_actual <= 0.1:
                claves_a_eliminar.append(clave)
        
        # Eliminar memorias débiles
        for clave in claves_a_eliminar:
            del self._memorias[clave]
        
        return len(claves_a_eliminar)
    
    def estadisticas(self) -> Dict[str, Any]:
        """
        Retorna estadísticas de la memoria.
        
        Returns:
            Diccionario con {total, activas, promedio_fuerza}
        """
        total = len(self._memorias)
        tiempo_actual = time.time()
        fuerzas = []
        
        for valor, fuerza, timestamp in self._memorias.values():
            # Aplicar decaimiento
            tiempo_transcurrido = tiempo_actual - timestamp
            fuerza_actual = fuerza * (self.decaimiento ** tiempo_transcurrido)
            fuerzas.append(fuerza_actual)
        
        activas = sum(1 for f in fuerzas if f > 0.1)
        promedio_fuerza = sum(fuerzas) / total if total > 0 else 0.0
        
        return {
            "total": total,
            "activas": activas,
            "promedio_fuerza": promedio_fuerza
        }
    
    def exportar(self) -> Dict[str, Tuple[Any, float, float]]:
        """
        Exporta el estado actual de la memoria.
        
        Returns:
            Diccionario con estructura {clave: (valor, fuerza, timestamp)}
        """
        return dict(self._memorias)
    
    def importar(self, datos: Dict[str, Tuple[Any, float, float]]) -> None:
        """
        Importa datos a la memoria.
        
        Args:
            datos: Diccionario con estructura {clave: (valor, fuerza, timestamp)}
        """
        self._memorias.clear()
        self._memorias.update(datos)
    
    def _eliminar_mas_debil(self) -> None:
        """Elimina la memoria con la fuerza más baja."""
        if not self._memorias:
            return
        
        tiempo_actual = time.time()
        clave_mas_debil = None
        fuerza_minima = float('inf')
        
        for clave, (valor, fuerza, timestamp) in self._memorias.items():
            # Aplicar decaimiento para comparación
            tiempo_transcurrido = tiempo_actual - timestamp
            fuerza_actual = fuerza * (self.decaimiento ** tiempo_transcurrido)
            
            if fuerza_actual < fuerza_minima:
                fuerza_minima = fuerza_actual
                clave_mas_debil = clave
        
        if clave_mas_debil:
            del self._memorias[clave_mas_debil]