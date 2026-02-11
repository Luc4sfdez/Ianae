# nucleo_lucas.py - IANAE adaptado para proyectos de Lucas
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import random
import json
import os
from datetime import datetime

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
            self.añadir_concepto(nombre, atributos=vector)
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
        
        # Añadir a categoría si no es emergente
        if categoria != 'emergentes' and categoria in self.categorias:
            if nombre not in self.categorias[categoria]:
                self.categorias[categoria].append(nombre)
        else:
            self.categorias['emergentes'].append(nombre)
            
        return nombre
    
    def relacionar(self, concepto1, concepto2, fuerza=None, bidireccional=True):
        """
        Versión extendida con métricas de proyecto
        """
        if concepto1 not in self.conceptos or concepto2 not in self.conceptos:
            return 0
            
        if fuerza is None:
            v1 = self.conceptos[concepto1]['actual']
            v2 = self.conceptos[concepto2]['actual']
            similitud_base = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            fuerza = max(0.1, min(1.0, similitud_base + np.random.normal(0, 0.1)))
        
        self.relaciones[concepto1].append((concepto2, fuerza))
        if bidireccional:
            self.relaciones[concepto2].append((concepto1, fuerza))
            
        self.grafo.add_edge(concepto1, concepto2, weight=fuerza)
        self.metricas['conexiones_formadas'] += 1
        
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
    
    # Heredar métodos del nucleo original con adaptaciones mínimas
    def activar(self, concepto_inicial, pasos=3, temperatura=0.1):
        """Heredado de ConceptosDifusos con métricas adicionales"""
        if concepto_inicial not in self.conceptos:
            return []
            
        # Incrementar métricas específicas
        categoria = self.conceptos[concepto_inicial]['categoria'] 
        if categoria in ['tecnologias', 'proyectos']:
            self.metricas['tecnologias_conectadas'] += 1
            
        self.conceptos[concepto_inicial]['activaciones'] += 1
        self.conceptos[concepto_inicial]['ultima_activacion'] = self.metricas['ciclos_pensamiento']
        
        activacion = {c: 0.0 for c in self.conceptos}
        activacion[concepto_inicial] = 1.0
        
        resultados = [activacion.copy()]
        
        for paso in range(pasos):
            nueva_activacion = activacion.copy()
            
            for concepto, nivel in activacion.items():
                if nivel > 0.1:
                    for vecino, fuerza in self.relaciones[concepto]:
                        factor_aleatorio = np.random.uniform(1 - temperatura, 1 + temperatura)
                        propagacion = nivel * fuerza * factor_aleatorio
                        nueva_activacion[vecino] = max(nueva_activacion[vecino], propagacion)
            
            # Normalización
            total = sum(nueva_activacion.values()) + 1e-10
            for c in nueva_activacion:
                nueva_activacion[c] = nueva_activacion[c] / total
                nueva_activacion[c] += np.random.normal(0, temperatura * 0.5)
                nueva_activacion[c] = max(0, min(1, nueva_activacion[c]))
                
                if nueva_activacion[c] > 0.3:
                    self.conceptos[c]['activaciones'] += 1
                    self.conceptos[c]['ultima_activacion'] = self.metricas['ciclos_pensamiento']
                
            activacion = nueva_activacion
            resultados.append(activacion.copy())
        
        self.metricas['ciclos_pensamiento'] += 1
        self.historial_activaciones.append({
            'inicio': concepto_inicial,
            'resultado': resultados[-1],
            'pasos': pasos
        })
        
        return resultados
    
    def auto_modificar(self, fuerza=0.1):
        """Auto-modificación con detección de emergencias"""
        modificaciones = super().auto_modificar(fuerza) if hasattr(super(), 'auto_modificar') else 0
        
        # Implementación básica si no existe super()
        if not self.historial_activaciones:
            return 0
            
        modificaciones = 0
        ultima = self.historial_activaciones[-1]['resultado']
        conceptos_activos = [c for c, a in ultima.items() if a > 0.2]
        
        if len(conceptos_activos) < 2:
            return 0
        
        # Reforzar conexiones entre conceptos activos
        for i in range(len(conceptos_activos)):
            for j in range(i+1, len(conceptos_activos)):
                c1, c2 = conceptos_activos[i], conceptos_activos[j]
                
                if self.grafo.has_edge(c1, c2):
                    peso_actual = self.grafo[c1][c2]['weight']
                    nuevo_peso = min(1.0, peso_actual + fuerza * np.random.random())
                    self.grafo[c1][c2]['weight'] = nuevo_peso
                    
                    # Actualizar relaciones
                    for idx, (vecino, peso) in enumerate(self.relaciones[c1]):
                        if vecino == c2:
                            self.relaciones[c1][idx] = (vecino, nuevo_peso)
                    for idx, (vecino, peso) in enumerate(self.relaciones[c2]):
                        if vecino == c1:
                            self.relaciones[c2][idx] = (vecino, nuevo_peso)
                    modificaciones += 1
                    
                elif np.random.random() < fuerza * 0.5:
                    self.relacionar(c1, c2)
                    modificaciones += 1
        
        if modificaciones > 0:
            self.metricas['auto_modificaciones'] += 1
            
        return modificaciones


