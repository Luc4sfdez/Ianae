"""
IANAE - Optimizador
Módulo para optimizar el rendimiento del sistema IANAE con grandes cantidades de conceptos y ciclos
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from nucleo import ConceptosDifusos
import time
import json
import psutil  # Para monitoreo de recursos (instalar con pip install psutil)

class IANAEOptimizado:
    """
    Wrapper para ConceptosDifusos que implementa optimizaciones para manejar
    sistemas de gran escala con limitaciones de recursos.
    """
    
    def __init__(self, sistema=None, dim_vector=10, ruta_temp="./datos/temp/"):
        """
        Inicializa el optimizador
        
        Args:
            sistema: Sistema ConceptosDifusos existente (opcional)
            dim_vector: Dimensionalidad para un nuevo sistema
            ruta_temp: Ruta para almacenamiento temporal en disco
        """
        # Crear o usar sistema existente
        self.sistema = sistema if sistema else ConceptosDifusos(dim_vector=dim_vector)
        
        # Configurar límites
        self.MAX_CONCEPTOS = 500
        self.MAX_CONEXIONES_POR_CONCEPTO = 50  # Para limitar a máx ~1000 por par (bidireccional)
        self.MAX_CICLOS_BATCH = 100  # Máximo ciclos antes de guardar/optimizar
        
        # Umbrales para poda
        self.UMBRAL_ACTIVACION_MIN = 0.1  # Conceptos con activación menor se consideran inactivos
        self.UMBRAL_CONEXION_MIN = 0.05  # Conexiones con peso menor se eliminan
        
        # Configuración para almacenamiento temporal
        self.ruta_temp = ruta_temp
        if not os.path.exists(self.ruta_temp):
            os.makedirs(self.ruta_temp)
            
        # Métricas de rendimiento
        self.metricas_rendimiento = {
            'tiempo_ciclo': [],
            'memoria_usada': [],
            'num_conceptos': [],
            'num_conexiones': []
        }
        
        # Conceptos apartados (interesantes pero poco activados)
        self.conceptos_apartados = {}
        
    def monitorear_recursos(self):
        """
        Monitorea y registra el uso de recursos
        
        Returns:
            Dict con métricas de uso de recursos
        """
        proceso = psutil.Process(os.getpid())
        memoria_usada = proceso.memory_info().rss / 1024 / 1024  # MB
        
        metrics = {
            'memoria_usada': memoria_usada,
            'num_conceptos': len(self.sistema.conceptos),
            'num_conexiones': self.sistema.grafo.number_of_edges()
        }
        
        # Actualizar historial
        self.metricas_rendimiento['memoria_usada'].append(memoria_usada)
        self.metricas_rendimiento['num_conceptos'].append(len(self.sistema.conceptos))
        self.metricas_rendimiento['num_conexiones'].append(self.sistema.grafo.number_of_edges())
        
        return metrics
    
    def podar_conexiones_debiles(self):
        """
        Elimina conexiones con peso por debajo del umbral para optimizar rendimiento
        
        Returns:
            Número de conexiones eliminadas
        """
        conexiones_eliminadas = 0
        
        # Iterar sobre todos los conceptos y sus conexiones
        for concepto in list(self.sistema.relaciones.keys()):
            # Filtrar conexiones por debajo del umbral
            conexiones_originales = self.sistema.relaciones[concepto]
            conexiones_filtradas = [(dest, peso) for dest, peso in conexiones_originales 
                                   if peso >= self.UMBRAL_CONEXION_MIN]
            
            # Calcular cuántas se eliminaron
            eliminadas = len(conexiones_originales) - len(conexiones_filtradas)
            conexiones_eliminadas += eliminadas
            
            # Actualizar lista de conexiones
            self.sistema.relaciones[concepto] = conexiones_filtradas
            
            # Actualizar grafo
            if eliminadas > 0:
                for dest, peso in conexiones_originales:
                    if peso < self.UMBRAL_CONEXION_MIN and self.sistema.grafo.has_edge(concepto, dest):
                        self.sistema.grafo.remove_edge(concepto, dest)
        
        print(f"Conexiones podadas: {conexiones_eliminadas}")
        return conexiones_eliminadas
    
    def limitar_conexiones_por_concepto(self):
        """
        Limita el número de conexiones por concepto manteniendo solo las más fuertes
        
        Returns:
            Número de conexiones eliminadas
        """
        conexiones_eliminadas = 0
        
        # Iterar sobre todos los conceptos
        for concepto in self.sistema.relaciones:
            conexiones = self.sistema.relaciones[concepto]
            
            # Si hay más conexiones que el límite, ordenar por peso y quedarnos con las más fuertes
            if len(conexiones) > self.MAX_CONEXIONES_POR_CONCEPTO:
                # Ordenar por peso (descendente)
                conexiones_ordenadas = sorted(conexiones, key=lambda x: x[1], reverse=True)
                
                # Quedarnos solo con las MAX_CONEXIONES_POR_CONCEPTO más fuertes
                conexiones_