 
# lucas_memory.py - Lógica específica de memoria personal de Lucas
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sqlite3
import json
import logging
from datetime import datetime
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

@dataclass
class LucasPattern:
    """Patrón específico de Lucas detectado en su memoria"""
    pattern_type: str
    description: str
    confidence: float
    examples: List[str]
    categories: List[str]

@dataclass
class ConceptAnalysis:
    """Análisis profundo de un concepto en el contexto de Lucas"""
    concepto: str
    categoria: str
    relevancia_lucas: float
    conexiones_fuertes: List[Tuple[str, float]]
    contexto_personalizado: str
    patrones_detectados: List[str]

class LucasMemoryAnalyzer:
    """Analizador específico para la memoria personal de Lucas"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self._connect()
        
        # Patrones conocidos de Lucas
        self.lucas_tech_stack = [
            'Python', 'VBA', 'Excel', 'OpenCV', 'Docker', 'FastAPI',
            'SQLite', 'Automatizacion', 'LM_Studio'
        ]
        
        self.lucas_projects = [
            'Tacografos', 'IANAE', 'RAG_System', 'Memory_System',
            'Hollow_Earth', 'ThreeJS'
        ]
        
        self.lucas_superpowers = [
            'TOC_TDAH', 'Superpoder_Patrones', 'Deteccion', 'Optimizacion'
        ]
        
    def _connect(self):
        """Conectar a la base de datos"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Error conectando a memoria Lucas: {e}")
            
    def analyze_lucas_context(self, query: str) -> Dict:
        """Análisis contextual específico para Lucas"""
        
        # Determinar tipo de consulta
        query_type = self._classify_query_type(query)
        
        # Buscar conceptos relevantes
        relevant_concepts = self._find_relevant_concepts(query)
        
        # Detectar patrones de Lucas
        lucas_patterns = self._detect_lucas_patterns(query, relevant_concepts)
        
        # Generar contexto personalizado
        personalized_context = self._generate_lucas_context(
            query, query_type, relevant_concepts, lucas_patterns
        )
        
        return {
            "query_type": query_type,
            "relevant_concepts": relevant_concepts,
            "lucas_patterns": lucas_patterns,
            "personalized_context": personalized_context,
            "confidence": self._calculate_context_confidence(relevant_concepts)
        }
    
    def _classify_query_type(self, query: str) -> str:
        """Clasificar tipo de consulta según patrones de Lucas"""
        query_lower = query.lower()
        
        # Patrones técnicos
        if any(tech.lower() in query_lower for tech in self.lucas_tech_stack):
            if any(word in query_lower for word in ['optimizar', 'mejorar', 'acelerar']):
                return "optimizacion_tecnica"
            elif any(word in query_lower for word in ['error', 'problema', 'falla']):
                return "troubleshooting_tecnico"
            else:
                return "consulta_tecnica"
        
        # Patrones de proyectos
        if any(proj.lower() in query_lower for proj in self.lucas_projects):
            return "consulta_proyecto"
        
        # Patrones de automatización
        if any(word in query_lower for word in ['automatizar', 'automatizacion', 'script']):
            return "automatizacion"
        
        # Patrones creativos
        if any(word in query_lower for word in ['idea', 'creativo', 'innovar', 'crear']):
            return "exploracion_creativa"
        
        # Patrones de análisis
        if any(word in query_lower for word in ['patron', 'conexion', 'relacion', 'analizar']):
            return "analisis_patrones"
        
        return "consulta_general"
    
    def _find_relevant_concepts(self, query: str, limit: int = 8) -> List[ConceptAnalysis]:
        """Encontrar conceptos relevantes con análisis específico para Lucas"""
        cursor = self.connection.cursor()
        
        # Extraer palabras clave de la consulta
        keywords = self._extract_keywords(query)
        
        # Búsqueda en múltiples campos con ponderación
        search_results = []
        
        for keyword in keywords[:3]:  # Top 3 keywords
            cursor.execute("""
                SELECT concepto, categoria, contexto, activaciones,
                       CASE 
                           WHEN LOWER(concepto) LIKE ? THEN 1.0
                           WHEN LOWER(contexto) LIKE ? THEN 0.7
                           WHEN LOWER(categoria) LIKE ? THEN 0.5
                           ELSE 0.3
                       END as relevance_score
                FROM conceptos 
                WHERE LOWER(concepto) LIKE ? 
                   OR LOWER(contexto) LIKE ?
                   OR LOWER(categoria) LIKE ?
                ORDER BY relevance_score DESC, activaciones DESC
                LIMIT ?
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%',
                  f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))
            
            search_results.extend(cursor.fetchall())
        
        # Procesar y analizar resultados
        analyzed_concepts = []
        seen_concepts = set()
        
        for row in search_results:
            if row['concepto'] in seen_concepts:
                continue
            seen_concepts.add(row['concepto'])
            
            # Análisis específico para Lucas
            analysis = self._analyze_concept_for_lucas(row)
            if analysis.relevancia_lucas > 0.2:  # Filtro de relevancia
                analyzed_concepts.append(analysis)
        
        # Ordenar por relevancia para Lucas
        analyzed_concepts.sort(key=lambda x: x.relevancia_lucas, reverse=True)
        
        return analyzed_concepts[:limit]
    
    def _analyze_concept_for_lucas(self, concept_row) -> ConceptAnalysis:
        """Análisis profundo de un concepto específico para Lucas"""
        concepto = concept_row['concepto']
        categoria = concept_row['categoria']
        contexto = concept_row['contexto'] or ''
        activaciones = concept_row['activaciones'] or 0
        
        # Calcular relevancia específica para Lucas
        relevancia = self._calculate_lucas_relevance(concepto, categoria, contexto, activaciones)
        
        # Encontrar conexiones fuertes
        conexiones = self._get_strong_connections(concepto)
        
        # Contexto personalizado
        contexto_personal = self._generate_personal_context(concepto, categoria, contexto)
        
        # Detectar patrones
        patrones = self._detect_concept_patterns(concepto, categoria, contexto)
        
        return ConceptAnalysis(
            concepto=concepto,
            categoria=categoria,
            relevancia_lucas=relevancia,
            conexiones_fuertes=conexiones,
            contexto_personalizado=contexto_personal,
            patrones_detectados=patrones
        )
    
    def _calculate_lucas_relevance(self, concepto: str, categoria: str, contexto: str, activaciones: int) -> float:
        """Calcular relevancia específica para Lucas"""
        score = 0.0
        
        # Boost por tech stack de Lucas
        if concepto in self.lucas_tech_stack:
            score += 0.4
        
        # Boost por proyectos de Lucas
        if concepto in self.lucas_projects:
            score += 0.5
        
        # Boost por superpoderes
        if concepto in self.lucas_superpowers:
            score += 0.3
        
        # Boost por categorías importantes para Lucas
        categoria_boost = {
            'tecnologias': 0.3,
            'proyectos': 0.4,
            'lucas_personal': 0.5,
            'herramientas': 0.25,
            'automatizacion': 0.35
        }
        score += categoria_boost.get(categoria, 0.1)
        
        # Boost por activaciones (uso frecuente)
        if activaciones > 10:
            score += 0.2
        elif activaciones > 5:
            score += 0.1
        
        # Boost por palabras clave en contexto
        lucas_keywords = ['automatizacion', 'optimizacion', 'patron', 'deteccion', 'script']
        for keyword in lucas_keywords:
            if keyword.lower() in contexto.lower():
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_strong_connections(self, concepto: str, min_weight: float = 0.3) -> List[Tuple[str, float]]:
        """Obtener conexiones fuertes de un concepto"""
        cursor = self.connection.cursor()
        
        try:
            # Buscar conexiones salientes
            cursor.execute("""
                SELECT concepto2, peso FROM relaciones 
                WHERE concepto1 = ? AND peso >= ?
                ORDER BY peso DESC LIMIT 5
            """, (concepto, min_weight))
            
            outgoing = cursor.fetchall()
            
            # Buscar conexiones entrantes
            cursor.execute("""
                SELECT concepto1, peso FROM relaciones 
                WHERE concepto2 = ? AND peso >= ?
                ORDER BY peso DESC LIMIT 5
            """, (concepto, min_weight))
            
            incoming = cursor.fetchall()
            
            # Combinar y eliminar duplicados
            all_connections = {}
            for conn, weight in outgoing + incoming:
                if conn not in all_connections or all_connections[conn] < weight:
                    all_connections[conn] = weight
            
            return sorted(all_connections.items(), key=lambda x: x[1], reverse=True)[:5]
            
        except Exception as e:
            logger.error(f"Error obteniendo conexiones: {e}")
            return []
    
    def _generate_personal_context(self, concepto: str, categoria: str, contexto: str) -> str:
        """Generar contexto personalizado para Lucas"""
        personal_context = []
        
        # Identificar relación personal
        if concepto in self.lucas_tech_stack:
            personal_context.append(f"Es parte de tu stack técnico principal")
        
        if concepto in self.lucas_projects:
            personal_context.append(f"Uno de tus proyectos importantes")
        
        if concepto in self.lucas_superpowers:
            personal_context.append(f"Relacionado con tus superpoderes cognitivos")
        
        # Análisis de contexto original
        if 'optimizacion' in contexto.lower():
            personal_context.append("Área donde sueles buscar optimizaciones")
        
        if 'automatizacion' in contexto.lower():
            personal_context.append("Candidato para automatización")
        
        # Contexto por categoría
        categoria_context = {
            'tecnologias': "Herramienta técnica que dominas",
            'proyectos': "Proyecto en tu portfolio",
            'lucas_personal': "Aspecto personal/cognitivo",
            'herramientas': "Herramienta de trabajo habitual"
        }
        
        if categoria in categoria_context:
            personal_context.append(categoria_context[categoria])
        
        if personal_context:
            return ". ".join(personal_context) + "."
        else:
            return contexto[:150] + "..." if len(contexto) > 150 else contexto
    
    def _detect_concept_patterns(self, concepto: str, categoria: str, contexto: str) -> List[str]:
        """Detectar patrones específicos en el concepto"""
        patterns = []
        
        # Patrones técnicos
        if any(tech in concepto for tech in ['Python', 'OpenCV', 'Excel']):
            patterns.append("tecnologia_core")
        
        # Patrones de automatización
        if any(word in contexto.lower() for word in ['script', 'automatizacion', 'proceso']):
            patterns.append("automatizable")
        
        # Patrones de optimización
        if any(word in contexto.lower() for word in ['optimizacion', 'mejorar', 'acelerar']):
            patterns.append("optimizable")
        
        # Patrones de detección
        if any(word in contexto.lower() for word in ['deteccion', 'reconocimiento', 'identificar']):
            patterns.append("deteccion_patterns")
        
        return patterns
    
    def _detect_lucas_patterns(self, query: str, concepts: List[ConceptAnalysis]) -> List[LucasPattern]:
        """Detectar patrones específicos de Lucas en la consulta y conceptos"""
        patterns = []
        
        # Patrón: Combo Python + OpenCV
        python_concepts = [c for c in concepts if 'python' in c.concepto.lower()]
        opencv_concepts = [c for c in concepts if 'opencv' in c.concepto.lower()]
        
        if python_concepts and opencv_concepts:
            patterns.append(LucasPattern(
                pattern_type="python_opencv_combo",
                description="Combinación típica Python + OpenCV en tus proyectos",
                confidence=0.8,
                examples=["Tacógrafos", "Detección de círculos"],
                categories=["tecnologias", "proyectos"]
            ))
        
        # Patrón: Automatización con Excel
        excel_concepts = [c for c in concepts if 'excel' in c.concepto.lower()]
        auto_concepts = [c for c in concepts if 'automatizacion' in c.concepto.lower()]
        
        if excel_concepts and any('automatizacion' in query.lower() for q in [query]):
            patterns.append(LucasPattern(
                pattern_type="excel_automation",
                description="Patrón de automatización con Excel/VBA",
                confidence=0.7,
                examples=["Scripts VBA", "Macros Excel"],
                categories=["automatizacion", "herramientas"]
            ))
        
        # Patrón: Optimización técnica
        if any(word in query.lower() for word in ['optimizar', 'mejorar', 'acelerar']):
            patterns.append(LucasPattern(
                pattern_type="optimization_focus",
                description="Enfoque en optimización (patrón TOC)",
                confidence=0.9,
                examples=["Optimización de algoritmos", "Mejora de performance"],
                categories=["superpoderes", "optimizacion"]
            ))
        
        return patterns
    
    def _generate_lucas_context(self, query: str, query_type: str, concepts: List[ConceptAnalysis], patterns: List[LucasPattern]) -> str:
        """Generar contexto personalizado para Lucas"""
        context_parts = []
        
        # Introducción basada en tipo de consulta
        intro_templates = {
            "optimizacion_tecnica": "Basándome en tu patrón de optimización técnica",
            "consulta_proyecto": "Revisando tu historial de proyectos",
            "automatizacion": "Considerando tu enfoque de automatización",
            "analisis_patrones": "Aplicando tu superpoder de detección de patrones",
            "consulta_tecnica": "Usando tu stack técnico habitual",
            "exploracion_creativa": "Conectando con tu lado creativo",
            "consulta_general": "Basándome en tu memoria personal"
        }
        
        intro = intro_templates.get(query_type, "Basándome en tu memoria personal")
        context_parts.append(intro)
        
        # Conceptos más relevantes
        if concepts:
            top_concepts = [c.concepto for c in concepts[:3]]
            context_parts.append(f"encontré información sobre: {', '.join(top_concepts)}")
        
        # Patrones detectados
        if patterns:
            pattern_descriptions = [p.description for p in patterns[:2]]
            context_parts.append(f"Detecté patrones típicos tuyos: {'; '.join(pattern_descriptions)}")
        
        # Conexiones específicas
        strong_connections = []
        for concept in concepts[:2]:
            if concept.conexiones_fuertes:
                conn_names = [conn[0] for conn in concept.conexiones_fuertes[:2]]
                strong_connections.extend(conn_names)
        
        if strong_connections:
            context_parts.append(f"con conexiones a: {', '.join(set(strong_connections[:3]))}")
        
        return ". ".join(context_parts) + "."
    
    def _calculate_context_confidence(self, concepts: List[ConceptAnalysis]) -> float:
        """Calcular confianza del contexto generado"""
        if not concepts:
            return 0.1
        
        # Promedio de relevancia de conceptos encontrados
        avg_relevance = sum(c.relevancia_lucas for c in concepts) / len(concepts)
        
        # Boost por cantidad de conceptos
        quantity_boost = min(len(concepts) * 0.1, 0.3)
        
        # Boost por conexiones fuertes
        connection_boost = sum(0.05 for c in concepts if c.conexiones_fuertes) 
        
        confidence = avg_relevance + quantity_boost + connection_boost
        
        return min(confidence, 1.0)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extraer palabras clave relevantes"""
        # Limpiar y tokenizar
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        # Filtrar stop words
        stop_words = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 
                     'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'como', 'pero', 'muy'}
        
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Priorizar palabras técnicas conocidas
        tech_priority = []
        other_keywords = []
        
        for keyword in keywords:
            if any(tech.lower() == keyword for tech in self.lucas_tech_stack + self.lucas_projects):
                tech_priority.append(keyword)
            else:
                other_keywords.append(keyword)
        
        return tech_priority + other_keywords[:5]  # Tech keywords first
    
    def get_lucas_insights(self) -> Dict:
        """Obtener insights específicos sobre los patrones de Lucas"""
        cursor = self.connection.cursor()
        
        try:
            # Top conceptos por activaciones
            cursor.execute("""
                SELECT concepto, categoria, activaciones 
                FROM conceptos 
                ORDER BY activaciones DESC 
                LIMIT 10
            """)
            top_concepts = cursor.fetchall()
            
            # Categorías más utilizadas
            cursor.execute("""
                SELECT categoria, COUNT(*) as count, SUM(activaciones) as total_activations
                FROM conceptos 
                GROUP BY categoria 
                ORDER BY total_activations DESC 
                LIMIT 5
            """)
            top_categories = cursor.fetchall()
            
            # Conexiones más fuertes
            cursor.execute("""
                SELECT concepto1, concepto2, peso 
                FROM relaciones 
                ORDER BY peso DESC 
                LIMIT 10
            """)
            strongest_connections = cursor.fetchall()
            
            return {
                "favorite_concepts": [
                    {"name": row[0], "category": row[1], "usage": row[2]}
                    for row in top_concepts
                ],
                "preferred_categories": [
                    {"category": row[0], "concept_count": row[1], "total_usage": row[2]}
                    for row in top_categories
                ],
                "strongest_patterns": [
                    {"from": row[0], "to": row[1], "strength": row[2]}
                    for row in strongest_connections
                ],
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo insights: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()

# Función de conveniencia para integración
def analyze_for_lucas(db_path: str, query: str) -> Dict:
    """Función de conveniencia para análisis específico de Lucas"""
    analyzer = LucasMemoryAnalyzer(db_path)
    try:
        return analyzer.analyze_lucas_context(query)
    finally:
        analyzer.close()

def get_lucas_insights(db_path: str) -> Dict:
    """Función de conveniencia para obtener insights de Lucas"""
    analyzer = LucasMemoryAnalyzer(db_path)
    try:
        return analyzer.get_lucas_insights()
    finally:
        analyzer.close()