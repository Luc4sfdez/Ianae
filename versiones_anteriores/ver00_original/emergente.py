"""
Módulo de Pensamiento Emergente - IANAE v3.0

Implementa un sistema de generación de pensamiento asociativo basado en:
- Redes semánticas difusas
- Propagación de activación
- Generación de rutas conceptuales

Ejemplo básico:
>>> pe = PensamientoEmergente()
>>> pe.cargar_conceptos_desde_texto("Texto de ejemplo...")
>>> print(pe.generar_pensamiento())
"""

import numpy as np
import matplotlib.pyplot as plt
from nucleo import ConceptosDifusos
import random
import time
from typing import Dict, List, Tuple, Optional, Union

class PensamientoEmergente:
    """
    Sistema de pensamiento emergente basado en activación conceptual.
    
    Atributos:
        sistema (ConceptosDifusos): Núcleo de conceptos y relaciones
        historial_pensamientos (List[Dict]): Registro de pensamientos generados
    """
    """
    Clase que implementa experimentos de pensamiento emergente usando
    el núcleo de conceptos difusos
    """
    
    def __init__(self, sistema: Optional[ConceptosDifusos] = None, dim_vector: int = 20) -> None:
        """
        Inicializa el sistema de pensamiento emergente
        
        Args:
            sistema: Instancia existente de ConceptosDifusos (opcional)
            dim_vector: Dimensionalidad para un nuevo sistema
            
        Ejemplo:
            >>> from nucleo import ConceptosDifusos
            >>> cd = ConceptosDifusos()
            >>> pe = PensamientoEmergente(sistema=cd)
        """
        self.sistema = sistema if sistema else ConceptosDifusos(dim_vector=dim_vector)
        self.historial_pensamientos = []
        
    def cargar_conceptos_desde_texto(self, texto: str, max_conceptos: int = 30) -> List[str]:
        """
        Extrae conceptos desde un texto y los añade al sistema
        
        Args:
            texto: Texto de donde extraer conceptos
            max_conceptos: Número máximo de conceptos a extraer
            
        Returns:
            Lista de conceptos extraídos (strings)
            
        Ejemplo:
            >>> pe = PensamientoEmergente()
            >>> conceptos = pe.cargar_conceptos_desde_texto(
            ...     "El aprendizaje automático es una rama de la inteligencia artificial",
            ...     max_conceptos=10
            ... )
            >>> print(conceptos)
            ['aprendizaje', 'automático', 'rama', 'inteligencia', 'artificial']
            
        Raises:
            ValueError: Si max_conceptos es menor que 1
        """
        if max_conceptos < 1:
            raise ValueError("max_conceptos debe ser al menos 1")
        # Preprocesamiento y normalización del texto
        texto = texto.lower().strip()
        for c in ".,;:!?()[]{}\"'":
            texto = texto.replace(c, ' ')
            
        palabras = texto.split()
        
        # Filtrar palabras comunes (simplificado)
        stop_words = {
            "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "a", "ante", "bajo",
            "con", "de", "desde", "en", "entre", "hacia", "hasta", "para", "por", "según", "sin",
            "sobre", "tras", "que", "como", "cuando", "donde", "si", "no", "al", "del", "lo", "su",
            "sus", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "mi", "tu", "su",
            "es", "son", "era", "eran", "sido", "fue", "ha", "han", "he", "hemos"
        }
        
        palabras_filtradas = [p for p in palabras if p not in stop_words and len(p) > 3]
        
        # Contar frecuencias
        frecuencias = {}
        for p in palabras_filtradas:
            frecuencias[p] = frecuencias.get(p, 0) + 1
            
        # Ordenar por frecuencia
        palabras_ordenadas = sorted(frecuencias.items(), key=lambda x: x[1], reverse=True)
        
        # Tomar las más frecuentes hasta max_conceptos
        conceptos_extraidos = [p for p, f in palabras_ordenadas[:max_conceptos]]
        
        # Añadir al sistema
        conceptos_añadidos = []
        for c in conceptos_extraidos:
            if c not in self.sistema.conceptos:
                self.sistema.añadir_concepto(c)
                conceptos_añadidos.append(c)
                
        # Crear relaciones basadas en co-ocurrencia en el texto
        ventana = 5  # Palabras cercanas en el texto
        for i, p1 in enumerate(palabras_filtradas):
            if p1 in self.sistema.conceptos:
                # Buscar palabras cercanas
                inicio = max(0, i - ventana)
                fin = min(len(palabras_filtradas), i + ventana + 1)
                
                for j in range(inicio, fin):
                    if i != j:  # No relacionar consigo misma
                        p2 = palabras_filtradas[j]
                        if p2 in self.sistema.conceptos:
                            # Relacionar con fuerza inversamente proporcional a la distancia
                            distancia = abs(i - j)
                            fuerza = 1.0 / max(1, distancia)
                            
                            # Relacionar conceptos
                            self.sistema.relacionar(p1, p2, fuerza=fuerza)
        
        return conceptos_añadidos
    
    def explorar_asociaciones(
        self, 
        concepto_inicial: str, 
        profundidad: int = 3, 
        anchura: int = 5, 
        temperatura: float = 0.2
    ) -> str:
        """
        Explora asociaciones a partir de un concepto inicial
        
        Args:
            concepto_inicial: Concepto desde donde iniciar (debe existir en el sistema)
            profundidad: Número de pasos de propagación (entre 1 y 10)
            anchura: Número de conceptos a considerar en cada paso (entre 1 y 20)
            temperatura: Factor de aleatoriedad (entre 0.0 y 1.0)
            
        Returns:
            str: Cadena de pensamiento generada con las asociaciones encontradas
            
        Raises:
            ValueError: Si el concepto inicial no existe en el sistema
            TypeError: Si los parámetros no son del tipo esperado
            
        Ejemplo:
            >>> pe = PensamientoEmergente()
            >>> pe.cargar_conceptos_desde_texto("red neuronal aprendizaje profundo")
            >>> print(pe.explorar_asociaciones("red", profundidad=2))
        """
        # Validar parámetros
        if not isinstance(concepto_inicial, str):
            raise TypeError("concepto_inicial debe ser un string")
        if not isinstance(profundidad, int) or not 1 <= profundidad <= 10:
            raise ValueError("profundidad debe ser un entero entre 1 y 10")
        if not isinstance(anchura, int) or not 1 <= anchura <= 20:
            raise ValueError("anchura debe ser un entero entre 1 y 20")
        if not isinstance(temperatura, (float, int)) or not 0.0 <= temperatura <= 1.0:
            raise ValueError("temperatura debe ser un float entre 0.0 y 1.0")
        if concepto_inicial not in self.sistema.conceptos:
            return f"El concepto '{concepto_inicial}' no existe en el sistema"
            
        # Resultado de la propagación de activación
        resultado = self.sistema.activar(
            concepto_inicial, 
            pasos=profundidad,
            temperatura=temperatura
        )
        
        # Construir cadena de pensamiento
        cadena = [f"Explorando a partir de '{concepto_inicial}':\n"]
        
        for paso, activaciones in enumerate(resultado):
            # Ordenar conceptos por nivel de activación
            conceptos_activos = sorted(
                [(c, a) for c, a in activaciones.items() if a > 0.05],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Tomar los más activos según anchura
            conceptos_paso = conceptos_activos[:anchura]
            
            # Añadir a la cadena
            if paso == 0:
                cadena.append("Punto de partida:")
            else:
                cadena.append(f"\nPaso {paso}:")
                
            for c, a in conceptos_paso:
                # Formato: concepto (activación)
                cadena.append(f"  {c} ({a:.2f})")
                
        # Registrar este pensamiento
        pensamiento = {
            'inicio': concepto_inicial,
            'cadena': "\n".join(cadena),
            'activaciones_finales': resultado[-1] if resultado else {},
            'timestamp': time.time()
        }
        self.historial_pensamientos.append(pensamiento)
        
        return "\n".join(cadena)
    
    def generar_pensamiento(
        self, 
        semilla: Optional[str] = None, 
        longitud: int = 5, 
        temperatura: float = 0.3
    ) -> str:
        """
        Genera una cadena de pensamiento a partir de activaciones sucesivas
        
        Args:
            semilla: Concepto inicial (opcional, si no se provee se elige aleatoriamente)
            longitud: Número de conceptos a incluir (entre 1 y 20)
            temperatura: Factor de aleatoriedad (entre 0.0 y 1.0)
            
        Returns:
            str: Texto del pensamiento generado o mensaje de error
            
        Raises:
            ValueError: Si los parámetros están fuera de rango
            TypeError: Si los tipos de parámetros son incorrectos
            
        Ejemplo:
            >>> pe = PensamientoEmergente()
            >>> pe.cargar_conceptos_desde_texto("red neuronal aprendizaje profundo")
            >>> print(pe.generar_pensamiento("red", longitud=3))
        """
        # Validar parámetros
        if semilla is not None and not isinstance(semilla, str):
            raise TypeError("semilla debe ser un string o None")
        if not isinstance(longitud, int) or not 1 <= longitud <= 20:
            raise ValueError("longitud debe ser un entero entre 1 y 20")
        if not isinstance(temperatura, (float, int)) or not 0.0 <= temperatura <= 1.0:
            raise ValueError("temperatura debe ser un float entre 0.0 y 1.0")
        if not self.sistema.conceptos:
            return "No hay conceptos en el sistema para generar pensamiento"
            
        # Seleccionar concepto inicial si no se proporciona
        if not semilla or semilla not in self.sistema.conceptos:
            # Elegir con probabilidad ponderada por activaciones previas
            conceptos = list(self.sistema.conceptos.keys())
            pesos = [self.sistema.conceptos[c]['activaciones'] + 1 for c in conceptos]
            total = sum(pesos)
            probabilidades = [p/total for p in pesos]
            
            semilla = np.random.choice(conceptos, p=probabilidades)
            
        # Propagar activación
        cadena_conceptos = [semilla]
        concepto_actual = semilla
        
        for _ in range(longitud - 1):
            # Activar el concepto actual
            resultado = self.sistema.activar(
                concepto_actual, 
                pasos=2,  # Pocos pasos para mantener coherencia
                temperatura=temperatura
            )
            
            if not resultado:
                break
                
            # Obtener conceptos activados
            activaciones = resultado[-1]
            
            # Filtrar el concepto actual y los ya incluidos
            candidatos = [(c, a) for c, a in activaciones.items() 
                         if c != concepto_actual and c not in cadena_conceptos and a > 0.1]
            
            if not candidatos:
                break
                
            # Ordenar por activación
            candidatos.sort(key=lambda x: x[1], reverse=True)
            
            # Elegir siguiente concepto (con algo de aleatoriedad)
            if random.random() < 0.7:  # 70% de probabilidad de elegir el más activado
                siguiente = candidatos[0][0]
            else:
                # Elegir entre los 3 primeros con probabilidad proporcional a activación
                candidatos = candidatos[:min(3, len(candidatos))]
                pesos = [a for _, a in candidatos]
                total = sum(pesos)
                probs = [p/total for p in pesos]
                idx = np.random.choice(range(len(candidatos)), p=probs)
                siguiente = candidatos[idx][0]
                
            # Añadir a la cadena
            cadena_conceptos.append(siguiente)
            concepto_actual = siguiente
            
        # Construir texto del pensamiento
        texto = f"Pensamiento: {' → '.join(cadena_conceptos)}"
        
        # Registrar este pensamiento
        pensamiento = {
            'inicio': semilla,
            'conceptos': cadena_conceptos,
            'texto': texto,
            'timestamp': time.time()
        }
        self.historial_pensamientos.append(pensamiento)
        
        return texto
    
    def asociar_conceptos(
        self, 
        concepto1: str, 
        concepto2: str, 
        profundidad: int = 3
    ) -> str:
        """
        Busca asociaciones entre dos conceptos mediante propagación de activación
        
        Args:
            concepto1: Primer concepto (debe existir en el sistema)
            concepto2: Segundo concepto (debe existir en el sistema)
            profundidad: Profundidad de exploración (entre 1 y 10)
            
        Returns:
            str: Texto con las asociaciones encontradas o mensaje de error
            
        Raises:
            TypeError: Si los conceptos no son strings
            ValueError: Si la profundidad está fuera de rango
            
        Ejemplo:
            >>> pe = PensamientoEmergente()
            >>> pe.cargar_conceptos_desde_texto("red neuronal aprendizaje profundo")
            >>> print(pe.asociar_conceptos("red", "aprendizaje"))
        """
        # Validar parámetros
        if not isinstance(concepto1, str) or not isinstance(concepto2, str):
            raise TypeError("Los conceptos deben ser strings")
        if not isinstance(profundidad, int) or not 1 <= profundidad <= 10:
            raise ValueError("profundidad debe ser un entero entre 1 y 10")
        if concepto1 not in self.sistema.conceptos or concepto2 not in self.sistema.conceptos:
            conceptos_faltantes = []
            if concepto1 not in self.sistema.conceptos:
                conceptos_faltantes.append(concepto1)
            if concepto2 not in self.sistema.conceptos:
                conceptos_faltantes.append(concepto2)
                
            return f"Los siguientes conceptos no existen: {', '.join(conceptos_faltantes)}"
            
        # Activar ambos conceptos
        activacion1 = self.sistema.activar(concepto1, pasos=profundidad)[-1]
        activacion2 = self.sistema.activar(concepto2, pasos=profundidad)[-1]
        
        # Encontrar conceptos puente (activados por ambos)
        puentes = []
        for concepto in self.sistema.conceptos:
            if concepto != concepto1 and concepto != concepto2:
                act1 = activacion1.get(concepto, 0)
                act2 = activacion2.get(concepto, 0)
                
                # Si está significativamente activado por ambos
                if act1 > 0.1 and act2 > 0.1:
                    puentes.append((concepto, act1 * act2))  # Producto como medida de conexión
                    
        # Ordenar por fuerza de conexión
        puentes.sort(key=lambda x: x[1], reverse=True)
        
        # Construir texto de respuesta
        if puentes:
            texto = [f"Asociaciones entre '{concepto1}' y '{concepto2}':"]
            
            for concepto, fuerza in puentes[:5]:  # Top 5
                texto.append(f"  • {concepto} (fuerza: {fuerza:.2f})")
                
            # Si hay una conexión directa
            if self.sistema.grafo.has_edge(concepto1, concepto2):
                peso = self.sistema.grafo[concepto1][concepto2]['weight']
                texto.append(f"\nExiste una conexión directa con fuerza {peso:.2f}")
            else:
                texto.append("\nNo existe una conexión directa entre estos conceptos")
                
            return "\n".join(texto)
        else:
            return f"No se encontraron asociaciones significativas entre '{concepto1}' y '{concepto2}'"
    
    def visualizar_pensamiento(self, indice=-1):
        """
        Visualiza un pensamiento del historial
        
        Args:
            indice: Índice del pensamiento (-1 para el último)
        """
        if not self.historial_pensamientos:
            print("No hay pensamientos en el historial")
            return
            
        if indice < 0:
            indice = len(self.historial_pensamientos) + indice
            
        if indice < 0 or indice >= len(self.historial_pensamientos):
            print(f"Índice fuera de rango. Hay {len(self.historial_pensamientos)} pensamientos")
            return
            
        pensamiento = self.historial_pensamientos[indice]
        
        # Mostrar información
        print(f"Pensamiento #{indice + 1}:")
        print("-" * 40)
        
        if 'texto' in pensamiento:
            print(pensamiento['texto'])
        elif 'cadena' in pensamiento:
            print(pensamiento['cadena'])
            
        print("-" * 40)
        
        # Visualizar red conceptual con activaciones si están disponibles
        if 'activaciones_finales' in pensamiento and pensamiento['activaciones_finales']:
            self.sistema.visualizar(
                activaciones=pensamiento['activaciones_finales'],
                titulo=f"Pensamiento iniciado en '{pensamiento['inicio']}'"
            )
        elif 'conceptos' in pensamiento:
            # Crear activaciones ficticias para visualizar
            activaciones = {}
            for i, c in enumerate(pensamiento['conceptos']):
                # Decreciente desde el inicio
                activaciones[c] = 1.0 - (i * 0.8 / len(pensamiento['conceptos']))
                
            self.sistema.visualizar(
                activaciones=activaciones,
                titulo=f"Secuencia de conceptos: {' → '.join(pensamiento['conceptos'])}"
            )
    
    def experimento_divergencia(self, concepto, num_rutas=5, longitud=4):
        """
        Genera múltiples rutas de pensamiento a partir del mismo concepto
        para explorar la divergencia creativa
        
        Args:
            concepto: Concepto inicial
            num_rutas: Número de rutas diferentes a generar
            longitud: Longitud de cada ruta
            
        Returns:
            Texto con los resultados
        """
        if concepto not in self.sistema.conceptos:
            return f"El concepto '{concepto}' no existe en el sistema"
            
        rutas = []
        
        for i in range(num_rutas):
            # Variar temperatura para cada ruta
            temperatura = 0.2 + (i * 0.1)  # Incrementar para más divergencia
            
            # Generar pensamiento
            pensamiento = self.generar_pensamiento(
                semilla=concepto,
                longitud=longitud,
                temperatura=temperatura
            )
            
            # Extraer solo la cadena de conceptos
            if "Pensamiento: " in pensamiento:
                cadena = pensamiento.replace("Pensamiento: ", "")
                rutas.append(cadena)
                
        # Construir texto de resultados
        texto = [f"Rutas divergentes desde '{concepto}':"]
        
        for i, ruta in enumerate(rutas):
            texto.append(f"\nRuta {i+1}: {ruta}")
            
        # Visualización opcional
        plt.figure(figsize=(12, 8))
        
        # Crear grafo para visualizar todas las rutas
        import networkx as nx
        G = nx.DiGraph()
        
        # Añadir nodos y aristas para cada ruta
        for i, ruta in enumerate(rutas):
            conceptos = ruta.split(" → ")
            
            # Añadir nodos
            for c in conceptos:
                if not G.has_node(c):
                    G.add_node(c)
                    
            # Añadir aristas direccionales
            for j in range(len(conceptos) - 1):
                origen = conceptos[j]
                destino = conceptos[j+1]
                
                # Crear aristas con atributos para diferenciar rutas
                if G.has_edge(origen, destino):
                    # Si ya existe, actualizar atributos
                    G[origen][destino]['rutas'].append(i+1)
                    G[origen][destino]['weight'] += 1
                else:
                    # Crear nueva arista
                    G.add_edge(origen, destino, rutas=[i+1], weight=1)
        
        # Posicionar nodos
        pos = nx.spring_layout(G, k=0.3, iterations=50)
        
        # Dibujar nodos
        nx.draw_networkx_nodes(
            G, pos,
            node_color='skyblue',
            node_size=500,
            alpha=0.8
        )
        
        # Colores para las diferentes rutas
        colores = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        
        # Dibujar aristas coloreadas por ruta
        for ruta_idx in range(1, num_rutas + 1):
            aristas_ruta = [(u, v) for u, v, d in G.edges(data=True) if ruta_idx in d['rutas']]
            if aristas_ruta:
                nx.draw_networkx_edges(
                    G, pos,
                    edgelist=aristas_ruta,
                    width=2,
                    alpha=0.7,
                    edge_color=colores[(ruta_idx-1) % len(colores)],
                    arrows=True,
                    arrowstyle='-|>',
                    arrowsize=15
                )
        
        # Etiquetas
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        plt.title(f"Rutas divergentes desde '{concepto}'")
        plt.axis('off')
        plt.tight_layout()
        plt.show()
        
        return "\n".join(texto)
    
    def importar_texto(self, archivo):
        """
        Importa conceptos desde un archivo de texto
        
        Args:
            archivo: Ruta al archivo
            
        Returns:
            Número de conceptos importados
        """
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                texto = f.read()
                
            conceptos = self.cargar_conceptos_desde_texto(texto)
            return len(conceptos)
        except Exception as e:
            return f"Error al importar: {e}"
