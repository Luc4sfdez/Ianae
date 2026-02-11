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
        self.UMBRAL_ACTIVACION_MIN = 0.05  # Conceptos con activación menor se consideran inactivos (modo más exploratorio)
        self.UMBRAL_CONEXION_MIN = 0.02  # Conexiones con peso menor se eliminan (modo más exploratorio)
        
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
                conexiones_a_mantener = conexiones_ordenadas[:self.MAX_CONEXIONES_POR_CONCEPTO]
                conexiones_a_eliminar = conexiones_ordenadas[self.MAX_CONEXIONES_POR_CONCEPTO:]
                
                # Actualizar grafo eliminando las conexiones descartadas
                for dest, peso in conexiones_a_eliminar:
                    if self.sistema.grafo.has_edge(concepto, dest):
                        self.sistema.grafo.remove_edge(concepto, dest)
                
                # Actualizar lista de conexiones
                self.sistema.relaciones[concepto] = conexiones_a_mantener
                
                # Contar eliminadas
                conexiones_eliminadas += len(conexiones_a_eliminar)
        
        print(f"Conexiones limitadas: {conexiones_eliminadas}")
        return conexiones_eliminadas
    
    def apartar_conceptos_poco_activos(self):
        """
        Identifica y aparta conceptos interesantes pero con baja activación
        
        Returns:
            Lista de conceptos apartados
        """
        conceptos_apartados_ahora = []
        
        # Calcular umbral relativo basado en edad del sistema
        edad_min = max(10, self.sistema.metricas['edad'] / 10)
        
        # Buscar conceptos con baja tasa de activación pero que existen hace tiempo
        for nombre, datos in list(self.sistema.conceptos.items()):
            # Calcular ratio de activación (activaciones / edad desde creación)
            edad_concepto = self.sistema.metricas['edad'] - datos['creado']
            if edad_concepto < edad_min:
                continue  # Ignorar conceptos muy nuevos
                
            ratio_activacion = datos['activaciones'] / max(1, edad_concepto)
            
            # Si el concepto tiene baja activación pero tiene al menos algunas conexiones
            num_conexiones = len(self.sistema.relaciones.get(nombre, []))
            if ratio_activacion < 0.1 and num_conexiones >= 2:
                # Guardar información del concepto
                self.conceptos_apartados[nombre] = {
                    'vector': datos['base'].tolist(),
                    'actual': datos['actual'].tolist(),
                    'activaciones': datos['activaciones'],
                    'creado': datos['creado'],
                    'edad_cuando_apartado': self.sistema.metricas['edad'],
                    'conexiones': [(dest, peso) for dest, peso in self.sistema.relaciones.get(nombre, [])]
                }
                
                # Eliminar del sistema principal
                del self.sistema.conceptos[nombre]
                if nombre in self.sistema.relaciones:
                    del self.sistema.relaciones[nombre]
                
                # Eliminar nodo del grafo
                if nombre in self.sistema.grafo:
                    self.sistema.grafo.remove_node(nombre)
                
                # Eliminar de las relaciones de otros conceptos
                for c in self.sistema.relaciones:
                    self.sistema.relaciones[c] = [(dest, peso) for dest, peso in self.sistema.relaciones[c] 
                                                 if dest != nombre]
                
                conceptos_apartados_ahora.append(nombre)
        
        # Guardar conceptos apartados a disco
        if conceptos_apartados_ahora:
            self.guardar_conceptos_apartados()
            print(f"Conceptos apartados: {len(conceptos_apartados_ahora)}")
        
        return conceptos_apartados_ahora
    
    def guardar_conceptos_apartados(self):
        """
        Guarda los conceptos apartados a un archivo JSON
        """
        ruta = os.path.join(self.ruta_temp, "conceptos_apartados.json")
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(self.conceptos_apartados, f, indent=2)
    
    def cargar_conceptos_apartados(self):
        """
        Carga los conceptos apartados desde un archivo JSON
        
        Returns:
            Número de conceptos cargados
        """
        ruta = os.path.join(self.ruta_temp, "conceptos_apartados.json")
        if not os.path.exists(ruta):
            return 0
            
        with open(ruta, 'r', encoding='utf-8') as f:
            self.conceptos_apartados = json.load(f)
            
        return len(self.conceptos_apartados)
    
    def reincorporar_conceptos_apartados(self, num_conceptos=5):
        """
        Reincorpora algunos conceptos apartados al sistema principal
        
        Args:
            num_conceptos: Número de conceptos a reincorporar
            
        Returns:
            Lista de conceptos reincorporados
        """
        if not self.conceptos_apartados:
            return []
            
        # Ordenar conceptos apartados por número de conexiones
        conceptos_ordenados = sorted(
            self.conceptos_apartados.items(),
            key=lambda x: len(x[1]['conexiones']),
            reverse=True
        )
        
        # Tomar los primeros N conceptos
        a_reincorporar = conceptos_ordenados[:min(num_conceptos, len(conceptos_ordenados))]
        reincorporados = []
        
        for nombre, datos in a_reincorporar:
            # Comprobar que no exista ya un concepto con el mismo nombre
            if nombre in self.sistema.conceptos:
                continue
                
            # Recrear el concepto
            vector_base = np.array(datos['vector'])
            self.sistema.añadir_concepto(
                nombre=nombre,
                atributos=vector_base
            )
            
            # Restaurar métricas
            self.sistema.conceptos[nombre]['activaciones'] = datos['activaciones']
            self.sistema.conceptos[nombre]['creado'] = datos['creado']
            
            # Recrear conexiones que aún existan en el sistema
            for dest, peso in datos['conexiones']:
                if dest in self.sistema.conceptos:
                    self.sistema.relacionar(nombre, dest, fuerza=peso)
            
            # Eliminar del diccionario de apartados
            del self.conceptos_apartados[nombre]
            reincorporados.append(nombre)
        
        # Actualizar archivo de conceptos apartados
        self.guardar_conceptos_apartados()
        
        print(f"Conceptos reincorporados: {len(reincorporados)}")
        return reincorporados
    
    def optimizar_sistema(self):
        """
        Realiza todas las optimizaciones en un solo paso
        
        Returns:
            Dict con estadísticas de optimización
        """
        print("Optimizando sistema IANAE...")
        inicio = time.time()
        
        # Monitorear estado inicial
        estado_inicial = self.monitorear_recursos()
        
        # Aplicar todas las optimizaciones
        conexiones_podadas = self.podar_conexiones_debiles()
        conexiones_limitadas = self.limitar_conexiones_por_concepto()
        conceptos_apartados = self.apartar_conceptos_poco_activos()
        
        # Monitorear estado final
        estado_final = self.monitorear_recursos()
        tiempo = time.time() - inicio
        
        # Estadísticas
        stats = {
            'tiempo_optimizacion': tiempo,
            'memoria_inicial_mb': estado_inicial['memoria_usada'],
            'memoria_final_mb': estado_final['memoria_usada'],
            'conexiones_podadas': conexiones_podadas,
            'conexiones_limitadas': conexiones_limitadas,
            'conceptos_apartados': len(conceptos_apartados)
        }
        
        print(f"Optimización completada en {tiempo:.2f} segundos")
        print(f"Memoria: {estado_inicial['memoria_usada']:.1f}MB → {estado_final['memoria_usada']:.1f}MB")
        
        return stats
    
    def ciclo_vital_optimizado(self, num_ciclos_total=1000, ciclos_por_batch=None, 
                              visualizar_cada=0, optimizar_cada=None):
        """
        Ejecuta ciclos de vida con optimizaciones periódicas y guardado en disco
        
        Args:
            num_ciclos_total: Número total de ciclos a ejecutar
            ciclos_por_batch: Ciclos a ejecutar por batch antes de optimizar
            visualizar_cada: Frecuencia de visualización (0 para no visualizar)
            optimizar_cada: Cada cuántos ciclos optimizar (None para usar ciclos_por_batch)
            
        Returns:
            Dict con estadísticas de ejecución
        """
        if ciclos_por_batch is None:
            ciclos_por_batch = min(100, num_ciclos_total)
            
        if optimizar_cada is None:
            optimizar_cada = ciclos_por_batch
        
        tiempo_inicio_total = time.time()
        ciclos_completados = 0
        stats_totales = {
            'tiempo_total': 0,
            'tiempo_promedio_ciclo': 0,
            'num_optimizaciones': 0,
            'conceptos_generados': 0,
            'conexiones_creadas': 0,
            'memoria_max': 0
        }
        
        # Guardar estado inicial para comparación
        self.sistema.guardar(os.path.join(self.ruta_temp, "estado_inicial.json"))
        
        print(f"Iniciando ciclo vital optimizado: {num_ciclos_total} ciclos totales")
        print(f"Optimización cada {optimizar_cada} ciclos, batch de {ciclos_por_batch}")
        
        try:
            while ciclos_completados < num_ciclos_total:
                # Calcular ciclos para este batch
                ciclos_restantes = num_ciclos_total - ciclos_completados
                ciclos_batch = min(ciclos_por_batch, ciclos_restantes)
                
                print(f"\nEjecutando batch de {ciclos_batch} ciclos ({ciclos_completados}/{num_ciclos_total})...")
                
                # Monitorear antes del batch
                self.monitorear_recursos()
                
                # Ejecutar ciclos
                tiempo_inicio_batch = time.time()
                resultado = self.sistema.ciclo_vital(
                    num_ciclos=ciclos_batch,
                    visualizar_cada=visualizar_cada if visualizar_cada > 0 else 0
                )
                tiempo_batch = time.time() - tiempo_inicio_batch
                
                # Actualizar contadores
                ciclos_completados += ciclos_batch
                
                # Registrar tiempo promedio por ciclo
                tiempo_promedio = tiempo_batch / max(1, ciclos_batch)
                self.metricas_rendimiento['tiempo_ciclo'].append(tiempo_promedio)
                
                print(f"Batch completado en {tiempo_batch:.2f}s ({tiempo_promedio:.4f}s por ciclo)")
                
                # Actualizar contadores en stats
                conceptos_antes = stats_totales.get('conceptos_generados', 0)
                stats_totales['conceptos_generados'] = self.sistema.metricas['conceptos_creados']
                conceptos_nuevos = stats_totales['conceptos_generados'] - conceptos_antes
                
                # Monitorear recursos después del batch
                metrics = self.monitorear_recursos()
                stats_totales['memoria_max'] = max(stats_totales.get('memoria_max', 0), 
                                                  metrics['memoria_usada'])
                
                print(f"Memoria: {metrics['memoria_usada']:.1f}MB, Conceptos: {metrics['num_conceptos']}")
                
                # Verificar si es momento de optimizar
                if ciclos_completados % optimizar_cada == 0 or ciclos_completados >= num_ciclos_total:
                    print("\n" + "="*50)
                    print(f"Punto de optimización - Ciclo {ciclos_completados}")
                    
                    # Si se están acercando al límite de conceptos, optimizar antes
                    if len(self.sistema.conceptos) > self.MAX_CONCEPTOS * 0.8:
                        print(f"¡Alerta! Acercándose al límite de conceptos: {len(self.sistema.conceptos)}/{self.MAX_CONCEPTOS}")
                    
                    # Optimizar sistema
                    stats_opt = self.optimizar_sistema()
                    stats_totales['num_optimizaciones'] += 1
                    
                    # Guardar estado periódicamente
                    ruta_guardado = os.path.join(
                        self.ruta_temp, 
                        f"estado_ciclo_{ciclos_completados}.json"
                    )
                    self.sistema.guardar(ruta_guardado)
                    print(f"Estado guardado en {ruta_guardado}")
                    
                    # Reincorporar algunos conceptos apartados si hay espacio
                    if len(self.sistema.conceptos) < self.MAX_CONCEPTOS * 0.7:
                        self.reincorporar_conceptos_apartados(num_conceptos=3)
                    
                    print("="*50 + "\n")
        
        except KeyboardInterrupt:
            print("\n\nEjecución interrumpida por el usuario")
        except Exception as e:
            print(f"\n\nError durante la ejecución: {e}")
        finally:
            # Completar estadísticas finales
            tiempo_total = time.time() - tiempo_inicio_total
            stats_totales['tiempo_total'] = tiempo_total
            
            if self.metricas_rendimiento['tiempo_ciclo']:
                stats_totales['tiempo_promedio_ciclo'] = sum(self.metricas_rendimiento['tiempo_ciclo']) / len(self.metricas_rendimiento['tiempo_ciclo'])
                
            # Guardar estado final
            ruta_final = os.path.join(self.ruta_temp, "estado_final.json")
            self.sistema.guardar(ruta_final)
            
            # Guardar métricas
            self.guardar_metricas_rendimiento()
            
            print("\n" + "="*50)
            print(f"Ciclo vital optimizado finalizado: {ciclos_completados}/{num_ciclos_total} ciclos")
            print(f"Tiempo total: {tiempo_total:.2f}s")
            print(f"Tiempo promedio por ciclo: {stats_totales['tiempo_promedio_ciclo']:.4f}s")
            print(f"Conceptos finales: {len(self.sistema.conceptos)}")
            print(f"Conceptos apartados: {len(self.conceptos_apartados)}")
            print(f"Conexiones finales: {self.sistema.grafo.number_of_edges()}")
            print(f"Estado final guardado en: {ruta_final}")
            print("="*50)
            
            return stats_totales
    
    def guardar_metricas_rendimiento(self):
        """
        Guarda las métricas de rendimiento a un archivo JSON
        """
        ruta = os.path.join(self.ruta_temp, "metricas_rendimiento.json")
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(self.metricas_rendimiento, f, indent=2)
    
    def visualizar_metricas_rendimiento(self):
        """
        Visualiza las métricas de rendimiento a lo largo del tiempo
        """
        if not self.metricas_rendimiento['tiempo_ciclo']:
            print("No hay suficientes datos de rendimiento para visualizar")
            return
            
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        
        # Tiempo por ciclo
        axs[0, 0].plot(self.metricas_rendimiento['tiempo_ciclo'])
        axs[0, 0].set_title('Tiempo por ciclo (s)')
        axs[0, 0].set_xlabel('Batch')
        axs[0, 0].set_ylabel('Tiempo (s)')
        axs[0, 0].grid(True)
        
        # Memoria usada
        axs[0, 1].plot(self.metricas_rendimiento['memoria_usada'])
        axs[0, 1].set_title('Memoria utilizada (MB)')
        axs[0, 1].set_xlabel('Batch')
        axs[0, 1].set_ylabel('Memoria (MB)')
        axs[0, 1].grid(True)
        
        # Número de conceptos
        axs[1, 0].plot(self.metricas_rendimiento['num_conceptos'])
        axs[1, 0].set_title('Número de conceptos')
        axs[1, 0].set_xlabel('Batch')
        axs[1, 0].set_ylabel('Conceptos')
        axs[1, 0].grid(True)
        
        # Número de conexiones
        axs[1, 1].plot(self.metricas_rendimiento['num_conexiones'])
        axs[1, 1].set_title('Número de conexiones')
        axs[1, 1].set_xlabel('Batch')
        axs[1, 1].set_ylabel('Conexiones')
        axs[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.ruta_temp, "metricas_rendimiento.png"))
        plt.show()
    