# Función de inicialización específica para Lucas
def crear_universo_lucas():
    """
    Crea el universo conceptual completo de Lucas con todos sus proyectos
    """
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

    def guardar(self, ruta='ianae_estado.json'):
    """
    Guarda el estado actual del sistema a un archivo
    
    Args:
        ruta: Ruta del archivo donde guardar
        
    Returns:
        True si se guardó correctamente
    """
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
        
        # Guardar conceptos (serializar numpy arrays)
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
    """
    Carga el sistema desde un archivo guardado
    
    Args:
        ruta: Ruta del archivo a cargar
        
    Returns:
        Instancia de ConceptosLucas con el estado cargado
    """
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
        
        # Cargar métricas
        sistema.metricas = estado.get('metricas', {})
        
        # Cargar categorías
        sistema.categorias = estado.get('categorias', {})
        
        # Cargar conceptos
        for nombre, datos in estado.get('conceptos', {}).items():
            base = np.array(datos['base'])
            actual = np.array(datos['actual'])
            
            # Añadir concepto directamente al diccionario
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
            
            # Añadir nodo al grafo
            sistema.grafo.add_node(nombre)
            
        # Cargar relaciones
        for rel in estado.get('relaciones', []):
            origen = rel['origen']
            destino = rel['destino']
            peso = rel['peso']
            
            # Añadir a la lista de relaciones
            sistema.relaciones[origen].append((destino, peso))
            
            # Añadir al grafo
            sistema.grafo.add_edge(origen, destino, weight=peso)
            
        return sistema
        
    except Exception as e:
        print(f"Error al cargar: {e}")
        return None

def ciclo_vital(self, num_ciclos=1, auto_mod=True, visualizar_cada=5):
    """
    Ejecuta un ciclo completo de vida del sistema
    """
    resultados = []
    
    for i in range(num_ciclos):
        self.metricas['edad'] += 1
        
        # Seleccionar un concepto para activar
        if not self.conceptos:
            break
            
        # Elegir con probabilidad ponderada
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
            
        # Ocasionalmente generar nuevos conceptos
        if random.random() < 0.1:
            nuevos = self.generar_concepto(numero=1)
            
        # Visualizar si corresponde
        if visualizar_cada > 0 and i % visualizar_cada == 0:
            titulo = f"Ciclo {i+1}/{num_ciclos} - Activación desde '{concepto_inicial}'"
            self.visualizar_lucas(
                activaciones=resultado[-1] if resultado else None
            )
            
        resultados.append({
            'ciclo': i,
            'concepto_inicial': concepto_inicial,
            'activacion_final': resultado[-1] if resultado else None
        })
        
    return resultados

def generar_concepto(self, conceptos_base=None, numero=1):
    """
    Genera nuevos conceptos basados en combinaciones existentes
    """
    if len(self.conceptos) < 2:
        return []
        
    nuevos_conceptos = []
    
    for _ in range(numero):
        # Elegir conceptos base
        if conceptos_base is None or len(conceptos_base) < 2:
            conceptos_candidatos = list(self.conceptos.keys())
            peso_activacion = [self.conceptos[c]['activaciones'] + 1 for c in conceptos_candidatos]
            
            # Normalizar pesos
            suma = sum(peso_activacion)
            probs = [p/suma for p in peso_activacion]
            
            # Elegir 2-3 conceptos
            num_conceptos = random.randint(2, min(3, len(conceptos_candidatos)))
            conceptos_base = np.random.choice(
                conceptos_candidatos, 
                size=num_conceptos, 
                replace=False, 
                p=probs
            )
        
        # Combinar vectores base
        vector_combinado = np.zeros(self.dim_vector)
        for c in conceptos_base:
            if c in self.conceptos:
                vector_combinado += self.conceptos[c]['base'] * np.random.uniform(0.5, 1.5)
                
        # Normalizar y añadir ruido
        if np.linalg.norm(vector_combinado) > 0:
            vector_combinado = vector_combinado / np.linalg.norm(vector_combinado)
            vector_combinado += np.random.normal(0, 0.3, self.dim_vector)
            
            # Crear nombre
            nuevo_nombre = f"concepto_emergente_{len(self.conceptos)}"
            
            # Crear el nuevo concepto
            self.añadir_concepto(nuevo_nombre, vector_combinado, categoria='emergentes')
            nuevos_conceptos.append(nuevo_nombre)
            
            # Relacionarlo con los conceptos base
            for c in conceptos_base:
                if c in self.conceptos:
                    self.relacionar(nuevo_nombre, c)
    
    return nuevos_conceptos

if __name__ == "__main__":
    # Test básico
    sistema = crear_universo_lucas()
    sistema.informe_lucas()
    sistema.visualizar_lucas()
