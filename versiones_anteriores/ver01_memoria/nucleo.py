import numpy as np
import numpy.typing as npt
from numpy import float64
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import random
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from .nucleo_types import ConceptoData, MetricasData, ActivacionHistorial, ConceptosType, RelacionesType

class ConceptosDifusos:
    def __init__(self, dim_vector: int = 10, incertidumbre_base: float = 0.2) -> None:
        """Inicializa el sistema de conceptos difusos.
        
        Args:
            dim_vector (int): Dimensionalidad de los vectores conceptuales (10-50)
            incertidumbre_base (float): Nivel base de incertidumbre (0.1-0.5)
            
        Attributes:
            conceptos (Dict): Diccionario de conceptos con sus propiedades
            relaciones (Dict): Relaciones entre conceptos y sus pesos
            grafo (nx.Graph): Representación gráfica de la red conceptual
            dim_vector (int): Dimensión de los vectores de atributos
            incertidumbre_base (float): Incertidumbre base para nuevos conceptos
            historial_activaciones (List): Registro de activaciones pasadas
            metricas (Dict): Estadísticas del sistema
        """
        self.conceptos: ConceptosType = {}
        self.relaciones: RelacionesType = defaultdict(list)
        self.grafo: nx.Graph = nx.Graph()
        self.dim_vector: int = dim_vector
        self.incertidumbre_base: float = incertidumbre_base
        self.historial_activaciones: List[ActivacionHistorial] = []
        self.metricas: MetricasData = {
            'edad': 0,
            'conceptos_creados': 0,
            'conexiones_formadas': 0,
            'ciclos_pensamiento': 0,
            'auto_modificaciones': 0
        }
        
    def añadir_concepto(self, nombre: str, atributos: Optional[npt.NDArray[float64]] = None, 
                       incertidumbre: Optional[float] = None) -> str:
        """Crea un nuevo concepto en el sistema.
        
        Args:
            nombre (str): Identificador único del concepto
            atributos (Optional[npt.NDArray]): Vector de atributos preexistente
            incertidumbre (Optional[float]): Nivel de incertidumbre específico
            
        Returns:
            str: Nombre del concepto creado
            
        Raises:
            ValueError: Si el nombre ya existe o los atributos tienen dimensión incorrecta
            
        Example:
            >>> sistema = ConceptosDifusos()
            >>> sistema.añadir_concepto("pensamiento")
            'pensamiento'
        """
        if incertidumbre is None:
            incertidumbre = self.incertidumbre_base
            
        if atributos is None:
            # Vector aleatorio para representar el concepto
            atributos = np.random.normal(0, 1, self.dim_vector)
            
        # Normalizar el vector para consistencia
        atributos = atributos / np.linalg.norm(atributos)
        
        # Añadir ruido para representar incertidumbre inherente
        ruido = np.random.normal(0, incertidumbre, atributos.shape)
        self.conceptos[nombre] = {
            'base': atributos.copy(),
            'actual': atributos + ruido,  # Versión con incertidumbre
            'historial': [atributos.copy()],  # Para seguir evolución
            'creado': self.metricas['edad'],
            'activaciones': 0,
            'ultima_activacion': 0,
            'fuerza': 1.0  # Fuerza inicial del concepto
        }
        self.grafo.add_node(nombre)
        self.metricas['conceptos_creados'] += 1
        return nombre
    
    def relacionar(self, concepto1: str, concepto2: str, fuerza: Optional[float] = None, 
                 bidireccional: bool = True) -> float:
        """
        Crea una relación probabilística entre conceptos
        
        Args:
            concepto1: Primer concepto
            concepto2: Segundo concepto
            fuerza: Intensidad de la relación (opcional)
            bidireccional: Si la relación es en ambos sentidos
            
        Returns:
            Fuerza de la relación establecida (0 si falla)
        """
        # Verificar que ambos conceptos existan
        if concepto1 not in self.conceptos or concepto2 not in self.conceptos:
            return 0
            
        if fuerza is None:
            # La similitud se basa en la distancia coseno con ruido
            v1 = self.conceptos[concepto1]['actual']
            v2 = self.conceptos[concepto2]['actual']
            similitud_base = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            fuerza = max(0.1, min(1.0, similitud_base + np.random.normal(0, 0.1)))
            
        self.relaciones[concepto1].append((concepto2, fuerza))
        if bidireccional:
            self.relaciones[concepto2].append((concepto1, fuerza))
            
        self.grafo.add_edge(concepto1, concepto2, weight=fuerza)
        self.metricas['conexiones_formadas'] += 1
        return fuerza
    
    def activar(self, concepto_inicial, pasos=3, temperatura=0.1):
        """
        Simula propagación de activación a través de la red conceptual
        
        Args:
            concepto_inicial: Concepto desde donde inicia la activación
            pasos: Número de pasos de propagación
            temperatura: Factor que controla la aleatoriedad del proceso
            
        Returns:
            Lista de diccionarios de activación para cada paso
        """
        # Verificar que el concepto inicial exista
        if concepto_inicial not in self.conceptos:
            return []
            
        # Incrementar contador de activaciones para este concepto
        self.conceptos[concepto_inicial]['activaciones'] += 1
        self.conceptos[concepto_inicial]['ultima_activacion'] = self.metricas['ciclos_pensamiento']
        
        activacion = {c: 0.0 for c in self.conceptos}
        activacion[concepto_inicial] = 1.0
        
        resultados = [activacion.copy()]
        
        for _ in range(pasos):
            nueva_activacion = activacion.copy()
            
            # Propagación de la activación en paralelo (simulado)
            for concepto, nivel in activacion.items():
                if nivel > 0.1:  # Umbral de activación
                    for vecino, fuerza in self.relaciones[concepto]:
                        # La activación se propaga según la fuerza de conexión
                        # con un elemento estocástico
                        factor_aleatorio = np.random.uniform(1 - temperatura, 1 + temperatura)
                        propagacion = nivel * fuerza * factor_aleatorio
                        nueva_activacion[vecino] = max(nueva_activacion[vecino], propagacion)
            
            # Normalización y adición de ruido para simular pensamiento no determinista
            total = sum(nueva_activacion.values()) + 1e-10
            for c in nueva_activacion:
                nueva_activacion[c] = nueva_activacion[c] / total
                nueva_activacion[c] += np.random.normal(0, temperatura * 0.5)
                nueva_activacion[c] = max(0, min(1, nueva_activacion[c]))
                
                # Actualizar métricas de activación para los conceptos muy activos
                if nueva_activacion[c] > 0.3:
                    self.conceptos[c]['activaciones'] += 1
                    self.conceptos[c]['ultima_activacion'] = self.metricas['ciclos_pensamiento']
                
            activacion = nueva_activacion
            resultados.append(activacion.copy())
        
        # Actualizar métricas globales
        self.metricas['ciclos_pensamiento'] += 1
        self.historial_activaciones.append({
            'inicio': concepto_inicial,
            'resultado': resultados[-1],
            'pasos': pasos
        })
        
        return resultados
    
    def auto_modificar(self, fuerza=0.1):
        """
        Permite que el sistema modifique sus propias conexiones basado en la historia
        de activaciones para simular aprendizaje
        
        Args:
            fuerza: Intensidad del proceso de auto-modificación
            
        Returns:
            Número de modificaciones realizadas
        """
        if not self.historial_activaciones:
            return 0
            
        modificaciones = 0
        
        # Obtener la última activación
        ultima = self.historial_activaciones[-1]['resultado']
        conceptos_activos = [c for c, a in ultima.items() if a > 0.2]
        
        if len(conceptos_activos) < 2:
            return 0
            
        # Reforzar conexiones entre conceptos activos simultáneamente
        for i in range(len(conceptos_activos)):
            for j in range(i+1, len(conceptos_activos)):
                c1 = conceptos_activos[i]
                c2 = conceptos_activos[j]
                
                # Si ya hay conexión, reforzarla
                if self.grafo.has_edge(c1, c2):
                    peso_actual = self.grafo[c1][c2]['weight']
                    nuevo_peso = min(1.0, peso_actual + fuerza * np.random.random())
                    self.grafo[c1][c2]['weight'] = nuevo_peso
                    
                    # Actualizar en las relaciones
                    for idx, (vecino, peso) in enumerate(self.relaciones[c1]):
                        if vecino == c2:
                            self.relaciones[c1][idx] = (vecino, nuevo_peso)
                    
                    for idx, (vecino, peso) in enumerate(self.relaciones[c2]):
                        if vecino == c1:
                            self.relaciones[c2][idx] = (vecino, nuevo_peso)
                            
                    modificaciones += 1
                
                # Si no hay conexión, considerar crearla
                elif np.random.random() < fuerza * 0.5:
                    self.relacionar(c1, c2)
                    modificaciones += 1
                    
        # Debilitar conexiones poco usadas
        if np.random.random() < 0.3:  # No siempre se realiza este paso
            for c1 in self.conceptos:
                for vecino, peso in list(self.relaciones[c1]):
                    # Si ambos conceptos no han sido activados recientemente
                    if (self.metricas['ciclos_pensamiento'] - self.conceptos[c1]['ultima_activacion'] > 10 and
                        self.metricas['ciclos_pensamiento'] - self.conceptos[vecino]['ultima_activacion'] > 10):
                        
                        nuevo_peso = max(0.05, peso - fuerza * 0.2 * np.random.random())
                        
                        # Actualizar peso
                        for idx, (v, p) in enumerate(self.relaciones[c1]):
                            if v == vecino:
                                self.relaciones[c1][idx] = (v, nuevo_peso)
                                
                        for idx, (v, p) in enumerate(self.relaciones[vecino]):
                            if v == c1:
                                self.relaciones[vecino][idx] = (v, nuevo_peso)
                                
                        # Actualizar grafo
                        self.grafo[c1][vecino]['weight'] = nuevo_peso
                        modificaciones += 1
                        
        # Actualizar métricas
        if modificaciones > 0:
            self.metricas['auto_modificaciones'] += 1
            
        return modificaciones
    
    def generar_concepto(self, conceptos_base=None, numero=1):
        """
        Genera nuevos conceptos basados en combinaciones de conceptos existentes
        
        Args:
            conceptos_base: Lista de conceptos para combinar (si es None, se eligen aleatoriamente)
            numero: Número de conceptos a generar
            
        Returns:
            Lista de los nuevos conceptos generados
        """
        if len(self.conceptos) < 2:
            return []
            
        nuevos_conceptos = []
        
        for _ in range(numero):
            # Elegir conceptos base aleatoriamente si no se especifican
            if conceptos_base is None or len(conceptos_base) < 2:
                conceptos_candidatos = list(self.conceptos.keys())
                peso_activacion = [self.conceptos[c]['activaciones'] + 1 for c in conceptos_candidatos]
                
                # Normalizar pesos para usar como probabilidades
                suma = sum(peso_activacion)
                probs = [p/suma for p in peso_activacion]
                
                # Elegir 2-3 conceptos con preferencia por los más activos
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
                
                # Crear nombre para el nuevo concepto
                nuevo_nombre = f"concepto_{len(self.conceptos)}"
                
                # Crear el nuevo concepto
                self.añadir_concepto(nuevo_nombre, vector_combinado)
                nuevos_conceptos.append(nuevo_nombre)
                
                # Relacionarlo con los conceptos base
                for c in conceptos_base:
                    if c in self.conceptos:
                        self.relacionar(nuevo_nombre, c)
        
        return nuevos_conceptos
    
    def visualizar(self, activaciones=None, titulo=None, mostrar_etiquetas=True, tamaño=(12, 10)):
        """
        Visualiza la red conceptual y opcionalmente la activación
        
        Args:
            activaciones: Diccionario de activaciones para los nodos
            titulo: Título para la visualización
            mostrar_etiquetas: Si se muestran las etiquetas de los nodos
            tamaño: Tamaño de la figura
        """
        plt.figure(figsize=tamaño)
        
        if not titulo:
            titulo = f"Red conceptual - {len(self.conceptos)} conceptos, {self.grafo.number_of_edges()} conexiones"
        
        plt.title(titulo)
        
        # Usar layout basado en fuerza para posicionar nodos
        pos = nx.spring_layout(self.grafo, k=0.3, iterations=50)
        
        # Preparar colores y tamaños de nodos
        colores = []
        tamaños = []
        
        for n in self.grafo.nodes:
            # Color según activación o edad (rojo = reciente/activo, azul = antiguo/inactivo)
            if activaciones and n in activaciones:
                # Escala de rojo según activación
                intensidad = min(1.0, activaciones[n])
                colores.append((intensidad, 0.2, 1.0 - intensidad))
                tamaños.append(300 + 700 * intensidad)
            else:
                # Sin activación, usar edad del concepto
                edad_rel = max(0, min(1, self.conceptos[n]['creado'] / max(1, self.metricas['edad'])))
                colores.append((0.2, 0.2, 0.8 - 0.6 * edad_rel))
                tamaños.append(200)
        
        # Dibujar nodos
        nx.draw_networkx_nodes(
            self.grafo, pos, 
            node_color=colores,
            node_size=tamaños,
            alpha=0.8
        )
        
        # Preparar aristas con grosor basado en fuerza
        edges = self.grafo.edges(data=True)
        weights = [d['weight'] * 5 for u, v, d in edges]
        edge_colors = [(0.5, 0.5, 0.5, min(1.0, w/5)) for w in weights]
        
        # Dibujar aristas
        nx.draw_networkx_edges(
            self.grafo, 
            pos, 
            width=weights, 
            edge_color=edge_colors,
            alpha=0.6
        )
        
        # Etiquetas si se solicitan
        if mostrar_etiquetas:
            # Filtrar para mostrar solo etiquetas importantes
            if len(self.conceptos) > 20:
                # Mostrar solo conceptos activos o importantes
                nodos_a_mostrar = set()
                
                if activaciones:
                    nodos_a_mostrar.update([n for n, a in activaciones.items() if a > 0.2])
                
                # Añadir nodos con muchas conexiones
                grados = dict(self.grafo.degree())
                nodos_por_grado = sorted(grados.items(), key=lambda x: x[1], reverse=True)
                nodos_a_mostrar.update([n for n, g in nodos_por_grado[:10]])
                
                # Crear diccionario filtrado de etiquetas
                etiquetas = {n: n for n in nodos_a_mostrar}
            else:
                etiquetas = {n: n for n in self.grafo.nodes}
                
            nx.draw_networkx_labels(
                self.grafo, 
                pos, 
                labels=etiquetas,
                font_size=10,
                font_weight='bold'
            )
        
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
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
                    'fuerza': datos['fuerza']
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
            Instancia de ConceptosDifusos con el estado cargado
        """
        try:
            if not os.path.exists(ruta):
                print(f"El archivo {ruta} no existe")
                return None
                
            with open(ruta, 'r', encoding='utf-8') as f:
                estado = json.load(f)
                
            # Crear nueva instancia
            sistema = cls(
                dim_vector=estado.get('dim_vector', 10),
                incertidumbre_base=estado.get('incertidumbre_base', 0.2)
            )
            
            # Cargar métricas
            sistema.metricas = estado.get('metricas', {})
            
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
                    'fuerza': datos.get('fuerza', 1.0)
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
        Ejecuta un ciclo completo de vida del sistema: activación, auto-modificación
        y generación de nuevos conceptos
        
        Args:
            num_ciclos: Número de ciclos a ejecutar
            auto_mod: Si se realizan auto-modificaciones
            visualizar_cada: Frecuencia de visualización (0 para no visualizar)
        """
        resultados = []
        
        for i in range(num_ciclos):
            self.metricas['edad'] += 1
            
            # Seleccionar un concepto para activar
            if not self.conceptos:
                break
                
            # Elegir con probabilidad ponderada por activaciones previas
            conceptos = list(self.conceptos.keys())
            pesos = [self.conceptos[c]['activaciones'] + 1 for c in conceptos]
            total = sum(pesos)
            probabilidades = [p/total for p in pesos]
            
            concepto_inicial = np.random.choice(conceptos, p=probabilidades)
            
            # Activar el concepto (con duración aleatoria)
            pasos = random.randint(2, 5)
            resultado = self.activar(concepto_inicial, pasos=pasos, temperatura=0.2)
            
            # Auto-modificación del sistema
            if auto_mod and random.random() < 0.8:  # 80% de probabilidad
                self.auto_modificar(fuerza=0.15)
                
            # Ocasionalmente generar nuevos conceptos
            if random.random() < 0.2:  # 20% de probabilidad
                self.generar_concepto(numero=random.randint(1, 2))
                
            # Visualizar si corresponde
            if visualizar_cada > 0 and i % visualizar_cada == 0:
                titulo = f"Ciclo {i+1}/{num_ciclos} - Activación desde '{concepto_inicial}'"
                self.visualizar(
                    activaciones=resultado[-1] if resultado else None,
                    titulo=titulo
                )
                
            resultados.append({
                'ciclo': i,
                'concepto_inicial': concepto_inicial,
                'activacion_final': resultado[-1] if resultado else None
            })
            
        return resultados