def fusionar_conceptos_similares(self, umbral_similitud=0.8):
    """
    Fusiona conceptos muy similares para reducir redundancia
    
    Args:
        umbral_similitud: Umbral de similitud para considerar fusión
        
    Returns:
        Número de conceptos fusionados
    """
    if len(self.sistema.conceptos) < 2:
        return 0
    
    print("Buscando conceptos similares para fusionar...")
    
    # Preparar vectores y nombres
    vectores = {}
    for nombre, datos in self.sistema.conceptos.items():
        vectores[nombre] = datos['base']
    
    # Buscar pares de conceptos similares
    nombres = list(vectores.keys())
    candidatos_fusion = []
    
    # Comparar cada par (proceso O(n²), puede ser lento con muchos conceptos)
    for i in range(len(nombres)):
        for j in range(i+1, len(nombres)):
            v1 = vectores[nombres[i]]
            v2 = vectores[nombres[j]]
            
            # Calcular similitud coseno
            similitud = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            
            if similitud > umbral_similitud:
                # Guardar esta pareja y su similitud
                candidatos_fusion.append((nombres[i], nombres[j], similitud))
    
    # Ordenar candidatos por similitud (descendente)
    candidatos_fusion.sort(key=lambda x: x[2], reverse=True)
    
    # Realizar fusiones
    fusionados = 0
    conceptos_procesados = set()
    
    for c1, c2, sim in candidatos_fusion:
        # Si alguno ya ha sido procesado, saltamos
        if c1 in conceptos_procesados or c2 in conceptos_procesados:
            continue
        
        # Determinar cuál mantener y cuál eliminar
        # Preferimos mantener el que tiene más activaciones
        if self.sistema.conceptos[c1]['activaciones'] >= self.sistema.conceptos[c2]['activaciones']:
            mantener, eliminar = c1, c2
        else:
            mantener, eliminar = c2, c1
        
        print(f"Fusionando conceptos similares: '{eliminar}' -> '{mantener}' (similitud: {sim:.2f})")
        
        # Actualizar vector del concepto que mantenemos (promedio ponderado)
        act1 = self.sistema.conceptos[mantener]['activaciones'] + 1
        act2 = self.sistema.conceptos[eliminar]['activaciones'] + 1
        peso_total = act1 + act2
        
        # Nuevo vector base (promedio ponderado por activaciones)
        nuevo_vector = (self.sistema.conceptos[mantener]['base'] * act1 + 
                       self.sistema.conceptos[eliminar]['base'] * act2) / peso_total
        
        # Normalizar el nuevo vector
        nuevo_vector = nuevo_vector / np.linalg.norm(nuevo_vector)
        
        # Actualizar el concepto que mantenemos
        self.sistema.conceptos[mantener]['base'] = nuevo_vector
        self.sistema.conceptos[mantener]['actual'] = nuevo_vector + np.random.normal(0, 0.1, nuevo_vector.shape)
        self.sistema.conceptos[mantener]['activaciones'] += self.sistema.conceptos[eliminar]['activaciones']
        
        # Transferir conexiones del concepto eliminado al mantenido
        if eliminar in self.sistema.relaciones:
            for dest, peso in self.sistema.relaciones[eliminar]:
                # Si la conexión ya existe, quedarnos con el peso mayor
                existe = False
                for idx, (d, p) in enumerate(self.sistema.relaciones.get(mantener, [])):
                    if d == dest:
                        existe = True
                        # Actualizar peso si el nuevo es mayor
                        if peso > p:
                            self.sistema.relaciones[mantener][idx] = (d, peso)
                            # Actualizar grafo si existe
                            if self.sistema.grafo.has_edge(mantener, dest):
                                self.sistema.grafo[mantener][dest]['weight'] = peso
                        break
                
                # Si no existe, añadir la conexión
                if not existe and dest != mantener:
                    if mantener not in self.sistema.relaciones:
                        self.sistema.relaciones[mantener] = []
                    self.sistema.relaciones[mantener].append((dest, peso))
                    # Añadir al grafo
                    self.sistema.grafo.add_edge(mantener, dest, weight=peso)
            
            # También debemos actualizar las conexiones entrantes
            for origen in self.sistema.relaciones:
                for idx, (dest, peso) in enumerate(self.sistema.relaciones[origen]):
                    if dest == eliminar:
                        # Reemplazar por el concepto mantenido
                        self.sistema.relaciones[origen][idx] = (mantener, peso)
                        # Actualizar grafo
                        if self.sistema.grafo.has_edge(origen, eliminar):
                            # Eliminar arista antigua
                            self.sistema.grafo.remove_edge(origen, eliminar)
                            # Añadir nueva si no existe
                            if not self.sistema.grafo.has_edge(origen, mantener):
                                self.sistema.grafo.add_edge(origen, mantener, weight=peso)
                            # Si ya existe, mantener el peso mayor
                            elif self.sistema.grafo[origen][mantener]['weight'] < peso:
                                self.sistema.grafo[origen][mantener]['weight'] = peso
        
        # Eliminar el concepto redundante
        if eliminar in self.sistema.conceptos:
            del self.sistema.conceptos[eliminar]
        if eliminar in self.sistema.relaciones:
            del self.sistema.relaciones[eliminar]
        if eliminar in self.sistema.grafo:
            self.sistema.grafo.remove_node(eliminar)
        
        # Marcar como procesados
        conceptos_procesados.add(mantener)
        conceptos_procesados.add(eliminar)
        
        fusionados += 1
    
    print(f"Se fusionaron {fusionados} pares de conceptos")
    return fusionados

