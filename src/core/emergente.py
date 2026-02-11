# emergente_lucas.py - Pensamiento Emergente adaptado para Lucas
import numpy as np
import matplotlib.pyplot as plt
from nucleo_lucas import ConceptosLucas
import random
import time
from collections import defaultdict

class PensamientoLucas:
    """
    Sistema de pensamiento emergente específicamente adaptado para los proyectos
    y conceptos de Lucas
    """
    
    def __init__(self, sistema=None, dim_vector=15):
        """
        Inicializa el sistema de pensamiento emergente para Lucas
        """
        self.sistema = sistema if sistema else ConceptosLucas(dim_vector=dim_vector)
        self.historial_pensamientos = []
        
        # Contextos específicos de Lucas
        self.contextos_proyecto = {
            'desarrollo': ['Python', 'VBA', 'Excel', 'Automatizacion', 'Optimizacion'],
            'vision_artificial': ['OpenCV', 'Deteccion', 'Python', 'Tacografos'],  
            'ia_local': ['LM_Studio', 'RAG_System', 'Memory_System', 'IANAE'],
            'creatividad': ['ThreeJS', 'Hollow_Earth', 'Creatividad', 'Emergencia'],
            'personal': ['Lucas', 'Novelda', 'TOC_TDAH', 'Superpoder_Patrones']
        }
        
        # Patrones de pensamiento específicos de Lucas
        self.patrones_lucas = {
            'tecnico_optimizado': 0.8,      # Tendencia a soluciones técnicas eficientes
            'creativo_divergente': 0.7,     # Exploración de ideas no convencionales  
            'detalle_exhaustivo': 0.9,      # Análisis detallado (TOC benefit)
            'conexion_patterns': 0.85,      # Detección de patrones (TDAH benefit)
            'automatizacion_driven': 0.8    # Preferencia por automatizar
        }
    
    def explorar_desde_proyecto(self, proyecto, contexto=None, profundidad=4):
        """
        Explora pensamientos emergentes partiendo de un proyecto específico de Lucas
        """
        if proyecto not in self.sistema.conceptos:
            return f"Proyecto '{proyecto}' no encontrado en el universo conceptual"
            
        print(f"🚀 Explorando pensamiento emergente desde: {proyecto}")
        
        # Determinar contexto automáticamente si no se proporciona
        if not contexto:
            contexto = self._detectar_contexto_proyecto(proyecto)
            print(f"📍 Contexto detectado: {contexto}")
        
        # Activar proyecto inicial con parámetros optimizados para Lucas
        resultado = self.sistema.activar(
            proyecto, 
            pasos=profundidad,
            temperatura=0.2  # Algo de creatividad pero manteniendo coherencia
        )
        
        if not resultado:
            return "No se pudo generar pensamiento emergente"
            
        # Analizar el resultado
        activaciones_finales = resultado[-1]
        
        # Construir cadena de pensamiento emergente
        cadena = self._construir_cadena_emergente(proyecto, resultado, contexto)
        
        # Detectar conexiones inesperadas (superpoder Lucas)
        conexiones_inesperadas = self._detectar_conexiones_inesperadas(activaciones_finales)
        
        # Sugerir optimizaciones (patrón Lucas)
        optimizaciones = self._sugerir_optimizaciones(proyecto, activaciones_finales)
        
        # Crear reporte completo
        reporte = self._generar_reporte_exploracion(
            proyecto, cadena, conexiones_inesperadas, optimizaciones, contexto
        )
        
        # Guardar en historial
        pensamiento = {
            'proyecto_inicial': proyecto,
            'contexto': contexto,
            'cadena_emergente': cadena,
            'conexiones_inesperadas': conexiones_inesperadas,
            'optimizaciones': optimizaciones,
            'activaciones_finales': activaciones_finales,
            'timestamp': time.time()
        }
        self.historial_pensamientos.append(pensamiento)
        
        return reporte
    
    def _detectar_contexto_proyecto(self, proyecto):
        """
        Detecta automáticamente el contexto de un proyecto
        """
        # Activar brevemente el proyecto para ver qué se conecta
        resultado = self.sistema.activar(proyecto, pasos=2, temperatura=0.1)
        if not resultado:
            return 'general'
            
        activaciones = resultado[-1]
        conceptos_activos = [c for c, a in activaciones.items() if a > 0.2]
        
        # Determinar contexto por intersección
        scores_contexto = {}
        for contexto, conceptos_contexto in self.contextos_proyecto.items():
            interseccion = set(conceptos_activos) & set(conceptos_contexto)
            scores_contexto[contexto] = len(interseccion)
            
        # Retornar contexto con mayor score
        if scores_contexto:
            contexto_detectado = max(scores_contexto, key=scores_contexto.get)
            return contexto_detectado if scores_contexto[contexto_detectado] > 0 else 'general'
        
        return 'general'
    
    def _construir_cadena_emergente(self, proyecto_inicial, resultado_activacion, contexto):
        """
        Construye una cadena de pensamiento emergente narrativa
        """
        cadena = []
        
        # Analizar cada paso de la activación
        for paso, activaciones in enumerate(resultado_activacion):
            conceptos_paso = sorted(
                [(c, a) for c, a in activaciones.items() if a > 0.1],
                key=lambda x: x[1], reverse=True
            )[:5]  # Top 5 por paso
            
            if paso == 0:
                cadena.append(f"💡 Pensando en {proyecto_inicial}...")
            else:
                # Crear narrativa según el contexto
                if contexto == 'desarrollo':
                    cadena.append(f"🔧 Paso {paso}: Conectando herramientas técnicas")
                elif contexto == 'vision_artificial':
                    cadena.append(f"👁️ Paso {paso}: Explorando detección visual")
                elif contexto == 'ia_local':
                    cadena.append(f"🤖 Paso {paso}: Integrando sistemas de IA")
                elif contexto == 'creatividad':
                    cadena.append(f"🎨 Paso {paso}: Expandiendo creativamente")
                else:
                    cadena.append(f"🌟 Paso {paso}: Emergencia conceptual")
            
            # Añadir conceptos activos con interpretación
            for concepto, activacion in conceptos_paso:
                categoria = self.sistema.conceptos[concepto]['categoria']
                emoji = self._get_emoji_categoria(categoria)
                cadena.append(f"   {emoji} {concepto} ({activacion:.3f})")
        
        return cadena
    
    def _detectar_conexiones_inesperadas(self, activaciones):
        """
        Detecta conexiones que Lucas podría encontrar interesantes (patrón recognition)
        """
        conexiones = []
        
        # Encontrar conceptos activos de diferentes categorías
        conceptos_por_categoria = defaultdict(list)
        for concepto, activacion in activaciones.items():
            if activacion > 0.15:  # Umbral para considerarlo
                categoria = self.sistema.conceptos[concepto]['categoria']
                conceptos_por_categoria[categoria].append((concepto, activacion))
        
        # Buscar conexiones cross-categoría (esto a Lucas le encanta)
        categorias = list(conceptos_por_categoria.keys())
        for i, cat1 in enumerate(categorias):
            for cat2 in categorias[i+1:]:
                if cat1 != cat2:
                    conceptos_cat1 = conceptos_por_categoria[cat1]
                    conceptos_cat2 = conceptos_por_categoria[cat2]
                    
                    # Buscar la conexión más fuerte entre categorías
                    mejor_conexion = None
                    max_producto = 0
                    
                    for c1, a1 in conceptos_cat1:
                        for c2, a2 in conceptos_cat2:
                            producto = a1 * a2
                            if producto > max_producto:
                                max_producto = producto
                                mejor_conexion = (c1, c2, a1, a2)
                    
                    if mejor_conexion and max_producto > 0.1:
                        c1, c2, a1, a2 = mejor_conexion
                        
                        # Verificar si ya hay conexión directa
                        conexion_existente = 0
                        if self.sistema.grafo.has_edge(c1, c2):
                            conexion_existente = self.sistema.grafo[c1][c2]['weight']
                        
                        conexiones.append({
                            'conceptos': (c1, c2),
                            'categorias': (cat1, cat2),
                            'activaciones': (a1, a2),
                            'fuerza_emergente': max_producto,
                            'conexion_existente': conexion_existente,
                            'novedad': max_producto - conexion_existente
                        })
        
        # Ordenar por novedad (nuevas conexiones son más interesantes)
        conexiones.sort(key=lambda x: x['novedad'], reverse=True)
        
        return conexiones[:3]  # Top 3 conexiones más novedosas
    
    def _sugerir_optimizaciones(self, proyecto, activaciones):
        """
        Sugiere optimizaciones basadas en el patrón mental de Lucas
        """
        optimizaciones = []
        
        # Buscar conceptos de automatización no conectados fuertemente
        conceptos_automatizacion = ['Automatizacion', 'Optimizacion', 'Python']
        conceptos_activos = [c for c, a in activaciones.items() if a > 0.2]
        
        for concepto_auto in conceptos_automatizacion:
            if concepto_auto in activaciones and activaciones[concepto_auto] > 0.1:
                # Verificar si ya está fuertemente conectado al proyecto
                if self.sistema.grafo.has_edge(proyecto, concepto_auto):
                    fuerza_actual = self.sistema.grafo[proyecto][concepto_auto]['weight']
                    if fuerza_actual < 0.7:  # Conexión débil = oportunidad de optimización
                        optimizaciones.append({
                            'tipo': 'automatizacion',
                            'descripcion': f'Fortalecer automatización en {proyecto} usando {concepto_auto}',
                            'potencial': activaciones[concepto_auto] * (1 - fuerza_actual),
                            'herramienta': concepto_auto
                        })
        
        # Buscar patrones de detección no explorados
        if 'Deteccion' in activaciones and activaciones['Deteccion'] > 0.15:
            tecnologias_deteccion = ['OpenCV', 'Python']
            for tech in tecnologias_deteccion:
                if tech in activaciones and tech != proyecto:
                    optimizaciones.append({
                        'tipo': 'deteccion_patterns',
                        'descripcion': f'Aplicar detección de patrones de {proyecto} con {tech}',
                        'potencial': activaciones['Deteccion'] * activaciones.get(tech, 0),
                        'herramienta': tech
                    })
        
        # Buscar oportunidades de creatividad emergente
        if 'Creatividad' in activaciones and activaciones['Creatividad'] > 0.1:
            optimizaciones.append({
                'tipo': 'creatividad_emergente', 
                'descripcion': f'Explorar aplicación creativa de {proyecto} en nuevos contextos',
                'potencial': activaciones['Creatividad'],
                'herramienta': 'Pensamiento_Emergente'
            })
        
        # Ordenar por potencial
        optimizaciones.sort(key=lambda x: x['potencial'], reverse=True)
        
        return optimizaciones[:3]  # Top 3 optimizaciones
    
    def _generar_reporte_exploracion(self, proyecto, cadena, conexiones, optimizaciones, contexto):
        """
        Genera un reporte completo de la exploración emergente
        """
        reporte = []
        reporte.append(f"🚀 EXPLORACIÓN EMERGENTE: {proyecto.upper()}")
        reporte.append(f"📍 Contexto: {contexto.replace('_', ' ').title()}")
        reporte.append("=" * 60)
        reporte.append("")
        
        # Cadena de pensamiento
        reporte.append("💭 CADENA DE PENSAMIENTO EMERGENTE:")
        reporte.extend(cadena)
        reporte.append("")
        
        # Conexiones inesperadas
        if conexiones:
            reporte.append("🔗 CONEXIONES INESPERADAS DETECTADAS:")
            for i, conn in enumerate(conexiones, 1):
                c1, c2 = conn['conceptos']
                cat1, cat2 = conn['categorias']
                novedad = conn['novedad']
                
                reporte.append(f"{i}. {c1} ↔ {c2}")
                reporte.append(f"   Categorías: {cat1} → {cat2}")
                reporte.append(f"   Novedad emergente: {novedad:.3f}")
                reporte.append("")
        else:
            reporte.append("🔗 No se detectaron conexiones inesperadas significativas")
            reporte.append("")
        
        # Optimizaciones sugeridas
        if optimizaciones:
            reporte.append("⚡ OPTIMIZACIONES SUGERIDAS:")
            for i, opt in enumerate(optimizaciones, 1):
                tipo = opt['tipo'].replace('_', ' ').title()
                desc = opt['descripcion']
                potencial = opt['potencial']
                herramienta = opt['herramienta']
                
                reporte.append(f"{i}. {tipo}")
                reporte.append(f"   {desc}")
                reporte.append(f"   Potencial: {potencial:.3f} | Herramienta: {herramienta}")
                reporte.append("")
        else:
            reporte.append("⚡ No se identificaron optimizaciones inmediatas")
            reporte.append("")
        
        return "\n".join(reporte)
    
    def _get_emoji_categoria(self, categoria):
        """
        Retorna emoji apropiado para cada categoría
        """
        emojis = {
            'tecnologias': '🔧',
            'proyectos': '📁', 
            'lucas_personal': '👤',
            'conceptos_ianae': '🧠',
            'herramientas': '⚙️',
            'emergentes': '✨'
        }
        return emojis.get(categoria, '💡')
    
    def generar_pensamiento_contextual(self, contexto=None, longitud=6):
        """
        Genera un pensamiento siguiendo un contexto específico de los proyectos de Lucas
        """
        if not contexto:
            contexto = random.choice(list(self.contextos_proyecto.keys()))
            
        conceptos_contexto = self.contextos_proyecto.get(contexto, list(self.sistema.conceptos.keys()))
        
        # Elegir concepto inicial del contexto con ponderación por activaciones
        pesos = []
        for concepto in conceptos_contexto:
            if concepto in self.sistema.conceptos:
                peso = self.sistema.conceptos[concepto]['activaciones'] + 1
                pesos.append(peso)
            else:
                pesos.append(1)
                
        # Normalizar pesos
        total_peso = sum(pesos)
        probabilidades = [p/total_peso for p in pesos]
        
        # Seleccionar concepto inicial
        concepto_inicial = np.random.choice(conceptos_contexto, p=probabilidades)
        
        print(f"🎨 Generando pensamiento contextual: {contexto}")
        print(f"🌱 Semilla: {concepto_inicial}")
        
        # Generar cadena de pensamiento
        cadena_conceptos = [concepto_inicial]
        concepto_actual = concepto_inicial
        
        for paso in range(longitud - 1):
            # Activar concepto actual
            resultado = self.sistema.activar(
                concepto_actual,
                pasos=2,
                temperatura=self.patrones_lucas['creativo_divergente'] * 0.4  # Usar patrón de Lucas
            )
            
            if not resultado:
                break
                
            activaciones = resultado[-1]
            
            # Filtrar candidatos
            candidatos = []
            for c, a in activaciones.items():
                if (c != concepto_actual and 
                    c not in cadena_conceptos and 
                    a > 0.1):
                    
                    # Bonus si está en el contexto
                    bonus = 0.2 if c in conceptos_contexto else 0
                    candidatos.append((c, a + bonus))
            
            if not candidatos:
                break
                
            # Ordenar y elegir siguiente
            candidatos.sort(key=lambda x: x[1], reverse=True)
            
            # Aplicar patrón de pensamiento de Lucas
            if random.random() < self.patrones_lucas['detalle_exhaustivo']:
                # Elegir el más relacionado (análisis exhaustivo)
                siguiente = candidatos[0][0]
            else:
                # Algo de divergencia creativa
                candidatos_top = candidatos[:min(3, len(candidatos))]
                pesos_cand = [a for _, a in candidatos_top]
                total_cand = sum(pesos_cand)
                probs_cand = [p/total_cand for p in pesos_cand]
                idx = np.random.choice(range(len(candidatos_top)), p=probs_cand)
                siguiente = candidatos_top[idx][0]
            
            cadena_conceptos.append(siguiente)
            concepto_actual = siguiente
        
        # Crear texto narrativo del pensamiento
        texto_pensamiento = self._crear_narrativa_pensamiento(cadena_conceptos, contexto)
        
        # Registrar en historial
        pensamiento = {
            'contexto': contexto,
            'conceptos': cadena_conceptos,
            'texto': texto_pensamiento,
            'patron_aplicado': 'contextual_lucas',
            'timestamp': time.time()
        }
        self.historial_pensamientos.append(pensamiento)
        
        return texto_pensamiento
    
    def _crear_narrativa_pensamiento(self, conceptos, contexto):
        """
        Crea una narrativa fluida del pensamiento basada en el contexto
        """
        if contexto == 'desarrollo':
            conectores = ['optimizando con', 'implementando', 'automatizando mediante', 'integrando']
        elif contexto == 'vision_artificial':
            conectores = ['detectando', 'procesando', 'analizando', 'reconociendo']
        elif contexto == 'ia_local':
            conectores = ['conectando', 'procesando', 'integrando', 'emergiendo']
        elif contexto == 'creatividad':
            conectores = ['inspirando', 'combinando', 'explorando', 'creando']
        else:
            conectores = ['conectando', 'relacionando', 'explorando', 'emergiendo']
        
        # Construir narrativa
        narrativa = [f"💭 Pensamiento {contexto.replace('_', ' ')}: {conceptos[0]}"]
        
        for i in range(1, len(conceptos)):
            conector = random.choice(conectores)
            narrativa.append(f" → {conector} {conceptos[i]}")
            
        return "".join(narrativa)
    
    def experimento_convergencia_proyectos(self, proyectos_input=None):
        """
        Experimenta con convergencia entre múltiples proyectos de Lucas
        """
        if not proyectos_input:
            proyectos_disponibles = self.sistema.categorias.get('proyectos', [])
            if len(proyectos_disponibles) < 2:
                return "Se necesitan al menos 2 proyectos para convergencia"
            proyectos_input = random.sample(proyectos_disponibles, min(3, len(proyectos_disponibles)))
        
        print(f"🔬 EXPERIMENTO DE CONVERGENCIA DE PROYECTOS")
        print(f"📁 Proyectos: {', '.join(proyectos_input)}")
        print("=" * 50)
        
        # Activar todos los proyectos simultáneamente
        activaciones_convergentes = {}
        
        for proyecto in proyectos_input:
            if proyecto in self.sistema.conceptos:
                resultado = self.sistema.activar(proyecto, pasos=3, temperatura=0.2)
                if resultado:
                    for concepto, activacion in resultado[-1].items():
                        if activacion > 0.1:
                            if concepto in activaciones_convergentes:
                                activaciones_convergentes[concepto] += activacion
                            else:
                                activaciones_convergentes[concepto] = activacion
        
        # Normalizar activaciones convergentes
        max_activacion = max(activaciones_convergentes.values()) if activaciones_convergentes else 1
        for concepto in activaciones_convergentes:
            activaciones_convergentes[concepto] /= max_activacion
        
        # Encontrar conceptos de convergencia (activos en múltiples proyectos)
        conceptos_convergencia = [(c, a) for c, a in activaciones_convergentes.items() 
                                 if a > 0.3 and c not in proyectos_input]
        conceptos_convergencia.sort(key=lambda x: x[1], reverse=True)
        
        # Generar reporte de convergencia
        reporte = []
        reporte.append(f"🎯 PUNTOS DE CONVERGENCIA DETECTADOS:")
        reporte.append("")
        
        if conceptos_convergencia:
            for i, (concepto, activacion) in enumerate(conceptos_convergencia[:5], 1):
                categoria = self.sistema.conceptos[concepto]['categoria']
                emoji = self._get_emoji_categoria(categoria)
                
                reporte.append(f"{i}. {emoji} {concepto} (activación: {activacion:.3f})")
                
                # Mostrar conexiones con cada proyecto
                conexiones_proyecto = []
                for proyecto in proyectos_input:
                    if self.sistema.grafo.has_edge(concepto, proyecto):
                        fuerza = self.sistema.grafo[concepto][proyecto]['weight']
                        conexiones_proyecto.append(f"{proyecto}({fuerza:.2f})")
                
                if conexiones_proyecto:
                    reporte.append(f"   Conectado a: {', '.join(conexiones_proyecto)}")
                reporte.append("")
        else:
            reporte.append("• No se encontraron puntos de convergencia significativos")
            reporte.append("• Intenta con proyectos más relacionados o ajusta parámetros")
            reporte.append("")
        
        # Sugerir sinergias potenciales
        if len(conceptos_convergencia) >= 2:
            reporte.append("🚀 SINERGIAS POTENCIALES:")
            
            # Buscar pares de conceptos convergentes que podrían crear sinergias
            sinergias_encontradas = False
            for i in range(min(3, len(conceptos_convergencia))):
                for j in range(i+1, min(3, len(conceptos_convergencia))):
                    c1, a1 = conceptos_convergencia[i]
                    c2, a2 = conceptos_convergencia[j]
                    
                    # Calcular potencial de sinergia
                    potencial_sinergia = a1 * a2
                    
                    if potencial_sinergia > 0.2:
                        reporte.append(f"• {c1} + {c2}")
                        reporte.append(f"  Potencial: {potencial_sinergia:.3f}")
                        reporte.append(f"  Aplicación: Integrar en proyecto híbrido")
                        reporte.append("")
                        sinergias_encontradas = True
            
            if not sinergias_encontradas:
                reporte.append("• No se detectaron sinergias con potencial alto")
                reporte.append("• Las convergencias son independientes entre sí")
                reporte.append("")
        else:
            reporte.append("🚀 SINERGIAS POTENCIALES:")
            reporte.append("• Se necesitan más puntos de convergencia para sugerir sinergias")
            reporte.append("• Intenta con más proyectos relacionados")
            reporte.append("")
        
        resultado_texto = "\n".join(reporte)
        
        # Guardar experimento en historial
        if not resultado_texto:  # Seguridad adicional
            resultado_texto = "🔬 Experimento de convergencia completado sin resultados significativos"
            
        experimento = {
            'tipo': 'convergencia_proyectos',
            'proyectos': proyectos_input,
            'conceptos_convergencia': conceptos_convergencia,
            'activaciones_convergentes': activaciones_convergentes,
            'reporte': resultado_texto,
            'timestamp': time.time()
        }
        self.historial_pensamientos.append(experimento)
        
        return resultado_texto
    
    def detectar_oportunidades_automatizacion(self):
        """
        Detecta oportunidades de automatización en los proyectos de Lucas
        (uno de sus superpoderes favoritos)
        """
        print("🤖 DETECTANDO OPORTUNIDADES DE AUTOMATIZACIÓN...")
        
        oportunidades = []
        
        # Verificar si existe el concepto de automatización
        if 'Automatizacion' not in self.sistema.conceptos:
            return "🤖 OPORTUNIDADES DE AUTOMATIZACIÓN DETECTADAS\n" + "="*50 + "\n✅ Concepto 'Automatizacion' no encontrado en el sistema"
        
        # Activar concepto de automatización para ver conexiones
        resultado = self.sistema.activar('Automatizacion', pasos=4, temperatura=0.2)
        if not resultado:
            return "🤖 No se pudo analizar automatización"
            
        activaciones = resultado[-1]
        
        # Buscar proyectos con potencial de automatización no explotado
        proyectos = self.sistema.categorias.get('proyectos', [])
        
        for proyecto in proyectos:
            if proyecto in activaciones and activaciones[proyecto] > 0.2:
                # Verificar si ya está fuertemente automatizado
                automatizacion_actual = 0
                if self.sistema.grafo.has_edge(proyecto, 'Automatizacion'):
                    automatizacion_actual = self.sistema.grafo[proyecto]['Automatizacion']['weight']
                
                # Si hay potencial pero poca automatización actual = oportunidad
                potencial = activaciones[proyecto]
                gap_automatizacion = potencial - automatizacion_actual
                
                if gap_automatizacion > 0.3:
                    # Buscar herramientas específicas para este proyecto
                    herramientas_sugeridas = []
                    
                    # Activar el proyecto para ver qué herramientas se conectan
                    resultado_proyecto = self.sistema.activar(proyecto, pasos=2, temperatura=0.1)
                    if resultado_proyecto:
                        act_proyecto = resultado_proyecto[-1]
                        herramientas_tecnicas = ['Python', 'VBA', 'Excel', 'Docker']
                        
                        for herramienta in herramientas_tecnicas:
                            if (herramienta in act_proyecto and 
                                act_proyecto[herramienta] > 0.15 and
                                herramienta != proyecto):
                                herramientas_sugeridas.append(herramienta)
                    
                    oportunidades.append({
                        'proyecto': proyecto,
                        'potencial': potencial,
                        'automatizacion_actual': automatizacion_actual,
                        'gap': gap_automatizacion,
                        'herramientas_sugeridas': herramientas_sugeridas,
                        'prioridad': gap_automatizacion * potencial
                    })
        
        # Ordenar por prioridad
        oportunidades.sort(key=lambda x: x['prioridad'], reverse=True)
        
        # Generar reporte
        reporte = []
        reporte.append("🤖 OPORTUNIDADES DE AUTOMATIZACIÓN DETECTADAS")
        reporte.append("=" * 50)
        
        if oportunidades:
            for i, oport in enumerate(oportunidades, 1):
                proyecto = oport['proyecto']
                gap = oport['gap']
                herramientas = oport['herramientas_sugeridas']
                prioridad = oport['prioridad']
                
                reporte.append(f"{i}. 📁 {proyecto}")
                reporte.append(f"   Potencial de automatización: {gap:.3f}")
                reporte.append(f"   Prioridad: {prioridad:.3f}")
                
                if herramientas:
                    reporte.append(f"   Herramientas sugeridas: {', '.join(herramientas)}")
                
                # Sugerir pasos específicos
                if 'Python' in herramientas:
                    reporte.append(f"   💡 Implementar scripts Python para {proyecto}")
                if 'VBA' in herramientas and 'Excel' in herramientas:
                    reporte.append(f"   💡 Crear macros VBA para procesos repetitivos")
                if 'Docker' in herramientas:
                    reporte.append(f"   💡 Containerizar {proyecto} para deployment automático")
                
                reporte.append("")
        else:
            reporte.append("✅ Todos los proyectos parecen bien automatizados")
            reporte.append("   O el potencial de automatización es bajo actualmente")
        
        return "\n".join(reporte)
    
    def analizar_patrones_personales(self):
        """
        Analiza los patrones específicos de pensamiento y trabajo de Lucas
        """
        print("🧠 ANALIZANDO PATRONES PERSONALES DE LUCAS...")
        
        # Activar concepto de Lucas para ver su universo conceptual
        resultado = self.sistema.activar('Lucas', pasos=4, temperatura=0.2)
        if not resultado:
            return "No se pudo analizar patrones personales"
            
        activaciones = resultado[-1]
        
        # Categorizar activaciones por tipo
        patrones_detectados = {
            'fortalezas_tecnicas': [],
            'superpoderes_cognitivos': [],
            'proyectos_preferidos': [],
            'herramientas_dominantes': [],
            'areas_emergentes': []
        }
        
        for concepto, activacion in activaciones.items():
            if activacion > 0.2 and concepto != 'Lucas':
                categoria = self.sistema.conceptos[concepto]['categoria']
                
                if categoria == 'tecnologias' and activacion > 0.4:
                    patrones_detectados['fortalezas_tecnicas'].append((concepto, activacion))
                elif categoria == 'lucas_personal' and 'superpoder' in concepto.lower():
                    patrones_detectados['superpoderes_cognitivos'].append((concepto, activacion))
                elif categoria == 'proyectos' and activacion > 0.3:
                    patrones_detectados['proyectos_preferidos'].append((concepto, activacion))
                elif categoria == 'herramientas' and activacion > 0.35:
                    patrones_detectados['herramientas_dominantes'].append((concepto, activacion))
                elif categoria == 'emergentes' and activacion > 0.25:
                    patrones_detectados['areas_emergentes'].append((concepto, activacion))
        
        # Generar análisis personalizado
        reporte = []
        reporte.append("🧠 ANÁLISIS DE PATRONES PERSONALES - LUCAS")
        reporte.append("=" * 50)
        
        # Fortalezas técnicas
        if patrones_detectados['fortalezas_tecnicas']:
            reporte.append("💪 FORTALEZAS TÉCNICAS DOMINANTES:")
            for concepto, fuerza in sorted(patrones_detectados['fortalezas_tecnicas'], 
                                         key=lambda x: x[1], reverse=True):
                reporte.append(f"   🔧 {concepto}: {fuerza:.3f}")
            reporte.append("")
        
        # Superpoderes cognitivos
        if patrones_detectados['superpoderes_cognitivos']:
            reporte.append("🚀 SUPERPODERES COGNITIVOS ACTIVOS:")
            for concepto, fuerza in sorted(patrones_detectados['superpoderes_cognitivos'], 
                                         key=lambda x: x[1], reverse=True):
                reporte.append(f"   ⚡ {concepto}: {fuerza:.3f}")
            reporte.append("")
        
        # Proyectos con mayor afinidad
        if patrones_detectados['proyectos_preferidos']:
            reporte.append("📁 PROYECTOS CON MAYOR AFINIDAD:")
            for concepto, fuerza in sorted(patrones_detectados['proyectos_preferidos'], 
                                         key=lambda x: x[1], reverse=True):
                reporte.append(f"   📊 {concepto}: {fuerza:.3f}")
            reporte.append("")
        
        # Herramientas dominantes
        if patrones_detectados['herramientas_dominantes']:
            reporte.append("⚙️ HERRAMIENTAS MENTALES DOMINANTES:")
            for concepto, fuerza in sorted(patrones_detectados['herramientas_dominantes'], 
                                         key=lambda x: x[1], reverse=True):
                reporte.append(f"   🛠️ {concepto}: {fuerza:.3f}")
            reporte.append("")
        
        # Áreas emergentes
        if patrones_detectados['areas_emergentes']:
            reporte.append("✨ ÁREAS EMERGENTES DE INTERÉS:")
            for concepto, fuerza in sorted(patrones_detectados['areas_emergentes'], 
                                         key=lambda x: x[1], reverse=True):
                reporte.append(f"   🌟 {concepto}: {fuerza:.3f}")
            reporte.append("")
        
        # Recomendaciones personalizadas
        reporte.append("💡 RECOMENDACIONES PERSONALIZADAS:")
        
        # Basado en TOC+TDAH = Superpoder
        if any('TOC' in c[0] or 'TDAH' in c[0] for c in patrones_detectados['superpoderes_cognitivos']):
            reporte.append("   🎯 Aprovechar detección de patrones para nuevos proyectos")
            reporte.append("   🔍 Usar análisis exhaustivo como ventaja competitiva")
        
        # Basado en fortalezas técnicas
        tecnicas_fuertes = [c[0] for c in patrones_detectados['fortalezas_tecnicas']]
        if 'Python' in tecnicas_fuertes and 'OpenCV' in tecnicas_fuertes:
            reporte.append("   🤖 Combinar Python+OpenCV en proyectos de visión artificial")
        
        # Basado en automatización
        if any('Automatizacion' in c[0] for c in patrones_detectados['herramientas_dominantes']):
            reporte.append("   ⚡ Buscar más procesos manuales para automatizar")
        
        return "\n".join(reporte)
    
    def visualizar_pensamiento_lucas(self, indice=-1, mostrar_categorias=True):
        """
        Visualización específica para los pensamientos de Lucas
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
        
        # Mostrar información del pensamiento
        print(f"🧠 PENSAMIENTO LUCAS #{indice + 1}")
        print("=" * 40)
        
        if 'proyecto_inicial' in pensamiento:
            print(f"🚀 Proyecto inicial: {pensamiento['proyecto_inicial']}")
            print(f"📍 Contexto: {pensamiento.get('contexto', 'N/A')}")
        elif 'contexto' in pensamiento:
            print(f"🎨 Pensamiento contextual: {pensamiento['contexto']}")
        elif 'tipo' in pensamiento:
            print(f"🔬 Experimento: {pensamiento['tipo']}")
        
        # Mostrar el contenido principal
        if 'reporte' in pensamiento:
            print("\n" + pensamiento['reporte'])
        elif 'texto' in pensamiento:
            print(f"\n{pensamiento['texto']}")
        elif 'cadena_emergente' in pensamiento:
            print("\n💭 Cadena emergente:")
            for linea in pensamiento['cadena_emergente']:
                print(linea)
        
        print("=" * 40)
        
        # Visualizar red si hay activaciones
        if 'activaciones_finales' in pensamiento and pensamiento['activaciones_finales']:
            titulo = f"Pensamiento Lucas #{indice + 1}"
            if 'proyecto_inicial' in pensamiento:
                titulo += f" - {pensamiento['proyecto_inicial']}"
                
            self.sistema.visualizar_lucas(
                activaciones=pensamiento['activaciones_finales'],
                mostrar_categorias=mostrar_categorias
            )
    
    def exportar_insights_lucas(self, archivo='insights_lucas.txt'):
        """
        Exporta todos los insights y pensamientos de Lucas a un archivo
        """
        try:
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write("🧠 INSIGHTS Y PENSAMIENTOS EMERGENTES - LUCAS\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de pensamientos: {len(self.historial_pensamientos)}\n\n")
                
                # Exportar cada pensamiento
                for i, pensamiento in enumerate(self.historial_pensamientos):
                    f.write(f"\n--- PENSAMIENTO #{i+1} ---\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pensamiento['timestamp']))}\n")
                    
                    if 'proyecto_inicial' in pensamiento:
                        f.write(f"Tipo: Exploración de proyecto\n")
                        f.write(f"Proyecto: {pensamiento['proyecto_inicial']}\n")
                        f.write(f"Contexto: {pensamiento.get('contexto', 'N/A')}\n\n")
                        
                        if 'reporte' in pensamiento:
                            f.write(pensamiento['reporte'] + "\n")
                    
                    elif 'contexto' in pensamiento and 'texto' in pensamiento:
                        f.write(f"Tipo: Pensamiento contextual\n")
                        f.write(f"Contexto: {pensamiento['contexto']}\n")
                        f.write(f"Texto: {pensamiento['texto']}\n")
                    
                    elif 'tipo' in pensamiento:
                        f.write(f"Tipo: {pensamiento['tipo']}\n")
                        if 'reporte' in pensamiento:
                            f.write(pensamiento['reporte'] + "\n")
                    
                    f.write("\n" + "-" * 50 + "\n")
                
            print(f"✅ Insights exportados a: {archivo}")
            return True
            
        except Exception as e:
            print(f"❌ Error al exportar: {e}")
            return False

# Función de prueba rápida
def test_pensamiento_lucas():
    """
    Función de prueba para el pensamiento emergente de Lucas
    """
    from nucleo_lucas import crear_universo_lucas
    
    print("🧪 INICIANDO PRUEBA DE PENSAMIENTO EMERGENTE...")
    
    # Crear sistema
    sistema = crear_universo_lucas()
    
    # Crear pensamiento emergente
    pensamiento = PensamientoLucas(sistema)
    
    # Pruebas básicas
    print("\n1. Explorando desde proyecto Tacógrafos...")
    resultado1 = pensamiento.explorar_desde_proyecto('Tacografos')
    print(resultado1)
    
    print("\n2. Generando pensamiento contextual de desarrollo...")
    resultado2 = pensamiento.generar_pensamiento_contextual('desarrollo')
    print(resultado2)
    
    print("\n3. Detectando oportunidades de automatización...")
    resultado3 = pensamiento.detectar_oportunidades_automatizacion()
    print(resultado3)
    
    print("\n4. Analizando patrones personales...")
    resultado4 = pensamiento.analizar_patrones_personales()
    print(resultado4)
    
    return pensamiento

if __name__ == "__main__":
    # Ejecutar prueba
    pensamiento_lucas = test_pensamiento_lucas()