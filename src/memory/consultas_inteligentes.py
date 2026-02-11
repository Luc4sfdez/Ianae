# ianae_consultas_inteligentes.py - Sistema de Consultas Avanzadas
import sqlite3
import json
from collections import defaultdict, Counter
import itertools
import time
from datetime import datetime

class ConsultasInteligentesLucas:
    """
    Sistema de consultas inteligentes para analizar los patrones reales de Lucas
    Basado en 4,545 conceptos y 832K relaciones de memoria real
    """
    
    def __init__(self, memory_db_path="C:/IANAE/IANAE_MEMORY/ianae_index.db"):
        """
        Inicializa el sistema de consultas inteligentes
        """
        self.db_path = memory_db_path
        self.conceptos_cache = {}
        self.relaciones_cache = {}
        
        print("🔍 Inicializando Sistema de Consultas Inteligentes...")
        print(f"📍 Base de datos: {memory_db_path}")
        
        # Cargar datos para consultas rápidas
        self._cargar_cache()
        
        print(f"✅ Sistema listo: {len(self.conceptos_cache)} conceptos en cache")
    
    def _cargar_cache(self):
        """
        Carga conceptos y relaciones en cache para consultas rápidas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cache de conceptos
            cursor.execute('''
                SELECT name, usage_count, category, strength, file_path
                FROM concepts
                ORDER BY usage_count DESC
            ''')
            
            for row in cursor.fetchall():
                name, usage_count, category, strength, file_path = row
                self.conceptos_cache[name] = {
                    'frequency': usage_count,
                    'category': category,
                    'strength': strength,
                    'files': file_path.split(',') if file_path else []
                }
            
            # Cache de relaciones (top 10K para rendimiento)
            cursor.execute('''
                SELECT concept_a, concept_b, strength
                FROM relationships
                ORDER BY strength DESC
                LIMIT 10000
            ''')
            
            for concept_a, concept_b, strength in cursor.fetchall():
                key = tuple(sorted([concept_a, concept_b]))
                self.relaciones_cache[key] = strength
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error cargando cache: {e}")
    
    def consulta_tecnologias_juntas(self, min_coocurrencia=5, top_n=15):
        """
        ¿Qué tecnologías uso juntas más frecuentemente?
        """
        print("🔍 ANALIZANDO: ¿Qué tecnologías uso juntas más frecuentemente?")
        print("=" * 60)
        
        # Identificar conceptos técnicos
        conceptos_tecnicos = {
            nombre: data for nombre, data in self.conceptos_cache.items()
            if (data['category'].startswith('tech') and 
                data['frequency'] >= min_coocurrencia and
                any(tech in nombre.lower() for tech in 
                    ['cv2', 'python', 'vba', 'excel', 'docker', 'import', 'def', 'class']))
        }
        
        print(f"📊 Analizando {len(conceptos_tecnicos)} conceptos técnicos...")
        
        # Buscar co-ocurrencias en relaciones
        coocurrencias = defaultdict(float)
        
        for (concept_a, concept_b), strength in self.relaciones_cache.items():
            if (concept_a in conceptos_tecnicos and 
                concept_b in conceptos_tecnicos and
                concept_a != concept_b):
                
                # Crear par ordenado por categoría/tipo
                cat_a = conceptos_tecnicos[concept_a]['category']
                cat_b = conceptos_tecnicos[concept_b]['category']
                
                # Agrupar por tecnología base
                tech_a = self._extraer_tecnologia_base(concept_a)
                tech_b = self._extraer_tecnologia_base(concept_b)
                
                if tech_a != tech_b:  # Solo diferentes tecnologías
                    pair_key = tuple(sorted([tech_a, tech_b]))
                    coocurrencias[pair_key] += strength * (
                        conceptos_tecnicos[concept_a]['frequency'] + 
                        conceptos_tecnicos[concept_b]['frequency']
                    ) / 2000.0  # Normalizar
        
        # Ordenar por co-ocurrencia
        coocurrencias_ordenadas = sorted(
            coocurrencias.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        # Generar reporte
        reporte = []
        reporte.append("🤝 TECNOLOGÍAS QUE USAS JUNTAS MÁS FRECUENTEMENTE:")
        reporte.append("")
        
        for i, ((tech_a, tech_b), score) in enumerate(coocurrencias_ordenadas, 1):
            reporte.append(f"{i:2d}. {tech_a} + {tech_b}")
            reporte.append(f"    Índice de co-uso: {score:.3f}")
            
            # Buscar ejemplos específicos
            ejemplos = self._buscar_ejemplos_coocurrencia(tech_a, tech_b)
            if ejemplos:
                reporte.append(f"    Ejemplo: {ejemplos[0]}")
            reporte.append("")
        
        return "\n".join(reporte)
    
    def _extraer_tecnologia_base(self, concepto):
        """
        Extrae la tecnología base de un concepto específico
        """
        concepto_lower = concepto.lower()
        
        if 'cv2' in concepto_lower or 'opencv' in concepto_lower:
            return 'OpenCV'
        elif any(vba in concepto_lower for vba in ['ws.', 'cells', 'range', 'application.', 'debug.print']):
            return 'VBA/Excel'
        elif any(py in concepto_lower for py in ['import', 'def', 'class', 'self.', '.py']):
            return 'Python'
        elif 'docker' in concepto_lower or 'compose' in concepto_lower:
            return 'Docker'
        elif 'document.' in concepto_lower or 'event.' in concepto_lower:
            return 'JavaScript'
        elif 'df.' in concepto_lower or 'pandas' in concepto_lower:
            return 'Pandas'
        elif 'np.' in concepto_lower or 'numpy' in concepto_lower:
            return 'NumPy'
        else:
            return concepto.split('.')[0] if '.' in concepto else concepto
    
    def _buscar_ejemplos_coocurrencia(self, tech_a, tech_b):
        """
        Busca ejemplos específicos de co-ocurrencia entre tecnologías
        """
        ejemplos = []
        
        for (concept_a, concept_b), _ in self.relaciones_cache.items():
            if (self._extraer_tecnologia_base(concept_a) == tech_a and
                self._extraer_tecnologia_base(concept_b) == tech_b):
                ejemplos.append(f"{concept_a} ↔ {concept_b}")
                if len(ejemplos) >= 3:
                    break
        
        return ejemplos
    
    def consulta_patrones_desarrollo(self, top_n=20):
        """
        ¿Cuáles son mis patrones de desarrollo más comunes?
        """
        print("🔍 ANALIZANDO: ¿Cuáles son mis patrones de desarrollo más comunes?")
        print("=" * 60)
        
        # Analizar patrones por categorías y frecuencias
        patrones = {
            'POO_Patterns': [],
            'Excel_Automation': [],
            'Image_Processing': [],
            'Data_Manipulation': [],
            'Development_Tools': [],
            'Debugging_Patterns': []
        }
        
        for concepto, data in self.conceptos_cache.items():
            freq = data['frequency']
            
            if freq < 10:  # Solo patrones significativos
                continue
            
            concepto_lower = concepto.lower()
            
            # Clasificar patrones
            if 'self.' in concepto:
                patrones['POO_Patterns'].append((concepto, freq))
            elif any(excel in concepto_lower for excel in ['ws.', 'cells', 'range', 'application.']):
                patrones['Excel_Automation'].append((concepto, freq))
            elif any(cv in concepto_lower for cv in ['cv2', 'imagen', 'contour', 'color']):
                patrones['Image_Processing'].append((concepto, freq))
            elif any(data in concepto_lower for data in ['df.', 'pandas', 'np.']):
                patrones['Data_Manipulation'].append((concepto, freq))
            elif any(dev in concepto_lower for dev in ['main.py', 'compose', 'docker', 'import']):
                patrones['Development_Tools'].append((concepto, freq))
            elif any(debug in concepto_lower for debug in ['debug.print', 'console.log', 'print(']):
                patrones['Debugging_Patterns'].append((concepto, freq))
        
        # Ordenar cada categoría por frecuencia
        for categoria in patrones:
            patrones[categoria].sort(key=lambda x: x[1], reverse=True)
            patrones[categoria] = patrones[categoria][:5]  # Top 5 por categoría
        
        # Generar reporte
        reporte = []
        reporte.append("🧠 TUS PATRONES DE DESARROLLO MÁS COMUNES:")
        reporte.append("")
        
        emoji_categoria = {
            'POO_Patterns': '🎯',
            'Excel_Automation': '📊',
            'Image_Processing': '👁️',
            'Data_Manipulation': '📈',
            'Development_Tools': '🔧',
            'Debugging_Patterns': '🐛'
        }
        
        for categoria, conceptos in patrones.items():
            if conceptos:
                emoji = emoji_categoria.get(categoria, '💡')
                nombre_categoria = categoria.replace('_', ' ')
                reporte.append(f"{emoji} {nombre_categoria.upper()}:")
                
                for concepto, freq in conceptos:
                    reporte.append(f"   • {concepto} ({freq}x)")
                reporte.append("")
        
        # Análisis de dominancia
        reporte.append("📊 ANÁLISIS DE DOMINANCIA:")
        total_frecuencia = sum(data['frequency'] for data in self.conceptos_cache.values())
        
        dominancia_categoria = defaultdict(int)
        for concepto, data in self.conceptos_cache.items():
            if data['frequency'] >= 50:  # Solo conceptos muy frecuentes
                tech = self._extraer_tecnologia_base(concepto)
                dominancia_categoria[tech] += data['frequency']
        
        for tech, freq_total in sorted(dominancia_categoria.items(), 
                                     key=lambda x: x[1], reverse=True)[:5]:
            porcentaje = (freq_total / total_frecuencia) * 100
            reporte.append(f"   • {tech}: {freq_total} usos ({porcentaje:.1f}% del total)")
        
        return "\n".join(reporte)
    
    def consulta_proyectos_relacionados(self, tecnologia, top_n=10):
        """
        ¿Qué proyectos están relacionados con una tecnología específica?
        """
        print(f"🔍 ANALIZANDO: ¿Qué proyectos relacionados con '{tecnologia}'?")
        print("=" * 60)
        
        # Buscar conceptos relacionados con la tecnología
        conceptos_tech = []
        tech_lower = tecnologia.lower()
        
        for concepto, data in self.conceptos_cache.items():
            if tech_lower in concepto.lower():
                conceptos_tech.append((concepto, data))
        
        if not conceptos_tech:
            return f"❌ No se encontraron conceptos relacionados con '{tecnologia}'"
        
        print(f"📊 Encontrados {len(conceptos_tech)} conceptos relacionados...")
        
        # Buscar proyectos y archivos relacionados
        proyectos_relacionados = defaultdict(float)
        archivos_relacionados = defaultdict(int)
        
        for concepto, data in conceptos_tech:
            # Analizar archivos donde aparece
            for archivo in data['files']:
                if archivo:
                    # Extraer nombre de proyecto del archivo
                    proyecto = self._extraer_proyecto_de_archivo(archivo)
                    if proyecto:
                        proyectos_relacionados[proyecto] += data['frequency'] * data['strength']
                    
                    archivos_relacionados[archivo] += data['frequency']
        
        # Buscar conexiones adicionales por relaciones
        for concepto, _ in conceptos_tech:
            for (concept_a, concept_b), strength in self.relaciones_cache.items():
                if concepto in [concept_a, concept_b]:
                    otro_concepto = concept_b if concepto == concept_a else concept_a
                    
                    # Si el otro concepto parece ser un proyecto
                    if (self.conceptos_cache.get(otro_concepto, {}).get('category') == 'projects' or
                        any(proj in otro_concepto.lower() for proj in 
                            ['tacografo', 'vba2python', 'ianae', 'proyecto'])):
                        proyectos_relacionados[otro_concepto] += strength * 100
        
        # Generar reporte
        reporte = []
        reporte.append(f"📁 PROYECTOS RELACIONADOS CON {tecnologia.upper()}:")
        reporte.append("")
        
        # Proyectos identificados
        if proyectos_relacionados:
            proyectos_ordenados = sorted(
                proyectos_relacionados.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            reporte.append("🎯 PROYECTOS DETECTADOS:")
            for i, (proyecto, score) in enumerate(proyectos_ordenados, 1):
                reporte.append(f"{i:2d}. {proyecto}")
                reporte.append(f"    Relevancia: {score:.1f}")
                reporte.append("")
        
        # Archivos más relevantes
        if archivos_relacionados:
            archivos_ordenados = sorted(
                archivos_relacionados.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            reporte.append("📄 ARCHIVOS MÁS RELEVANTES:")
            for archivo, freq in archivos_ordenados:
                reporte.append(f"   • {archivo} ({freq} conceptos relacionados)")
            reporte.append("")
        
        # Conceptos técnicos específicos
        conceptos_ordenados = sorted(conceptos_tech, key=lambda x: x[1]['frequency'], reverse=True)[:10]
        reporte.append(f"⚙️ CONCEPTOS ESPECÍFICOS DE {tecnologia.upper()}:")
        for concepto, data in conceptos_ordenados:
            reporte.append(f"   • {concepto} ({data['frequency']}x)")
        
        return "\n".join(reporte)
    
    def _extraer_proyecto_de_archivo(self, nombre_archivo):
        """
        Extrae el nombre del proyecto de un nombre de archivo
        """
        if not nombre_archivo:
            return None
        
        # Patrones conocidos de proyectos de Lucas
        if 'tacografo' in nombre_archivo.lower():
            return 'Tacógrafos'
        elif 'vba2python' in nombre_archivo.lower():
            return 'VBA2Python'
        elif 'ianae' in nombre_archivo.lower():
            return 'IANAE'
        elif 'docker' in nombre_archivo.lower():
            return 'Docker Setup'
        elif any(term in nombre_archivo.lower() for term in ['cv', 'vision', 'imagen']):
            return 'Computer Vision'
        elif 'excel' in nombre_archivo.lower() or 'macro' in nombre_archivo.lower():
            return 'Excel Automation'
        else:
            # Extraer primera parte del nombre de archivo
            base_name = nombre_archivo.split('_')[0].split('.')[0]
            if len(base_name) > 3:
                return base_name.title()
        
        return None
    
    def consulta_evolucion_temporal(self):
        """
        ¿Cómo han evolucionado mis intereses técnicos?
        """
        print("🔍 ANALIZANDO: ¿Cómo han evolucionado mis intereses técnicos?")
        print("=" * 60)
        
        # Analizar categorías por intensidad de uso
        intensidad_categorias = defaultdict(list)
        
        for concepto, data in self.conceptos_cache.items():
            categoria = data['category']
            freq = data['frequency']
            
            if freq >= 5:  # Solo conceptos significativos
                intensidad_categorias[categoria].append((concepto, freq))
        
        # Calcular dominancia por categoría
        dominancia = {}
        for categoria, conceptos in intensidad_categorias.items():
            total_freq = sum(freq for _, freq in conceptos)
            dominancia[categoria] = {
                'total_frequency': total_freq,
                'concept_count': len(conceptos),
                'avg_frequency': total_freq / len(conceptos) if conceptos else 0,
                'top_concepts': sorted(conceptos, key=lambda x: x[1], reverse=True)[:3]
            }
        
        # Generar reporte
        reporte = []
        reporte.append("📈 EVOLUCIÓN DE TUS INTERESES TÉCNICOS:")
        reporte.append("")
        
        # Ordenar categorías por dominancia
        categorias_ordenadas = sorted(
            dominancia.items(),
            key=lambda x: x[1]['total_frequency'],
            reverse=True
        )
        
        emojis_categoria = {
            'technical': '⚙️',
            'tech_python': '🐍',
            'tech_opencv': '👁️',
            'tech_vba': '📊',
            'projects': '📁',
            'lucas_personal': '👤'
        }
        
        for categoria, stats in categorias_ordenadas:
            emoji = emojis_categoria.get(categoria, '💡')
            reporte.append(f"{emoji} {categoria.replace('_', ' ').upper()}:")
            reporte.append(f"   Intensidad total: {stats['total_frequency']} usos")
            reporte.append(f"   Conceptos únicos: {stats['concept_count']}")
            reporte.append(f"   Promedio por concepto: {stats['avg_frequency']:.1f}")
            
            reporte.append("   Top conceptos:")
            for concepto, freq in stats['top_concepts']:
                reporte.append(f"      • {concepto} ({freq}x)")
            reporte.append("")
        
        # Análisis de especialización
        reporte.append("🎯 ANÁLISIS DE ESPECIALIZACIÓN:")
        total_usos = sum(stats['total_frequency'] for stats in dominancia.values())
        
        for categoria, stats in categorias_ordenadas[:5]:
            porcentaje = (stats['total_frequency'] / total_usos) * 100
            reporte.append(f"   • {categoria}: {porcentaje:.1f}% de tu actividad técnica")
        
        return "\n".join(reporte)
    
    def consulta_personalizada(self, pregunta):
        """
        Sistema de consulta en lenguaje natural
        """
        pregunta_lower = pregunta.lower()
        
        if any(word in pregunta_lower for word in ['tecnologías juntas', 'uso juntas', 'combinaciones']):
            return self.consulta_tecnologias_juntas()
        elif any(word in pregunta_lower for word in ['patrones', 'desarrollo', 'código']):
            return self.consulta_patrones_desarrollo()
        elif any(word in pregunta_lower for word in ['proyectos', 'relacionados']):
            # Extraer tecnología de la pregunta
            for concepto in self.conceptos_cache.keys():
                if concepto.lower() in pregunta_lower and len(concepto) > 3:
                    return self.consulta_proyectos_relacionados(concepto)
            return "❓ ¿Con qué tecnología quieres ver proyectos relacionados?"
        elif any(word in pregunta_lower for word in ['evolución', 'temporal', 'cambio', 'intereses']):
            return self.consulta_evolucion_temporal()
        else:
            return self._sugerir_consultas()
    
    def _sugerir_consultas(self):
        """
        Sugiere consultas disponibles
        """
        sugerencias = [
            "🔍 CONSULTAS DISPONIBLES:",
            "",
            "1. '¿Qué tecnologías uso juntas más frecuentemente?'",
            "2. '¿Cuáles son mis patrones de desarrollo más comunes?'",
            "3. '¿Qué proyectos están relacionados con [tecnología]?'",
            "4. '¿Cómo han evolucionado mis intereses técnicos?'",
            "",
            "💡 O usa los métodos directos:",
            "   • consulta_tecnologias_juntas()",
            "   • consulta_patrones_desarrollo()",
            "   • consulta_proyectos_relacionados('opencv')",
            "   • consulta_evolucion_temporal()"
        ]
        
        return "\n".join(sugerencias)

def test_consultas_inteligentes():
    """
    Prueba completa del sistema de consultas inteligentes
    """
    print("🧪 PROBANDO SISTEMA DE CONSULTAS INTELIGENTES")
    print("=" * 70)
    
    # Inicializar sistema
    consultas = ConsultasInteligentesLucas()
    
    print("\n" + "="*70)
    print("🤝 CONSULTA 1: TECNOLOGÍAS QUE USAS JUNTAS")
    print("="*70)
    resultado1 = consultas.consulta_tecnologias_juntas()
    print(resultado1)
    
    print("\n" + "="*70)
    print("🧠 CONSULTA 2: PATRONES DE DESARROLLO")
    print("="*70)
    resultado2 = consultas.consulta_patrones_desarrollo()
    print(resultado2)
    
    print("\n" + "="*70)
    print("📁 CONSULTA 3: PROYECTOS RELACIONADOS CON OPENCV")
    print("="*70)
    resultado3 = consultas.consulta_proyectos_relacionados('opencv')
    print(resultado3)
    
    print("\n" + "="*70)
    print("📈 CONSULTA 4: EVOLUCIÓN TEMPORAL")
    print("="*70)
    resultado4 = consultas.consulta_evolucion_temporal()
    print(resultado4)
    
    return consultas

if __name__ == "__main__":
    # Ejecutar pruebas completas
    sistema_consultas = test_consultas_inteligentes()