def buscar_patrones_emergentes(self):
    """
    Busca patrones emergentes en la red de conceptos, como comunidades,
    hubs, ciclos y otras estructuras interesantes
    
    Returns:
        Dict con patrones identificados
    """
    if len(self.sistema.conceptos) < 10:
        print("Se necesitan más conceptos para buscar patrones emergentes")
        return {}
    
    print("Buscando patrones emergentes en la red conceptual...")
    
    import networkx as nx
    from networkx.algorithms import community
    
    # Usar solo conexiones con peso significativo para análisis de patrones
    G = nx.Graph()
    
    # Añadir nodos al grafo
    for concepto in self.sistema.conceptos:
        # Podemos incluir atributos como la edad o activaciones
        G.add_node(concepto, 
                  edad=self.sistema.metricas['edad'] - self.sistema.conceptos[concepto]['creado'],
                  activaciones=self.sistema.conceptos[concepto]['activaciones'])
    
    # Añadir aristas con peso > umbral
    umbral_conexion = 0.1
    for origen, destinos in self.sistema.relaciones.items():
        for destino, peso in destinos:
            if peso > umbral_conexion:
                G.add_edge(origen, destino, weight=peso)
    
    resultados = {}
    
    # 1. Detectar comunidades (agrupaciones de conceptos fuertemente conectados)
    print("Detectando comunidades...")
    try:
        # Usar algoritmo de Louvain para detección de comunidades
        comunidades = community.louvain_communities(G, weight='weight')
        resultados['comunidades'] = [list(com) for com in comunidades]
        
        print(f"Se detectaron {len(comunidades)} comunidades")
        for i, com in enumerate(comunidades):
            if i < 3:  # Mostrar solo las primeras 3
                print(f"  Comunidad {i+1}: {len(com)} conceptos")
                # Mostrar algunos miembros
                algunos = list(com)[:5]
                print(f"    Ejemplos: {', '.join(algunos)}")
    except Exception as e:
        print(f"Error al detectar comunidades: {e}")
        resultados['comunidades'] = []
    
    # 2. Identificar nodos centrales (hubs)
    print("Identificando nodos centrales...")
    try:
        # Calcular centralidad de grado ponderado
        centralidad = {}
        for nodo in G.nodes():
            # Suma de los pesos de todas las conexiones
            cent = sum(G[nodo][vecino]['weight'] for vecino in G[nodo])
            centralidad[nodo] = cent
        
        # Ordenar por centralidad
        nodos_centrales = sorted(centralidad.items(), key=lambda x: x[1], reverse=True)
        resultados['nodos_centrales'] = nodos_centrales[:10]  # Top 10
        
        print("Nodos más centrales (conceptos hub):")
        for nodo, cent in nodos_centrales[:5]:
            print(f"  {nodo}: {cent:.2f}")
    except Exception as e:
        print(f"Error al identificar nodos centrales: {e}")
        resultados['nodos_centrales'] = []
    
    # 3. Buscar ciclos interesantes
    print("Buscando ciclos conceptuales...")
    try:
        # Buscar ciclos simples de tamaño 3-5
        ciclos = []
        for tam in range(3, 6):
            try:
                for c in nx.simple_cycles(nx.DiGraph(G)):
                    if len(c) == tam:
                        ciclos.append(c)
                        if len(ciclos) >= 20:  # Limitar a 20 ciclos
                            break
            except:
                continue
        
        resultados['ciclos'] = ciclos[:10]  # Hasta 10 ciclos
        
        print(f"Se encontraron {len(ciclos)} ciclos conceptuales")
        for i, ciclo in enumerate(ciclos[:3]):
            print(f"  Ciclo {i+1}: {' -> '.join(ciclo)}")
    except Exception as e:
        print(f"Error al buscar ciclos: {e}")
        resultados['ciclos'] = []
    
    # 4. Calcular métricas globales de la red
    print("Calculando métricas globales de la red...")
    try:
        # Componentes conexas
        componentes = list(nx.connected_components(G))
        tam_componente_principal = len(max(componentes, key=len))
        
        # Diámetro de la componente principal (mayor distancia entre nodos)
        componente_principal = max(componentes, key=len)
        subgrafo_principal = G.subgraph(componente_principal)
        diametro = nx.diameter(subgrafo_principal)
        
        # Densidad de la red (proporción de conexiones existentes respecto a posibles)
        densidad = nx.density(G)
        
        # Coeficiente de clustering (tendencia a formar grupos)
        clustering = nx.average_clustering(G, weight='weight')
        
        resultados['metricas_red'] = {
            'num_componentes': len(componentes),
            'tam_componente_principal': tam_componente_principal,
            'diametro': diametro,
            'densidad': densidad,
            'clustering': clustering
        }
        
        print(f"Componentes conexas: {len(componentes)}")
        print(f"Tamaño de componente principal: {tam_componente_principal} conceptos")
        print(f"Diámetro de la red: {diametro}")
        print(f"Densidad: {densidad:.4f}")
        print(f"Coeficiente de clustering: {clustering:.4f}")
    except Exception as e:
        print(f"Error al calcular métricas globales: {e}")
        resultados['metricas_red'] = {}
    
    # Visualizar la red con las comunidades detectadas
    if 'comunidades' in resultados and resultados['comunidades']:
        plt.figure(figsize=(12, 10))
        
        # Crear mapa de comunidades a colores
        colores = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        color_nodo = {}
        
        for i, comunidad in enumerate(resultados['comunidades']):
            color_idx = i % len(colores)
            for nodo in comunidad:
                color_nodo[nodo] = colores[color_idx]
        
        # Posicionar nodos
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Dibujar nodos
        for i, comunidad in enumerate(resultados['comunidades']):
            if i < 10:  # Limitar a 10 comunidades para la visualización
                nx.draw_networkx_nodes(
                    G, pos, 
                    nodelist=list(comunidad),
                    node_color=colores[i % len(colores)],
                    node_size=200,
                    alpha=0.8,
                    label=f"Comunidad {i+1}"
                )
        
        # Dibujar aristas
        nx.draw_networkx_edges(
            G, pos, 
            width=[G[u][v]['weight'] * 3 for u, v in G.edges()],
            alpha=0.4
        )
        
        # Dibujar etiquetas
        if len(G.nodes()) < 30:  # Si hay pocos nodos, mostrar todas las etiquetas
            nx.draw_networkx_labels(G, pos, font_size=10)
        else:
            # Si hay muchos, mostrar solo para nodos centrales
            etiquetas = {nodo: nodo for nodo, _ in resultados['nodos_centrales'][:10]}
            nx.draw_networkx_labels(G, pos, labels=etiquetas, font_size=12, font_weight='bold')
        
        plt.title("Patrones emergentes en la red conceptual")
        plt.legend(scatterpoints=1)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(self.ruta_temp, "patrones_emergentes.png"))
        plt.show()
    
    return resultados

