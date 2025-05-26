"""
Funciones complementarias para el optimizador IANAE
"""
import os
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

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
        # Usar algoritmo de detección de comunidades más simple
        from networkx.algorithms import community
        
        # Intentar con el algoritmo Louvain si está disponible
        try:
            comunidades = community.louvain_communities(G, weight='weight')
        except:
            # Alternativa si el método anterior no está disponible
            comunidades = community.greedy_modularity_communities(G, weight='weight')
            
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
    
    # 3. Calcular métricas globales de la red
    print("Calculando métricas globales de la red...")
    try:
        # Componentes conexas
        componentes = list(nx.connected_components(G))
        tam_componente_principal = len(max(componentes, key=len))
        
        # Si hay componentes conexas
        if componentes:
            # Componente principal
            componente_principal = max(componentes, key=len)
            subgrafo_principal = G.subgraph(componente_principal)
            
            # Diámetro (si el grafo está conectado)
            try:
                diametro = nx.diameter(subgrafo_principal)
            except:
                diametro = -1  # No conectado o infinito
            
            # Densidad de la red
            densidad = nx.density(G)
            
            # Coeficiente de clustering
            try:
                clustering = nx.average_clustering(G, weight='weight')
            except:
                clustering = 0
            
            resultados['metricas_red'] = {
                'num_componentes': len(componentes),
                'tam_componente_principal': tam_componente_principal,
                'diametro': diametro,
                'densidad': densidad,
                'clustering': clustering
            }
            
            print(f"Componentes conexas: {len(componentes)}")
            print(f"Tamaño de componente principal: {tam_componente_principal} conceptos")
            if diametro > 0:
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
            etiquetas = {nodo: nodo for nodo, _ in resultados.get('nodos_centrales', [])[:10]}
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
    
    # Guardar informe en un archivo si hay ruta definida
    try:
        import os
        if hasattr(self, 'ruta_temp') and self.ruta_temp:
            ruta_informe = os.path.join(self.ruta_temp, "informe_sistema.json")
            import json
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
    except Exception as e:
        print(f"Nota: No se pudo guardar el informe: {e}")
    
    return stats
