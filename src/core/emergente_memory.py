# emergente_lucas_real_memory.py - INTEGRADO CON MEMORIA REAL
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import random
import time
import networkx as nx

class PensamientoLucasReal:
    """
    Sistema de pensamiento emergente usando la MEMORIA REAL de Lucas
    Integrado con la base de datos de 4,545 conceptos reales
    """
    
    def __init__(self, memory_db_path="C:/IANAE/IANAE_MEMORY/ianae_index.db"):
        """
        Inicializa conectado a la memoria real de Lucas
        """
        self.db_path = memory_db_path
        self.grafo = nx.Graph()
        self.conceptos_reales = {}
        self.estadisticas_reales = {}
        self.historial_pensamientos = []
        
        print(f"🧠 Inicializando pensamiento emergente con memoria REAL...")
        print(f"📍 Base de datos: {memory_db_path}")
        
        # Cargar conceptos y relaciones reales
        self._cargar_memoria_real()
        
        # Construir grafo con datos reales
        self._construir_grafo_real()
        
        # Patrones específicos de Lucas (ahora basados en datos reales)
        self.patrones_lucas_reales = self._detectar_patrones_reales()
        
        print(f"✅ Sistema listo: {len(self.conceptos_reales)} conceptos reales cargados")
    
    def _cargar_memoria_real(self):
        """
        Carga conceptos y estadísticas desde la base de datos real
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cargar conceptos reales
            cursor.execute('''
                SELECT name, usage_count, category, strength, file_path
                FROM concepts
                ORDER BY usage_count DESC
            ''')
            
            for row in cursor.fetchall():
                name, usage_count, category, strength, file_path = row
                
                self.conceptos_reales[name] = {
                    'name': name,
                    'frequency': usage_count,
                    'category': category,
                    'strength': strength,
                    'files': file_path.split(',') if file_path else [],
                    'activaciones': usage_count / 100.0  # Normalizar para compatibilidad
                }
            
            # Estadísticas generales
            cursor.execute('SELECT COUNT(*) FROM concepts')
            total_concepts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM relationships')
            total_relations = cursor.fetchone()[0]
            
            self.estadisticas_reales = {
                'total_conceptos': total_concepts,
                'total_relaciones': total_relations,
                'conceptos_tecnicos': len([c for c in self.conceptos_reales.values() 
                                         if c['category'].startswith('tech')]),
                'proyectos_detectados': len([c for c in self.conceptos_reales.values() 
                                           if c['category'] == 'projects'])
            }
            
            conn.close()
            
            print(f"📊 Memoria real cargada:")
            print(f"   • {self.estadisticas_reales['total_conceptos']} conceptos")
            print(f"   • {self.estadisticas_reales['total_relaciones']} relaciones")
            print(f"   • {self.estadisticas_reales['conceptos_tecnicos']} conceptos técnicos")
            
        except Exception as e:
            print(f"❌ Error cargando memoria real: {e}")
            self.conceptos_reales = {}
    
    def _construir_grafo_real(self):
        """
        Construye el grafo usando las relaciones reales de la base de datos
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Agregar nodos (conceptos)
            for concepto, data in self.conceptos_reales.items():
                self.grafo.add_node(concepto, **data)
            
            # Agregar aristas (relaciones reales)
            cursor.execute('''
                SELECT concept_a, concept_b, strength
                FROM relationships
                ORDER BY strength DESC
                LIMIT 5000
            ''')
            
            relaciones_agregadas = 0
            for concept_a, concept_b, strength in cursor.fetchall():
                if concept_a in self.conceptos_reales and concept_b in self.conceptos_reales:
                    self.grafo.add_edge(concept_a, concept_b, weight=strength)
                    relaciones_agregadas += 1
            
            conn.close()
            
            print(f"🔗 Grafo construido: {relaciones_agregadas} relaciones activas")
            
        except Exception as e:
            print(f"❌ Error construyendo grafo: {e}")
    
    def _detectar_patrones_reales(self):
        """
        Detecta patrones específicos de Lucas basados en datos reales
        """
        patrones = {}
        
        # Analizar conceptos más frecuentes por categoría
        categorias = defaultdict(list)
        for concepto, data in self.conceptos_reales.items():
            categorias[data['category']].append((concepto, data['frequency']))
        
        # Detectar dominancias reales
        for categoria, conceptos in categorias.items():
            conceptos_ordenados = sorted(conceptos, key=lambda x: x[1], reverse=True)
            
            if len(conceptos_ordenados) > 0:
                top_concepto, top_freq = conceptos_ordenados[0]
                if top_freq > 50:  # Umbral para considerarlo dominante
                    patrones[f'{categoria}_dominante'] = {
                        'concepto': top_concepto,
                        'frecuencia': top_freq,
                        'fuerza': min(1.0, top_freq / 1000.0)
                    }
        
        # Patrones específicos detectados
        patrones_especificos = {
            'vba_excel_expert': 0.0,
            'opencv_master': 0.0,
            'python_developer': 0.0,
            'automation_driven': 0.0,
            'pattern_detector': 0.0
        }
        
        # Calcular basado en frecuencias reales
        for concepto, data in self.conceptos_reales.items():
            freq = data['frequency']
            
            if any(x in concepto.lower() for x in ['ws.', 'cells', 'range', 'application.']):
                patrones_especificos['vba_excel_expert'] += freq
            
            if any(x in concepto.lower() for x in ['cv2', 'opencv', 'imagen', 'contour']):
                patrones_especificos['opencv_master'] += freq
                
            if any(x in concepto.lower() for x in ['python', 'import', 'def', 'self.']):
                patrones_especificos['python_developer'] += freq
                
            if any(x in concepto.lower() for x in ['main.py', 'compose', 'docker']):
                patrones_especificos['automation_driven'] += freq
        
        # Normalizar patrones
        max_valor = max(patrones_especificos.values()) if patrones_especificos.values() else 1
        for key in patrones_especificos:
            patrones_especificos[key] = min(1.0, patrones_especificos[key] / max_valor)
        
        patrones['especificos'] = patrones_especificos
        
        return patrones
    
    def explorar_desde_concepto_real(self, concepto_inicial, profundidad=4, temperatura=0.3):
        """
        Exploración emergente desde un concepto real de la base de datos
        """
        print(f"🚀 Explorando desde concepto real: {concepto_inicial}")
        
        # Verificar que el concepto existe
        if concepto_inicial not in self.conceptos_reales:
            # Buscar conceptos similares
            conceptos_similares = self._buscar_conceptos_similares(concepto_inicial)
            if conceptos_similares:
                print(f"💡 Conceptos similares encontrados: {conceptos_similares[:3]}")
                concepto_inicial = conceptos_similares[0]
                print(f"🎯 Usando: {concepto_inicial}")
            else:
                return f"❌ Concepto '{concepto_inicial}' no encontrado en memoria real"
        
        # Información del concepto inicial
        info_inicial = self.conceptos_reales[concepto_inicial]
        print(f"📊 Concepto inicial: {info_inicial['frequency']}x apariciones, categoría: {info_inicial['category']}")
        
        # Realizar exploración emergente
        cadena_activacion = self._activar_emergente_real(concepto_inicial, profundidad, temperatura)
        
        # Analizar resultados
        if not cadena_activacion:
            return "❌ No se pudo generar pensamiento emergente"
        
        # Construir narrativa del pensamiento
        narrativa = self._construir_narrativa_real(concepto_inicial, cadena_activacion)
        
        # Detectar insights
        insights = self._detectar_insights_real(cadena_activacion)
        
        # Sugerencias basadas en patrones reales
        sugerencias = self._generar_sugerencias_reales(concepto_inicial, cadena_activacion)
        
        # Crear reporte completo
        reporte = self._generar_reporte_exploracion_real(
            concepto_inicial, narrativa, insights, sugerencias
        )
        
        # Guardar en historial
        pensamiento = {
            'concepto_inicial': concepto_inicial,
            'cadena_activacion': cadena_activacion,
            'insights': insights,
            'sugerencias': sugerencias,
            'timestamp': time.time(),
            'tipo': 'exploracion_real'
        }
        self.historial_pensamientos.append(pensamiento)
        
        return reporte
    
    def _buscar_conceptos_similares(self, termino_busqueda):
        """
        Busca conceptos similares en la memoria real
        """
        similares = []
        termino_lower = termino_busqueda.lower()
        
        for concepto in self.conceptos_reales.keys():
            if termino_lower in concepto.lower():
                similares.append(concepto)
        
        # Ordenar por frecuencia
        similares.sort(key=lambda x: self.conceptos_reales[x]['frequency'], reverse=True)
        
        return similares[:10]
    
    def _activar_emergente_real(self, concepto_inicial, profundidad, temperatura):
        """
        Realiza activación emergente usando el grafo real
        """
        cadena = []
        concepto_actual = concepto_inicial
        conceptos_visitados = set()
        
        for paso in range(profundidad):
            # Información del concepto actual
            info_actual = self.conceptos_reales[concepto_actual]
            
            # Obtener vecinos del grafo real
            vecinos = []
            if self.grafo.has_node(concepto_actual):
                for vecino in self.grafo.neighbors(concepto_actual):
                    if vecino not in conceptos_visitados:
                        peso = self.grafo[concepto_actual][vecino]['weight']
                        freq_vecino = self.conceptos_reales[vecino]['frequency']
                        
                        # Calcular activación combinando peso de relación y frecuencia
                        activacion = peso * 0.7 + (freq_vecino / 1000.0) * 0.3
                        vecinos.append((vecino, activacion))
            
            # Registrar estado actual
            estado_paso = {
                'paso': paso,
                'concepto_activo': concepto_actual,
                'frecuencia': info_actual['frequency'],
                'categoria': info_actual['category'],
                'vecinos_disponibles': len(vecinos)
            }
            cadena.append(estado_paso)
            
            conceptos_visitados.add(concepto_actual)
            
            # Seleccionar siguiente concepto
            if not vecinos:
                break
                
            # Aplicar temperatura para controlar exploración vs explotación
            vecinos.sort(key=lambda x: x[1], reverse=True)
            
            if random.random() < temperatura:
                # Exploración: elegir aleatoriamente entre top vecinos
                top_vecinos = vecinos[:min(3, len(vecinos))]
                siguiente = random.choice(top_vecinos)[0]
            else:
                # Explotación: elegir el más activado
                siguiente = vecinos[0][0]
            
            concepto_actual = siguiente
        
        return cadena
    
    def _construir_narrativa_real(self, concepto_inicial, cadena):
        """
        Construye narrativa del pensamiento basada en datos reales
        """
        narrativa = []
        narrativa.append(f"💭 Pensamiento emergente desde: {concepto_inicial}")
        
        info_inicial = self.conceptos_reales[concepto_inicial]
        narrativa.append(f"📊 Punto de partida: {info_inicial['frequency']} apariciones en {len(info_inicial['files'])} archivos")
        narrativa.append("")
        
        for i, estado in enumerate(cadena):
            concepto = estado['concepto_activo']
            frecuencia = estado['frecuencia']
            categoria = estado['categoria']
            
            emoji_categoria = self._get_emoji_categoria_real(categoria)
            
            narrativa.append(f"🔄 Paso {i+1}: {emoji_categoria} {concepto}")
            narrativa.append(f"   📈 Frecuencia: {frecuencia}x | Categoría: {categoria}")
            
            if i > 0:
                # Mostrar la conexión
                concepto_anterior = cadena[i-1]['concepto_activo']
                if self.grafo.has_edge(concepto_anterior, concepto):
                    fuerza_conexion = self.grafo[concepto_anterior][concepto]['weight']
                    narrativa.append(f"   🔗 Conexión: {fuerza_conexion:.3f}")
            
            narrativa.append("")
        
        return narrativa
    
    def _detectar_insights_real(self, cadena):
        """
        Detecta insights basados en la cadena de activación real
        """
        insights = []
        
        # Analizar categorías atravesadas
        categorias_visitadas = [estado['categoria'] for estado in cadena]
        categorias_unicas = set(categorias_visitadas)
        
        if len(categorias_unicas) > 2:
            insights.append({
                'tipo': 'cross_category_thinking',
                'descripcion': f'Pensamiento cross-categorial: {len(categorias_unicas)} categorías',
                'categorias': list(categorias_unicas),
                'relevancia': 0.8
            })
        
        # Detectar saltos de frecuencia
        frecuencias = [estado['frecuencia'] for estado in cadena]
        if len(frecuencias) > 1:
            max_freq = max(frecuencias)
            min_freq = min(frecuencias)
            
            if max_freq / min_freq > 10:  # Gran diferencia de frecuencias
                insights.append({
                    'tipo': 'frequency_jump',
                    'descripcion': 'Salto entre conceptos muy frecuentes y específicos',
                    'rango': f'{min_freq}x → {max_freq}x',
                    'relevancia': 0.7
                })
        
        # Detectar patrones técnicos
        conceptos_tecnicos = [estado['concepto_activo'] for estado in cadena 
                            if estado['categoria'].startswith('tech')]
        
        if len(conceptos_tecnicos) >= 3:
            insights.append({
                'tipo': 'technical_pattern',
                'descripcion': 'Cadena técnica detectada',
                'conceptos': conceptos_tecnicos,
                'relevancia': 0.9
            })
        
        return insights
    
    def _generar_sugerencias_reales(self, concepto_inicial, cadena):
        """
        Genera sugerencias basadas en patrones reales de Lucas
        """
        sugerencias = []
        
        # Analizar conceptos en la cadena
        conceptos_cadena = [estado['concepto_activo'] for estado in cadena]
        
        # Sugerencia 1: Conceptos relacionados no explorados
        vecinos_no_explorados = set()
        for concepto in conceptos_cadena:
            if self.grafo.has_node(concepto):
                for vecino in self.grafo.neighbors(concepto):
                    if vecino not in conceptos_cadena:
                        vecinos_no_explorados.add(vecino)
        
        if vecinos_no_explorados:
            # Ordenar por frecuencia
            vecinos_ordenados = sorted(
                list(vecinos_no_explorados),
                key=lambda x: self.conceptos_reales[x]['frequency'],
                reverse=True
            )[:5]
            
            sugerencias.append({
                'tipo': 'exploracion_adicional',
                'descripcion': 'Conceptos relacionados para explorar',
                'conceptos': vecinos_ordenados,
                'accion': 'explorar_desde_concepto_real'
            })
        
        # Sugerencia 2: Basada en patrones de Lucas
        categoria_dominante = max(set([estado['categoria'] for estado in cadena]),
                                key=lambda x: sum(1 for estado in cadena if estado['categoria'] == x))
        
        if categoria_dominante == 'tech_vba':
            sugerencias.append({
                'tipo': 'optimizacion_vba',
                'descripcion': 'Oportunidad de automatización VBA detectada',
                'accion': 'Considerar migración a Python o mejora de macros'
            })
        elif categoria_dominante == 'tech_opencv':
            sugerencias.append({
                'tipo': 'vision_artificial',
                'descripcion': 'Patrón de procesamiento de imágenes detectado',
                'accion': 'Explorar nuevas técnicas de computer vision'
            })
        
        return sugerencias
    
    def _generar_reporte_exploracion_real(self, concepto_inicial, narrativa, insights, sugerencias):
        """
        Genera reporte completo de la exploración
        """
        reporte = []
        reporte.append("🧠 PENSAMIENTO EMERGENTE CON MEMORIA REAL")
        reporte.append("=" * 60)
        reporte.append("")
        
        # Narrativa
        reporte.append("💭 CADENA DE PENSAMIENTO:")
        reporte.extend(narrativa)
        reporte.append("")
        
        # Insights
        if insights:
            reporte.append("💡 INSIGHTS DETECTADOS:")
            for i, insight in enumerate(insights, 1):
                reporte.append(f"{i}. {insight['tipo'].replace('_', ' ').title()}")
                reporte.append(f"   {insight['descripcion']}")
                reporte.append(f"   Relevancia: {insight['relevancia']:.1f}/1.0")
                reporte.append("")
        
        # Sugerencias
        if sugerencias:
            reporte.append("🎯 SUGERENCIAS BASADAS EN TUS PATRONES:")
            for i, sugerencia in enumerate(sugerencias, 1):
                reporte.append(f"{i}. {sugerencia['tipo'].replace('_', ' ').title()}")
                reporte.append(f"   {sugerencia['descripcion']}")
                if 'conceptos' in sugerencia:
                    conceptos_str = ', '.join(sugerencia['conceptos'][:3])
                    reporte.append(f"   Conceptos: {conceptos_str}")
                if 'accion' in sugerencia:
                    reporte.append(f"   Acción: {sugerencia['accion']}")
                reporte.append("")
        
        return "\n".join(reporte)
    
    def _get_emoji_categoria_real(self, categoria):
        """
        Emojis para categorías reales
        """
        emojis = {
            'tech_vba': '📊',
            'tech_opencv': '👁️',
            'tech_python': '🐍',
            'technical': '⚙️',
            'projects': '📁',
            'lucas_personal': '👤'
        }
        return emojis.get(categoria, '💡')
    
    def generar_insight_automatico(self):
        """
        Genera un insight automático basado en la memoria real
        """
        print("🔍 Generando insight automático desde memoria real...")
        
        # Seleccionar concepto interesante aleatoriamente
        conceptos_frecuentes = [(nombre, data) for nombre, data in self.conceptos_reales.items() 
                              if data['frequency'] > 20]
        
        if not conceptos_frecuentes:
            return "❌ No hay suficientes conceptos frecuentes para generar insights"
        
        concepto_elegido = random.choice(conceptos_frecuentes)[0]
        
        # Explorar desde ese concepto
        resultado = self.explorar_desde_concepto_real(concepto_elegido, profundidad=3, temperatura=0.4)
        
        return f"🎲 Insight automático desde '{concepto_elegido}':\n\n{resultado}"
    
    def consultar_estadisticas_reales(self):
        """
        Muestra estadísticas de la memoria real
        """
        print("📊 ESTADÍSTICAS DE MEMORIA REAL DE LUCAS")
        print("=" * 50)
        
        print(f"💾 Total conceptos: {self.estadisticas_reales['total_conceptos']}")
        print(f"🔗 Total relaciones: {self.estadisticas_reales['total_relaciones']}")
        print(f"⚙️ Conceptos técnicos: {self.estadisticas_reales['conceptos_tecnicos']}")
        print(f"📁 Proyectos detectados: {self.estadisticas_reales['proyectos_detectados']}")
        print()
        
        # Top 10 conceptos más frecuentes
        top_conceptos = sorted(self.conceptos_reales.items(), 
                             key=lambda x: x[1]['frequency'], 
                             reverse=True)[:10]
        
        print("🏆 TOP 10 CONCEPTOS MÁS FRECUENTES:")
        for i, (concepto, data) in enumerate(top_conceptos, 1):
            print(f"{i:2d}. {concepto} ({data['frequency']}x) - {data['category']}")
        
        print()
        
        # Patrones detectados
        if self.patrones_lucas_reales.get('especificos'):
            print("🧠 PATRONES DE LUCAS DETECTADOS:")
            for patron, valor in self.patrones_lucas_reales['especificos'].items():
                if valor > 0.1:
                    patron_nombre = patron.replace('_', ' ').title()
                    print(f"   • {patron_nombre}: {valor:.2f}")