def generar_informe_sistema(self):
    """
    Genera un informe completo del estado actual del sistema
    
    Returns:
        Dict con estadísticas del sistema
    """
    print("Generando informe completo del sistema IANAE...")
    
    # Estadísticas básicas
    stats = {
        'num_conceptos': len(self.sistema.conceptos),
        'num_conexiones': self.sistema.grafo.number_of_edges(),
        'edad_sistema': self.sistema.metricas['edad'],
        'conceptos_creados_total': self.sistema.metricas['conceptos_creados'],
        'ciclos_pensamiento': self.sistema.metricas['ciclos_pensamiento'],
        'auto_modificaciones': self.sistema.metricas['auto_modificaciones'],
        'conceptos_apartados': len(self.conceptos_apartados)
    }
    
    # Calcular estadísticas de activación
    activaciones = [datos['activaciones'] for _, datos in self.sistema.conceptos.items()]
    if activaciones:
        stats['activaciones_promedio'] = sum(activaciones) / len(activaciones)
        stats['activaciones_max'] = max(activaciones)
        stats['activaciones_min'] = min(activaciones)
    
    # Estadísticas de conexiones
    pesos_conexiones = []
    for origen, destinos in self.sistema.relaciones.items():
        for _, peso in destinos:
            pesos_conexiones.append(peso)
            
    if pesos_conexiones:
        stats['peso_conexion_promedio'] = sum(pesos_conexiones) / len(pesos_conexiones)
        stats['peso_conexion_max'] = max(pesos_conexiones)
        stats['peso_conexion_min'] = min(pesos_conexiones)
    
    # Conceptos más activos
    conceptos_por_activacion = sorted(
        [(nombre, datos['activaciones']) for nombre, datos in self.sistema.conceptos.items()],
        key=lambda x: x[1],
        reverse=True
    )
    stats['conceptos_mas_activos'] = conceptos_por_activacion[:10]
    
    # Conceptos con más conexiones
    conceptos_por_conexiones = sorted(
        [(concepto, len(self.sistema.relaciones.get(concepto, []))) 
         for concepto in self.sistema.conceptos],
        key=lambda x: x[1],
        reverse=True
    )
    stats['conceptos_mas_conectados'] = conceptos_por_conexiones[:10]
    
    # Imprimir resumen
    print("\n===== INFORME DEL SISTEMA IANAE =====")
    print(f"Edad del sistema: {stats['edad_sistema']} ciclos")
    print(f"Conceptos actuales: {stats['num_conceptos']} (de {stats['conceptos_creados_total']} creados en total)")
    print(f"Conceptos apartados: {stats['conceptos_apartados']}")
    print(f"Conexiones: {stats['num_conexiones']}")
    print(f"Ciclos de pensamiento: {stats['ciclos_pensamiento']}")
    print(f"Auto-modificaciones: {stats['auto_modificaciones']}")
    
    if activaciones:
        print(f"\nActivaciones promedio: {stats['activaciones_promedio']:.2f}")
        print(f"Rango de activaciones: {stats['activaciones_min']} - {stats['activaciones_max']}")
    
    if pesos_conexiones:
        print(f"\nPeso promedio de conexiones: {stats['peso_conexion_promedio']:.2f}")
        print(f"Rango de pesos: {stats['peso_conexion_min']:.2f} - {stats['peso_conexion_max']:.2f}")
    
    print("\nConceptos más activos:")
    for nombre, acts in stats['conceptos_mas_activos'][:5]:
        print(f"  {nombre}: {acts} activaciones")
    
    print("\nConceptos más conectados:")
    for nombre, conx in stats['conceptos_mas_conectados'][:5]:
        print(f"  {nombre}: {conx} conexiones")
    
    print("\n====================================")
    
    # Guardar informe
    ruta_informe = os.path.join(self.ruta_temp, "informe_sistema.json")
    with open(ruta_informe, 'w', encoding='utf-8') as f:
        # Convertir elementos no serializables
        informe_json = {}
        for k, v in stats.items():
            if isinstance(v, (list, dict, str, int, float, bool)) or v is None:
                informe_json[k] = v
            else:
                # Convertir a formato serializable
                informe_json[k] = str(v)
        
        json.dump(informe_json, f, indent=2)
    
    print(f"Informe guardado en {ruta_informe}")
    
    return stats
