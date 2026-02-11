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
        self.MAX_