def test_pensamiento_real():
    """
    Función de prueba para el pensamiento emergente con memoria real
    """
    print("🧪 PROBANDO PENSAMIENTO EMERGENTE CON MEMORIA REAL")
    print("=" * 60)
    
    # Crear sistema con memoria real
    pensamiento = PensamientoLucasReal()
    
    # Mostrar estadísticas
    pensamiento.consultar_estadisticas_reales()
    
    print("\n" + "="*60)
    print("🧠 PRUEBAS DE EXPLORACIÓN EMERGENTE")
    print("="*60)
    
    # Prueba 1: Explorar desde concepto muy frecuente
    print("\n1️⃣ EXPLORANDO DESDE 'cv2.cvtColor' (tu concepto más usado en OpenCV)")
    resultado1 = pensamiento.explorar_desde_concepto_real('cv2.cvtColor', profundidad=4)
    print(resultado1)
    
    # Prueba 2: Explorar desde proyecto
    print("\n2️⃣ EXPLORANDO DESDE 'tacografo' (tu proyecto)")
    resultado2 = pensamiento.explorar_desde_concepto_real('tacografo', profundidad=3)
    print(resultado2)
    
    # Prueba 3: Insight automático
    print("\n3️⃣ INSIGHT AUTOMÁTICO")
    insight = pensamiento.generar_insight_automatico()
    print(insight)
    
    return pensamiento

if __name__ == "__main__":
    # Ejecutar prueba completa
    pensamiento_lucas = test_pensamiento_real()
