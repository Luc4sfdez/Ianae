# nucleo_lucas.py - IANAE adaptado para proyectos de Lucas
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import random
import json
import os
import time
from datetime import datetime
from src.core.indice_espacial import IndiceEspacial
from src.core.persistencia import PersistenciaVectores
from src.core.versionado import VersionadoEstado

class ConceptosLucas:
    """
    Sistema IANAE adaptado específicamente para los proyectos y conceptos de Lucas
    """
    
    def __init__(self, dim_vector=15, incertidumbre_base=0.2):
        """
        Inicializa el sistema con configuración optimizada para nuestros proyectos
        """
        self.conceptos = {}
        self.relaciones = defaultdict(list)
        self.grafo = nx.Graph()
        self.dim_vector = dim_vector
        self.incertidumbre_base = incertidumbre_base
        self.historial_activaciones = []
        self.indice = IndiceEspacial(dim_vector)
        self.persistencia = PersistenciaVectores()
        self.versionado = VersionadoEstado()

        # Métricas específicas para nuestro caso
        self.metricas = {
            'edad': 0,
            'conceptos_creados': 0,
            'conexiones_formadas': 0,
            'ciclos_pensamiento': 0,
            'auto_modificaciones': 0,
            'proyectos_referenciados': 0,
            'tecnologias_conectadas': 0,
            'emergencias_detectadas': 0
        }
        
        # Categorías de conceptos para análisis especializado
        self.categorias = {
            'tecnologias': [],
            'proyectos': [],
            'lucas_personal': [],
            'conceptos_ianae': [],
            'herramientas': [],
            'emergentes': []
        }

        # === Estructuras numpy para propagación matricial ===
        self._cap = 64                    # Capacidad pre-asignada
        self._n = 0                       # Número actual de conceptos
        self._idx = {}                    # nombre -> índice numpy
        self._names = []                  # índice -> nombre
        self._adj = np.zeros((self._cap, self._cap), dtype=np.float64)   # Matriz de adyacencia
        self._vec_actual = np.zeros((self._cap, dim_vector), dtype=np.float64)  # Vectores actuales
        self._vec_base = np.zeros((self._cap, dim_vector), dtype=np.float64)    # Vectores base
        
    # === Métodos internos numpy ===

    def _ensure_capacity(self):
        """Expande arrays numpy si se alcanza la capacidad"""
        if self._n >= self._cap:
            new_cap = self._cap * 2
            new_adj = np.zeros((new_cap, new_cap), dtype=np.float64)
            new_adj[:self._cap, :self._cap] = self._adj
            self._adj = new_adj
            new_va = np.zeros((new_cap, self.dim_vector), dtype=np.float64)
            new_va[:self._cap] = self._vec_actual
            self._vec_actual = new_va
            new_vb = np.zeros((new_cap, self.dim_vector), dtype=np.float64)
            new_vb[:self._cap] = self._vec_base
            self._vec_base = new_vb
            self._cap = new_cap

    def _act_to_dict(self, arr):
        """Convierte vector numpy de activación a dict {nombre: valor}"""
        return {self._names[i]: float(arr[i]) for i in range(self._n)}

    def _rebuild_numpy(self):
        """Reconstruye estructuras numpy desde dicts (usado por cargar)"""
        names = list(self.conceptos.keys())
        self._n = len(names)
        self._cap = max(64, self._n * 2)
        self._idx = {name: i for i, name in enumerate(names)}
        self._names = names
        self._adj = np.zeros((self._cap, self._cap), dtype=np.float64)
        self._vec_actual = np.zeros((self._cap, self.dim_vector), dtype=np.float64)
        self._vec_base = np.zeros((self._cap, self.dim_vector), dtype=np.float64)
        for name, i in self._idx.items():
            self._vec_actual[i] = self.conceptos[name]['actual']
            self._vec_base[i] = self.conceptos[name]['base']
        for origen in self.relaciones:
            if origen in self._idx:
                i = self._idx[origen]
                for destino, peso in self.relaciones[origen]:
                    if destino in self._idx:
                        j = self._idx[destino]
                        self._adj[i, j] = peso

    def buscar_similares(self, concepto, top_k=5):
        """Índice espacial: búsqueda vectorizada de conceptos similares por coseno"""
        if concepto not in self._idx:
            return []
        idx = self._idx[concepto]
        n = self._n
        V = self._vec_actual[:n]
        norms = np.linalg.norm(V, axis=1)
        norms = np.maximum(norms, 1e-10)
        V_norm = V / norms[:, np.newaxis]
        target = V_norm[idx]
        similarities = V_norm @ target
        similarities[idx] = -1  # Excluir a sí mismo
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(self._names[i], float(similarities[i])) for i in top_indices]

    def crear_conceptos_lucas(self):
        """
        Crea la base conceptual específica de Lucas con todos sus proyectos y tecnologías
        """
        print("🔥 Creando universo conceptual de Lucas...")
        
        # === TECNOLOGÍAS CORE ===
        tecnologias = {
            'Python': {'vector_base': [0.9, 0.8, 0.7, 0.6, 0.9, 0.8, 0.5, 0.4, 0.7, 0.8, 0.6, 0.9, 0.7, 0.5, 0.8], 'categoria': 'tecnologias'},
            'OpenCV': {'vector_base': [0.8, 0.9, 0.6, 0.7, 0.8, 0.5, 0.9, 0.6, 0.7, 0.8, 0.4, 0.7, 0.9, 0.6, 0.5], 'categoria': 'tecnologias'},
            'VBA': {'vector_base': [0.6, 0.7, 0.8, 0.9, 0.5, 0.6, 0.7, 0.8, 0.4, 0.5, 0.9, 0.6, 0.7, 0.8, 0.3], 'categoria': 'tecnologias'},
            'Excel': {'vector_base': [0.7, 0.6, 0.9, 0.8, 0.7, 0.5, 0.6, 0.9, 0.8, 0.4, 0.7, 0.5, 0.8, 0.9, 0.6], 'categoria': 'tecnologias'},
            'Pandas': {'vector_base': [0.9, 0.7, 0.6, 0.8, 0.9, 0.5, 0.4, 0.7, 0.8, 0.9, 0.6, 0.5, 0.7, 0.8, 0.9], 'categoria': 'tecnologias'},
            'Docker': {'vector_base': [0.5, 0.8, 0.7, 0.6, 0.4, 0.9, 0.8, 0.5, 0.6, 0.7, 0.8, 0.9, 0.4, 0.5, 0.7], 'categoria': 'tecnologias'},
            'ThreeJS': {'vector_base': [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.2, 0.3], 'categoria': 'tecnologias'},
            'LM_Studio': {'vector_base': [0.8, 0.9, 0.7, 0.5, 0.6, 0.8, 0.9, 0.4, 0.3, 0.7, 0.8, 0.5, 0.6, 0.9, 0.7], 'categoria': 'tecnologias'}
        }
        
        # === PROYECTOS ESPECÍFICOS ===
        proyectos = {
            'Tacografos': {'vector_base': [0.9, 0.8, 0.7, 0.9, 0.6, 0.5, 0.8, 0.9, 0.7, 0.4, 0.6, 0.8, 0.9, 0.5, 0.7], 'categoria': 'proyectos'},
            'VBA2Python': {'vector_base': [0.8, 0.9, 0.6, 0.7, 0.9, 0.8, 0.5, 0.6, 0.8, 0.9, 0.4, 0.5, 0.7, 0.8, 0.9], 'categoria': 'proyectos'},
            'Hollow_Earth': {'vector_base': [0.3, 0.4, 0.9, 0.8, 0.7, 0.6, 0.5, 0.9, 0.8, 0.3, 0.4, 0.7, 0.6, 0.9, 0.8], 'categoria': 'proyectos'},
            'RAG_System': {'vector_base': [0.9, 0.7, 0.8, 0.6, 0.5, 0.9, 0.8, 0.7, 0.6, 0.9, 0.5, 0.4, 0.8, 0.7, 0.9], 'categoria': 'proyectos'},
            'Memory_System': {'vector_base': [0.8, 0.6, 0.9, 0.7, 0.8, 0.5, 0.9, 0.6, 0.7, 0.8, 0.9, 0.4, 0.5, 0.6, 0.8], 'categoria': 'proyectos'}
        }
        
        # === LUCAS PERSONAL ===
        lucas_personal = {
            'Lucas': {'vector_base': [1.0, 0.9, 0.8, 0.7, 0.9, 0.8, 0.6, 0.5, 0.8, 0.9, 0.7, 0.6, 0.8, 0.9, 0.5], 'categoria': 'lucas_personal'},
            'Novelda': {'vector_base': [0.7, 0.8, 0.6, 0.9, 0.5, 0.7, 0.8, 0.9, 0.4, 0.6, 0.5, 0.8, 0.7, 0.6, 0.9], 'categoria': 'lucas_personal'},
            'Alicante': {'vector_base': [0.6, 0.7, 0.5, 0.8, 0.9, 0.6, 0.4, 0.7, 0.8, 0.5, 0.9, 0.6, 0.4, 0.8, 0.7], 'categoria': 'lucas_personal'},
            'i9_10900KF': {'vector_base': [0.9, 0.8, 0.4, 0.5, 0.7, 0.9, 0.8, 0.3, 0.6, 0.4, 0.8, 0.9, 0.5, 0.7, 0.6], 'categoria': 'lucas_personal'},
            'RTX3060': {'vector_base': [0.8, 0.5, 0.7, 0.6, 0.9, 0.4, 0.8, 0.7, 0.5, 0.9, 0.6, 0.3, 0.8, 0.4, 0.9], 'categoria': 'lucas_personal'},
            'TOC_TDAH': {'vector_base': [0.5, 0.9, 0.8, 0.4, 0.6, 0.7, 0.9, 0.8, 0.3, 0.5, 0.7, 0.9, 0.6, 0.4, 0.8], 'categoria': 'lucas_personal'},
            'Superpoder_Patrones': {'vector_base': [0.9, 0.6, 0.5, 0.8, 0.7, 0.9, 0.4, 0.5, 0.8, 0.6, 0.9, 0.7, 0.3, 0.5, 0.8], 'categoria': 'lucas_personal'}
        }
        
        # === CONCEPTOS IANAE ===
        ianae_conceptos = {
            'IANAE': {'vector_base': [0.8, 0.9, 0.7, 0.8, 0.6, 0.9, 0.5, 0.7, 0.8, 0.9, 0.4, 0.6, 0.7, 0.8, 0.9], 'categoria': 'conceptos_ianae'},
            'Pensamiento_Emergente': {'vector_base': [0.7, 0.8, 0.9, 0.5, 0.6, 0.8, 0.9, 0.4, 0.7, 0.5, 0.8, 0.9, 0.6, 0.3, 0.7], 'categoria': 'conceptos_ianae'},
            'Conceptos_Difusos': {'vector_base': [0.6, 0.7, 0.8, 0.9, 0.4, 0.5, 0.7, 0.8, 0.9, 0.3, 0.6, 0.4, 0.8, 0.7, 0.5], 'categoria': 'conceptos_ianae'},
            'Auto_Modificacion': {'vector_base': [0.5, 0.6, 0.7, 0.8, 0.9, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.2, 0.5, 0.6, 0.8], 'categoria': 'conceptos_ianae'},
            'Emergencia': {'vector_base': [0.9, 0.5, 0.6, 0.7, 0.8, 0.9, 0.3, 0.4, 0.5, 0.7, 0.8, 0.9, 0.2, 0.4, 0.6], 'categoria': 'conceptos_ianae'}
        }
        
        # === HERRAMIENTAS ===
        herramientas = {
            'Automatizacion': {'vector_base': [0.8, 0.7, 0.9, 0.6, 0.5, 0.8, 0.7, 0.9, 0.4, 0.6, 0.5, 0.8, 0.9, 0.7, 0.3], 'categoria': 'herramientas'},
            'Deteccion': {'vector_base': [0.7, 0.9, 0.6, 0.8, 0.5, 0.7, 0.9, 0.4, 0.6, 0.8, 0.3, 0.7, 0.5, 0.9, 0.6], 'categoria': 'herramientas'},
            'Optimizacion': {'vector_base': [0.9, 0.6, 0.7, 0.5, 0.8, 0.9, 0.4, 0.6, 0.7, 0.3, 0.8, 0.5, 0.9, 0.6, 0.4], 'categoria': 'herramientas'},
            'Creatividad': {'vector_base': [0.4, 0.8, 0.5, 0.9, 0.6, 0.3, 0.7, 0.8, 0.9, 0.5, 0.4, 0.6, 0.7, 0.8, 0.9], 'categoria': 'herramientas'},
            'Memoria': {'vector_base': [0.6, 0.5, 0.8, 0.7, 0.9, 0.4, 0.5, 0.6, 0.8, 0.9, 0.7, 0.3, 0.4, 0.5, 0.8], 'categoria': 'herramientas'}
        }
        
        # Crear todos los conceptos
        todos_conceptos = {**tecnologias, **proyectos, **lucas_personal, **ianae_conceptos, **herramientas}
        
        conceptos_creados = []
        for nombre, datos in todos_conceptos.items():
            vector = np.array(datos['vector_base'])
            self.añadir_concepto(nombre, atributos=vector, categoria=datos['categoria'])
            self.categorias[datos['categoria']].append(nombre)
            conceptos_creados.append(nombre)
            
        print(f"✅ Creados {len(conceptos_creados)} conceptos base")
        return conceptos_creados
    
    def crear_relaciones_lucas(self):
        """
        Establece relaciones específicas basadas en nuestros proyectos reales
        """
        print("🔗 Estableciendo relaciones de proyectos reales...")
        
        # === RELACIONES PROYECTO TACÓGRAFOS ===
        relaciones_tacografos = [
            ('Tacografos', 'Python', 0.9),
            ('Tacografos', 'OpenCV', 0.95),
            ('Tacografos', 'Deteccion', 0.9),
            ('OpenCV', 'Python', 0.85),
            ('OpenCV', 'Deteccion', 0.9),
        ]
        
        # === RELACIONES VBA2PYTHON ===
        relaciones_vba2python = [
            ('VBA2Python', 'VBA', 0.95),
            ('VBA2Python', 'Python', 0.95),
            ('VBA2Python', 'Excel', 0.9),
            ('VBA2Python', 'Pandas', 0.85),
            ('VBA2Python', 'Automatizacion', 0.9),
            ('VBA', 'Excel', 0.95),
            ('Pandas', 'Python', 0.9),
        ]
        
        # === RELACIONES HOLLOW EARTH ===
        relaciones_hollow_earth = [
            ('Hollow_Earth', 'ThreeJS', 0.9),
            ('Hollow_Earth', 'Creatividad', 0.85),
            ('ThreeJS', 'Creatividad', 0.7),
        ]
        
        # === RELACIONES RAG + MEMORIA ===
        relaciones_rag = [
            ('RAG_System', 'Memory_System', 0.95),
            ('RAG_System', 'Python', 0.85),
            ('Memory_System', 'Memoria', 0.9),
            ('RAG_System', 'LM_Studio', 0.8),
        ]
        
        # === RELACIONES LUCAS PERSONAL ===
        relaciones_lucas = [
            ('Lucas', 'Novelda', 0.95),
            ('Lucas', 'Alicante', 0.9),
            ('Lucas', 'i9_10900KF', 0.9),
            ('Lucas', 'RTX3060', 0.9),
            ('Lucas', 'TOC_TDAH', 0.95),
            ('Lucas', 'Superpoder_Patrones', 0.9),
            ('TOC_TDAH', 'Superpoder_Patrones', 0.85),
            ('i9_10900KF', 'RTX3060', 0.8),
        ]
        
        # === RELACIONES IANAE ===
        relaciones_ianae = [
            ('IANAE', 'Pensamiento_Emergente', 0.95),
            ('IANAE', 'Conceptos_Difusos', 0.9),
            ('IANAE', 'Auto_Modificacion', 0.85),
            ('IANAE', 'Emergencia', 0.9),
            ('Pensamiento_Emergente', 'Conceptos_Difusos', 0.8),
            ('Emergencia', 'Auto_Modificacion', 0.75),
        ]
        
        # === RELACIONES CROSS-PROJECT ===
        relaciones_cross = [
            ('Lucas', 'Python', 0.95),
            ('Lucas', 'IANAE', 0.9),
            ('Python', 'Automatizacion', 0.85),
            ('Optimizacion', 'TOC_TDAH', 0.8),
            ('Creatividad', 'Emergencia', 0.8),
            ('Memoria', 'Superpoder_Patrones', 0.75),
        ]
        
        # Crear todas las relaciones
        todas_relaciones = (relaciones_tacografos + relaciones_vba2python + 
                           relaciones_hollow_earth + relaciones_rag + 
                           relaciones_lucas + relaciones_ianae + relaciones_cross)
        
        relaciones_creadas = 0
        for c1, c2, fuerza in todas_relaciones:
            if c1 in self.conceptos and c2 in self.conceptos:
                self.relacionar(c1, c2, fuerza=fuerza)
                relaciones_creadas += 1
                
        print(f"✅ Creadas {relaciones_creadas} relaciones específicas")
        return relaciones_creadas
    
    def añadir_concepto(self, nombre, atributos=None, incertidumbre=None, categoria='emergentes'):
        """
        Versión extendida que incluye categorización automática
        """
        if incertidumbre is None:
            incertidumbre = self.incertidumbre_base
            
        if atributos is None:
            atributos = np.random.normal(0, 1, self.dim_vector)
            
        # Normalizar
        atributos = atributos / np.linalg.norm(atributos)
        
        # Añadir ruido
        ruido = np.random.normal(0, incertidumbre, atributos.shape)
        self.conceptos[nombre] = {
            'base': atributos.copy(),
            'actual': atributos + ruido,
            'historial': [atributos.copy()],
            'creado': self.metricas['edad'],
            'activaciones': 0,
            'ultima_activacion': 0,
            'fuerza': 1.0,
            'categoria': categoria,  # Nueva propiedad
            'conexiones_proyecto': 0  # Nueva métrica
        }
        
        self.grafo.add_node(nombre)
        self.metricas['conceptos_creados'] += 1
        self.indice.agregar(nombre, self.conceptos[nombre]['actual'])

        # Sincronizar estructuras numpy
        self._ensure_capacity()
        idx = self._n
        self._idx[nombre] = idx
        self._names.append(nombre)
        self._vec_base[idx] = self.conceptos[nombre]['base']
        self._vec_actual[idx] = self.conceptos[nombre]['actual']
        self._n += 1

        # Añadir a categoría si no es emergente
        if categoria != 'emergentes' and categoria in self.categorias:
            if nombre not in self.categorias[categoria]:
                self.categorias[categoria].append(nombre)
        else:
            self.categorias['emergentes'].append(nombre)

        return nombre
    
    def relacionar(self, concepto1, concepto2, fuerza=None, bidireccional=True):
        """
        Versión extendida con métricas de proyecto y sincronización de matriz de adyacencia
        """
        if concepto1 not in self.conceptos or concepto2 not in self.conceptos:
            return 0

        if fuerza is None:
            # Similitud vectorizada desde arrays numpy
            i, j = self._idx[concepto1], self._idx[concepto2]
            v1, v2 = self._vec_actual[i], self._vec_actual[j]
            n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
            similitud_base = np.dot(v1, v2) / (n1 * n2 + 1e-10)
            fuerza = float(np.clip(similitud_base + np.random.normal(0, 0.1), 0.1, 1.0))

        self.relaciones[concepto1].append((concepto2, fuerza))
        if bidireccional:
            self.relaciones[concepto2].append((concepto1, fuerza))

        self.grafo.add_edge(concepto1, concepto2, weight=fuerza)
        self.metricas['conexiones_formadas'] += 1

        # Sincronizar matriz de adyacencia numpy
        i, j = self._idx[concepto1], self._idx[concepto2]
        self._adj[i, j] = fuerza
        if bidireccional:
            self._adj[j, i] = fuerza

        # Actualizar métricas de conexión de proyecto
        self.conceptos[concepto1]['conexiones_proyecto'] += 1
        self.conceptos[concepto2]['conexiones_proyecto'] += 1

        # Detectar si es una conexión cross-proyecto
        cat1 = self.conceptos[concepto1]['categoria']
        cat2 = self.conceptos[concepto2]['categoria']
        if cat1 != cat2 and cat1 != 'emergentes' and cat2 != 'emergentes':
            self.metricas['proyectos_referenciados'] += 1

        return fuerza
    
    def explorar_proyecto(self, proyecto, profundidad=3):
        """
        Explora específicamente un proyecto y sus tecnologías relacionadas
        """
        if proyecto not in self.conceptos:
            return f"Proyecto '{proyecto}' no encontrado"
            
        print(f"🔍 Explorando proyecto: {proyecto}")
        
        # Activar el proyecto
        resultado = self.activar(proyecto, pasos=profundidad, temperatura=0.15)
        
        if not resultado:
            return "No se pudo activar el proyecto"
            
        # Analizar activaciones finales
        activaciones_finales = resultado[-1]
        conceptos_activos = [(c, a) for c, a in activaciones_finales.items() if a > 0.1]
        conceptos_activos.sort(key=lambda x: x[1], reverse=True)
        
        # Categorizar resultados
        resultados_por_categoria = defaultdict(list)
        for concepto, activacion in conceptos_activos:
            categoria = self.conceptos[concepto]['categoria']
            resultados_por_categoria[categoria].append((concepto, activacion))
        
        # Generar reporte
        reporte = [f"=== EXPLORACIÓN DE {proyecto.upper()} ===\n"]
        
        for categoria, conceptos in resultados_por_categoria.items():
            if conceptos:
                reporte.append(f"{categoria.upper().replace('_', ' ')}:")
                for concepto, activacion in conceptos[:5]:  # Top 5 por categoría
                    reporte.append(f"  • {concepto}: {activacion:.3f}")
                reporte.append("")
        
        return "\n".join(reporte)
    
    def detectar_emergencias(self, umbral_emergencia=0.3):
        """
        Detecta patrones emergentes basado en activaciones recientes
        """
        if len(self.historial_activaciones) < 3:
            return "Necesario más historial para detectar emergencias"
            
        print("🌟 Detectando patrones emergentes...")
        
        # Analizar últimas activaciones
        ultimas_activaciones = self.historial_activaciones[-5:]
        
        # Contar frecuencia de co-activación
        co_activaciones = defaultdict(int)
        
        for activacion in ultimas_activaciones:
            conceptos_activos = [c for c, a in activacion['resultado'].items() if a > umbral_emergencia]
            
            # Contar pares co-activados
            for i, c1 in enumerate(conceptos_activos):
                for c2 in conceptos_activos[i+1:]:
                    par = tuple(sorted([c1, c2]))
                    co_activaciones[par] += 1
        
        # Filtrar emergencias (co-activaciones frecuentes entre categorías diferentes)
        emergencias = []
        for (c1, c2), frecuencia in co_activaciones.items():
            if frecuencia >= 3:  # Aparece en al menos 3 activaciones
                cat1 = self.conceptos[c1]['categoria']
                cat2 = self.conceptos[c2]['categoria']
                
                if cat1 != cat2:  # Cross-categoria = emergencia potencial
                    fuerza_conexion = 0
                    if self.grafo.has_edge(c1, c2):
                        fuerza_conexion = self.grafo[c1][c2]['weight']
                    
                    emergencias.append({
                        'conceptos': (c1, c2),
                        'categorias': (cat1, cat2),
                        'frecuencia': frecuencia,
                        'fuerza_existente': fuerza_conexion
                    })
        
        # Ordenar por frecuencia
        emergencias.sort(key=lambda x: x['frecuencia'], reverse=True)
        
        if emergencias:
            self.metricas['emergencias_detectadas'] += len(emergencias)
            
            reporte = ["🌟 EMERGENCIAS DETECTADAS:\n"]
            for emer in emergencias[:5]:  # Top 5
                c1, c2 = emer['conceptos']
                cat1, cat2 = emer['categorias']
                freq = emer['frecuencia']
                fuerza = emer['fuerza_existente']
                
                reporte.append(f"• {c1} ↔ {c2}")
                reporte.append(f"  Categorías: {cat1} → {cat2}")
                reporte.append(f"  Frecuencia: {freq}/5 activaciones")
                reporte.append(f"  Conexión actual: {fuerza:.3f}")
                reporte.append("")
                
            return "\n".join(reporte)
        else:
            return "No se detectaron patrones emergentes significativos"
    
    def visualizar_lucas(self, activaciones=None, mostrar_categorias=True):
        """
        Visualización específica para los conceptos de Lucas con colores por categoría
        """
        plt.figure(figsize=(16, 12))
        
        # Colores por categoría
        colores_categoria = {
            'tecnologias': '#FF6B6B',      # Rojo
            'proyectos': '#4ECDC4',        # Turquesa  
            'lucas_personal': '#45B7D1',   # Azul
            'conceptos_ianae': '#96CEB4',   # Verde
            'herramientas': '#FFEAA7',      # Amarillo
            'emergentes': '#DDA0DD'         # Púrpura
        }
        
        pos = nx.spring_layout(self.grafo, k=0.5, iterations=100)
        
        # Dibujar por categorías
        for categoria, color in colores_categoria.items():
            nodos_categoria = [n for n in self.grafo.nodes if n in self.categorias.get(categoria, [])]
            
            if nodos_categoria:
                # Tamaño basado en activaciones o conexiones
                tamaños = []
                for n in nodos_categoria:
                    if activaciones and n in activaciones:
                        tamaño = 300 + 1000 * activaciones[n]
                    else:
                        tamaño = 200 + 50 * self.conceptos[n]['activaciones']
                    tamaños.append(tamaño)
                
                nx.draw_networkx_nodes(
                    self.grafo, pos,
                    nodelist=nodos_categoria,
                    node_color=color,
                    node_size=tamaños,
                    alpha=0.8,
                    label=categoria.replace('_', ' ').title()
                )
        
        # Dibujar aristas
        edges = self.grafo.edges(data=True)
        for u, v, d in edges:
            peso = d['weight']
            alpha = min(1.0, peso)
            
            nx.draw_networkx_edges(
                self.grafo, pos,
                edgelist=[(u, v)],
                width=peso * 3,
                alpha=alpha,
                edge_color='gray'
            )
        
        # Etiquetas para conceptos importantes
        etiquetas_importantes = {}
        for categoria in ['lucas_personal', 'proyectos']:
            for concepto in self.categorias.get(categoria, []):
                etiquetas_importantes[concepto] = concepto
                
        # Añadir conceptos muy activos
        if activaciones:
            for c, a in activaciones.items():
                if a > 0.3:
                    etiquetas_importantes[c] = c
        
        nx.draw_networkx_labels(
            self.grafo, pos,
            labels=etiquetas_importantes,
            font_size=9,
            font_weight='bold'
        )
        
        plt.title("🔥 Universo Conceptual de Lucas - IANAE", fontsize=16, fontweight='bold')
        
        if mostrar_categorias:
            plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
            
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    def informe_lucas(self):
        """
        Genera un informe específico del estado del universo conceptual de Lucas
        """
        print("📊 INFORME DEL UNIVERSO CONCEPTUAL DE LUCAS")
        print("=" * 50)
        
        # Métricas generales
        print(f"Conceptos totales: {len(self.conceptos)}")
        print(f"Relaciones totales: {self.grafo.number_of_edges()}")
        print(f"Edad del sistema: {self.metricas['edad']} ciclos")
        print(f"Proyectos referenciados: {self.metricas['proyectos_referenciados']}")
        print(f"Emergencias detectadas: {self.metricas['emergencias_detectadas']}")
        print()
        
        # Por categorías
        print("📁 CONCEPTOS POR CATEGORÍA:")
        for categoria, conceptos in self.categorias.items():
            if conceptos:
                print(f"  {categoria.replace('_', ' ').title()}: {len(conceptos)}")
                # Mostrar los más activos de cada categoría
                conceptos_activos = [(c, self.conceptos[c]['activaciones']) for c in conceptos]
                conceptos_activos.sort(key=lambda x: x[1], reverse=True)
                if conceptos_activos:
                    print(f"    Más activo: {conceptos_activos[0][0]} ({conceptos_activos[0][1]} activaciones)")
        print()
        
        # Conceptos más conectados
        print("🔗 CONCEPTOS MÁS CONECTADOS:")
        grados = dict(self.grafo.degree())
        conceptos_por_grado = sorted(grados.items(), key=lambda x: x[1], reverse=True)
        for concepto, grado in conceptos_por_grado[:5]:
            categoria = self.conceptos[concepto]['categoria']
            print(f"  {concepto} ({categoria}): {grado} conexiones")
        
        return True
    
    def activar(self, concepto_inicial, pasos=3, temperatura=0.1):
        """Propagación matricial numpy — reemplaza bucles anidados Python"""
        if concepto_inicial not in self._idx:
            return []

        # Incrementar métricas específicas
        categoria = self.conceptos[concepto_inicial]['categoria']
        if categoria in ['tecnologias', 'proyectos']:
            self.metricas['tecnologias_conectadas'] += 1

        self.conceptos[concepto_inicial]['activaciones'] += 1
        self.conceptos[concepto_inicial]['ultima_activacion'] = self.metricas['ciclos_pensamiento']

        n = self._n
        adj = self._adj[:n, :n]

        # Vector de activación numpy
        act = np.zeros(n, dtype=np.float64)
        act[self._idx[concepto_inicial]] = 1.0

        resultados = [self._act_to_dict(act)]

        ciclo = self.metricas['ciclos_pensamiento']

        for paso in range(pasos):
            # Máscara de conceptos con activación > 0.1
            mask = act > 0.1

            if np.any(mask):
                active_idx = np.where(mask)[0]
                # Submatriz: filas de fuentes activas, todas las columnas destino
                sub_adj = adj[active_idx]             # (n_active, n)
                # Ruido vectorizado
                noise = np.random.uniform(
                    1 - temperatura, 1 + temperatura,
                    size=sub_adj.shape
                )
                # Propagación matricial: prop[i,j] = act[src_i] * adj[src_i,j] * noise[i,j]
                prop = act[active_idx, np.newaxis] * sub_adj * noise
                # Nueva activación: max sobre todas las fuentes
                max_prop = np.max(prop, axis=0)
                new_act = np.maximum(act, max_prop)
            else:
                new_act = act.copy()

            # Normalización vectorizada
            total = new_act.sum() + 1e-10
            new_act /= total
            new_act += np.random.normal(0, temperatura * 0.5, n)
            np.clip(new_act, 0, 1, out=new_act)

            # Actualizar contadores para conceptos > 0.3
            high_idx = np.where(new_act > 0.3)[0]
            for i in high_idx:
                name = self._names[i]
                self.conceptos[name]['activaciones'] += 1
                self.conceptos[name]['ultima_activacion'] = ciclo

            act = new_act
            resultados.append(self._act_to_dict(act))

        self.metricas['ciclos_pensamiento'] += 1
        self.historial_activaciones.append({
            'inicio': concepto_inicial,
            'resultado': resultados[-1],
            'pasos': pasos
        })

        return resultados
    
    def auto_modificar(self, fuerza=0.1):
        """Auto-modificación vectorizada con numpy"""
        if not self.historial_activaciones:
            return 0

        ultima = self.historial_activaciones[-1]['resultado']

        # Obtener índices numpy de conceptos activos
        active_idx = np.array(
            [self._idx[c] for c, a in ultima.items() if a > 0.2 and c in self._idx],
            dtype=np.intp
        )

        if len(active_idx) < 2:
            return 0

        n_active = len(active_idx)
        modificaciones = 0

        # Submatriz de adyacencia para conceptos activos
        sub_adj = self._adj[np.ix_(active_idx, active_idx)]

        # Triángulo superior: pares únicos (i,j) con i < j
        upper = np.triu(np.ones((n_active, n_active), dtype=bool), k=1)

        # --- Reforzar aristas existentes ---
        existing = (sub_adj > 0) & upper
        if np.any(existing):
            random_inc = fuerza * np.random.random((n_active, n_active))
            new_weights = np.minimum(1.0, sub_adj + random_inc)

            pairs = np.where(existing)
            for k in range(len(pairs[0])):
                il, jl = pairs[0][k], pairs[1][k]
                ig, jg = int(active_idx[il]), int(active_idx[jl])
                new_w = float(new_weights[il, jl])

                # Actualizar matriz numpy (bidireccional)
                self._adj[ig, jg] = new_w
                self._adj[jg, ig] = new_w

                c1, c2 = self._names[ig], self._names[jg]
                self.grafo[c1][c2]['weight'] = new_w

                # Actualizar listas de relaciones
                for idx, (vecino, _) in enumerate(self.relaciones[c1]):
                    if vecino == c2:
                        self.relaciones[c1][idx] = (vecino, new_w)
                for idx, (vecino, _) in enumerate(self.relaciones[c2]):
                    if vecino == c1:
                        self.relaciones[c2][idx] = (vecino, new_w)

                modificaciones += 1

        # --- Crear nuevas conexiones con baja probabilidad ---
        non_existing = (~(sub_adj > 0)) & upper
        create_mask = non_existing & (np.random.random((n_active, n_active)) < fuerza * 0.5)

        if np.any(create_mask):
            pairs = np.where(create_mask)
            for k in range(len(pairs[0])):
                ig = int(active_idx[pairs[0][k]])
                jg = int(active_idx[pairs[1][k]])
                self.relacionar(self._names[ig], self._names[jg])
                modificaciones += 1

        if modificaciones > 0:
            self.metricas['auto_modificaciones'] += 1

        return modificaciones
    
    def guardar(self, ruta='ianae_estado.json'):
        """Guarda el estado actual del sistema a un archivo"""
        try:
            estado = {
                'metricas': self.metricas,
                'dim_vector': self.dim_vector,
                'incertidumbre_base': self.incertidumbre_base,
                'conceptos': {},
                'relaciones': [],
                'categorias': self.categorias,
                'timestamp': datetime.now().isoformat()
            }
            
            # Guardar conceptos
            for nombre, datos in self.conceptos.items():
                estado['conceptos'][nombre] = {
                    'base': datos['base'].tolist(),
                    'actual': datos['actual'].tolist(),
                    'creado': datos['creado'],
                    'activaciones': datos['activaciones'],
                    'ultima_activacion': datos['ultima_activacion'],
                    'fuerza': datos['fuerza'],
                    'categoria': datos['categoria'],
                    'conexiones_proyecto': datos['conexiones_proyecto']
                }
                
            # Guardar relaciones
            for origen in self.relaciones:
                for destino, peso in self.relaciones[origen]:
                    estado['relaciones'].append({
                        'origen': origen,
                        'destino': destino,
                        'peso': peso
                    })
                    
            # Guardar a archivo
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump(estado, f, indent=2)
                
            return True
        
        except Exception as e:
            print(f"Error al guardar: {e}")
            return False
    
    @classmethod
    def cargar(cls, ruta='ianae_estado.json'):
        """Carga el sistema desde un archivo guardado"""
        try:
            if not os.path.exists(ruta):
                print(f"El archivo {ruta} no existe")
                return None
                
            with open(ruta, 'r', encoding='utf-8') as f:
                estado = json.load(f)
                
            # Crear nueva instancia
            sistema = cls(
                dim_vector=estado.get('dim_vector', 15),
                incertidumbre_base=estado.get('incertidumbre_base', 0.2)
            )
            
            # Cargar métricas y categorías
            sistema.metricas = estado.get('metricas', {})
            sistema.categorias = estado.get('categorias', {})
            
            # Cargar conceptos
            for nombre, datos in estado.get('conceptos', {}).items():
                base = np.array(datos['base'])
                actual = np.array(datos['actual'])
                
                sistema.conceptos[nombre] = {
                    'base': base,
                    'actual': actual,
                    'historial': [base.copy()],
                    'creado': datos.get('creado', 0),
                    'activaciones': datos.get('activaciones', 0),
                    'ultima_activacion': datos.get('ultima_activacion', 0),
                    'fuerza': datos.get('fuerza', 1.0),
                    'categoria': datos.get('categoria', 'emergentes'),
                    'conexiones_proyecto': datos.get('conexiones_proyecto', 0)
                }
                
                sistema.grafo.add_node(nombre)
                
            # Cargar relaciones
            for rel in estado.get('relaciones', []):
                origen = rel['origen']
                destino = rel['destino']
                peso = rel['peso']
                
                sistema.relaciones[origen].append((destino, peso))
                sistema.grafo.add_edge(origen, destino, weight=peso)

            # Reconstruir estructuras numpy desde los dicts cargados
            sistema._rebuild_numpy()

            return sistema
            
        except Exception as e:
            print(f"Error al cargar: {e}")
            return None
    
    def ciclo_vital(self, num_ciclos=1, auto_mod=True, visualizar_cada=5):
        """Ejecuta un ciclo completo de vida del sistema"""
        resultados = []
        
        for i in range(num_ciclos):
            self.metricas['edad'] += 1
            
            if not self.conceptos:
                break
                
            # Elegir concepto con probabilidad ponderada
            conceptos = list(self.conceptos.keys())
            pesos = [self.conceptos[c]['activaciones'] + 1 for c in conceptos]
            total = sum(pesos)
            probabilidades = [p/total for p in pesos]
            
            concepto_inicial = np.random.choice(conceptos, p=probabilidades)
            
            # Activar el concepto
            pasos = random.randint(2, 4)
            resultado = self.activar(concepto_inicial, pasos=pasos, temperatura=0.2)
            
            # Auto-modificación
            if auto_mod and random.random() < 0.8:
                self.auto_modificar(fuerza=0.15)
                
            resultados.append({
                'ciclo': i,
                'concepto_inicial': concepto_inicial,
                'activacion_final': resultado[-1] if resultado else None
            })
            
        return resultados

    # ========== GENESIS: Creación dinámica de conceptos ==========

    def genesis_concepto(self, padres, nombre_emergente=None):
        """
        Crea un concepto nuevo fusionando vectores de conceptos padres.

        Args:
            padres: Lista de nombres de conceptos padre (minimo 2).
            nombre_emergente: Nombre del nuevo concepto. Si None, auto-genera.

        Returns:
            Nombre del concepto creado.

        Raises:
            ValueError: Si algun padre no existe o hay menos de 2 padres.
        """
        if len(padres) < 2:
            raise ValueError("Se necesitan al menos 2 conceptos padres")

        for padre in padres:
            if padre not in self.conceptos:
                raise ValueError(f"Concepto padre '{padre}' no existe")

        # Vector fusionado: promedio de vectores padres + ruido
        vectores = [self.conceptos[p]['actual'] for p in padres]
        vector_fusionado = np.mean(vectores, axis=0)
        ruido = np.random.normal(0, self.incertidumbre_base * 0.5, self.dim_vector)
        vector_fusionado = vector_fusionado + ruido

        # Nombre auto-generado
        if nombre_emergente is None:
            ts = int(time.time()) if 'time' in dir() else self.metricas['edad']
            nombre_emergente = f"EMG_{'_'.join(padres[:2])}_{ts}"

        # Crear concepto
        self.añadir_concepto(
            nombre_emergente,
            atributos=vector_fusionado,
            categoria='emergentes',
        )

        # Crear conexiones con cada padre
        for padre in padres:
            self.relacionar(nombre_emergente, padre, fuerza=0.7, bidireccional=True)

        # Guardar linaje
        self.conceptos[nombre_emergente]['genesis'] = {
            'padres': list(padres),
            'ts': self.metricas['edad'],
        }

        self.metricas['conceptos_creados'] += 1

        return nombre_emergente

    def detectar_candidatos_genesis(self, umbral_coactivacion=0.5):
        """
        Analiza historial de activaciones para encontrar pares de conceptos
        de diferente categoria que se co-activan frecuentemente.

        Returns:
            Lista de (concepto1, concepto2, frecuencia).
        """
        ultimas = self.historial_activaciones[-5:] if self.historial_activaciones else []
        if len(ultimas) < 2:
            return []

        # Contar co-activaciones
        from collections import Counter
        coactivaciones = Counter()

        for activacion in ultimas:
            # historial_activaciones guarda {'inicio': str, 'resultado': dict}
            if isinstance(activacion, dict) and 'resultado' in activacion:
                activos = activacion['resultado']
            elif isinstance(activacion, dict):
                activos = activacion
            elif isinstance(activacion, list) and activacion:
                activos = activacion[-1] if isinstance(activacion[-1], dict) else {}
            else:
                continue

            conceptos_activos = [c for c, v in activos.items()
                                 if isinstance(v, (int, float)) and v > 0.1
                                 and c in self.conceptos]

            for i, c1 in enumerate(conceptos_activos):
                for c2 in conceptos_activos[i + 1:]:
                    cat1 = self.conceptos[c1].get('categoria', 'emergentes')
                    cat2 = self.conceptos[c2].get('categoria', 'emergentes')
                    if cat1 != cat2:
                        par = tuple(sorted([c1, c2]))
                        coactivaciones[par] += 1

        # Filtrar por umbral (normalizado a [0,1])
        n = max(len(ultimas), 1)
        candidatos = []
        for (c1, c2), count in coactivaciones.most_common():
            freq = count / n
            if freq >= umbral_coactivacion:
                candidatos.append((c1, c2, freq))

        return candidatos

    def ciclo_genesis(self, max_nuevos=3):
        """
        Ejecuta un ciclo completo de genesis:
        1. Detectar candidatos
        2. Crear conceptos emergentes
        3. Retornar nombres creados

        Returns:
            Lista de nombres de conceptos nuevos creados.
        """
        candidatos = self.detectar_candidatos_genesis()
        creados = []

        for c1, c2, freq in candidatos[:max_nuevos]:
            try:
                nombre = self.genesis_concepto([c1, c2])
                creados.append(nombre)
            except ValueError:
                continue

        return creados

    def buscar_por_similitud_coseno(self, nombre_concepto, top_k=5):
        """
        Busca los conceptos mas similares usando el IndiceEspacial (vectorizado).

        Args:
            nombre_concepto: nombre del concepto de referencia
            top_k: numero maximo de resultados

        Returns:
            Lista de (nombre_concepto, similitud) ordenada de mayor a menor.
            No incluye el concepto de referencia.
        """
        if nombre_concepto not in self.conceptos:
            return []

        ref = self.conceptos[nombre_concepto]['actual']
        return self.indice.buscar_similares(ref, top_k=top_k, excluir_id=nombre_concepto)

    def guardar_estado(self, nombre: str = "default", versionar: bool = True) -> bool:
        """
        Guardar todos los conceptos actuales en SQLite.

        Args:
            nombre: prefijo para identificar este snapshot.

        Returns:
            True si se guardó correctamente.
        """
        try:
            for concepto_nombre, data in self.conceptos.items():
                clave = f"{nombre}::{concepto_nombre}"
                meta = {
                    "categoria": data.get("categoria", "emergentes"),
                    "fuerza": data.get("fuerza", 1.0),
                    "activaciones": data.get("activaciones", 0),
                    "snapshot": nombre,
                }
                self.persistencia.guardar_vector(clave, data["actual"], meta)
            if versionar:
                self.versionado.guardar_con_version(nombre, self.conceptos)
            return True
        except Exception:
            return False

    def cargar_version(self, version_id: int) -> bool:
        """
        Cargar una version especifica y restaurar vectores.

        Returns:
            True si se cargo correctamente.
        """
        import numpy as np
        datos = self.versionado.cargar_version(version_id)
        if not datos:
            return False
        cargados = 0
        for nombre, info in datos["conceptos"].items():
            if nombre in self.conceptos:
                vec = np.array(info["vector"])
                self.conceptos[nombre]["actual"] = vec
                self.indice.actualizar(nombre, vec)
                cargados += 1
        return cargados > 0

    def cargar_estado(self, nombre: str = "default") -> bool:
        """
        Cargar conceptos desde SQLite y restaurar vectores.

        Args:
            nombre: prefijo del snapshot a cargar.

        Returns:
            True si se cargó al menos un concepto.
        """
        try:
            items = self.persistencia.listar_vectores(limite=10000)
            prefix = f"{nombre}::"
            cargados = 0
            for clave, meta, _ts in items:
                if not clave.startswith(prefix):
                    continue
                concepto_nombre = clave[len(prefix):]
                vec, _ = self.persistencia.cargar_vector(clave)
                if vec is not None and concepto_nombre in self.conceptos:
                    self.conceptos[concepto_nombre]["actual"] = vec
                    self.indice.actualizar(concepto_nombre, vec)
                    cargados += 1
            return cargados > 0
        except Exception:
            return False


# Función de inicialización específica para Lucas
def crear_universo_lucas():
    """Crea el universo conceptual completo de Lucas"""
    print("🚀 INICIALIZANDO UNIVERSO CONCEPTUAL DE LUCAS...")
    
    # Crear sistema
    sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.15)
    
    # Crear conceptos base
    conceptos = sistema.crear_conceptos_lucas()
    
    # Establecer relaciones de proyectos
    relaciones = sistema.crear_relaciones_lucas()
    
    print(f"✅ UNIVERSO CREADO:")
    print(f"   • {len(conceptos)} conceptos")
    print(f"   • {relaciones} relaciones")
    print("🔥 ¡Listo para experimentar!")
    
    return sistema

if __name__ == "__main__":
    # Test básico
    sistema = crear_universo_lucas()
    sistema.informe_lucas()
    sistema.visualizar_lucas()
