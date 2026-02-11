# real_memory_connector.py - Conector REAL para la estructura de Lucas
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class LucasConcept:
    name: str
    strength: float
    usage_count: int
    category: str
    file_path: str
    context: str

@dataclass
class LucasRelationship:
    concept_a: str
    concept_b: str
    strength: float
    context: str

class RealLucasMemory:
    """Conector REAL para la memoria de Lucas con su estructura actual"""
    
    def __init__(self, db_path: str = "database/ianae_memory.db"):
        self.db_path = db_path
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Conectar a la base de datos real"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"✅ Conectado a memoria real: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Error conectando: {e}")
            raise
    
    def get_memory_stats(self) -> Dict:
        """Estadísticas REALES de tu memoria"""
        try:
            cursor = self.connection.cursor()
            
            # Contar conceptos
            cursor.execute("SELECT COUNT(*) FROM concepts")
            concept_count = cursor.fetchone()[0]
            
            # Contar relaciones
            cursor.execute("SELECT COUNT(*) FROM relationships")
            relation_count = cursor.fetchone()[0]
            
            # Contar insights
            cursor.execute("SELECT COUNT(*) FROM insights")
            insight_count = cursor.fetchone()[0]
            
            # Categorías más usadas
            cursor.execute("""
                SELECT category, COUNT(*) as count, SUM(usage_count) as total_usage
                FROM concepts 
                WHERE category IS NOT NULL
                GROUP BY category 
                ORDER BY total_usage DESC 
                LIMIT 5
            """)
            categories_data = cursor.fetchall()
            top_categories = {row[0]: {"count": row[1], "usage": row[2]} for row in categories_data}
            
            return {
                "concepts": concept_count,
                "relations": relation_count,
                "insights": insight_count,
                "top_categories": top_categories,
                "status": "connected"
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo stats reales: {e}")
            return {"error": str(e), "status": "error"}
    
    def search_concepts(self, query: str, limit: int = 10) -> List[LucasConcept]:
        """Buscar conceptos REALES - BÚSQUEDA MEJORADA"""
        try:
            cursor = self.connection.cursor()
            
            # Búsqueda más agresiva y flexible
            query_lower = query.lower()
            
            # 1. Búsqueda exacta (máxima prioridad)
            cursor.execute("""
                SELECT name, strength, usage_count, category, file_path, 
                       COALESCE(file_path, '') as context, 3 as priority
                FROM concepts 
                WHERE LOWER(name) = ?
                UNION ALL
                -- 2. Búsqueda que empiece con el término
                SELECT name, strength, usage_count, category, file_path, 
                       COALESCE(file_path, '') as context, 2 as priority
                FROM concepts 
                WHERE LOWER(name) LIKE ?
                UNION ALL
                -- 3. Búsqueda que contenga el término
                SELECT name, strength, usage_count, category, file_path, 
                       COALESCE(file_path, '') as context, 1 as priority
                FROM concepts 
                WHERE (LOWER(name) LIKE ? OR 
                       LOWER(category) LIKE ? OR 
                       LOWER(file_path) LIKE ?)
                ORDER BY priority DESC, strength DESC, usage_count DESC
                LIMIT ?
            """, (query_lower, f"{query_lower}%", f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%", limit))
            
            results = []
            seen_names = set()
            
            for row in cursor.fetchall():
                if row['name'] not in seen_names:  # Evitar duplicados
                    seen_names.add(row['name'])
                    results.append(LucasConcept(
                        name=row['name'],
                        strength=float(row['strength'] or 0.0),
                        usage_count=int(row['usage_count'] or 0),
                        category=row['category'] or 'general',
                        file_path=row['file_path'] or '',
                        context=row['context'] or ''
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando conceptos: {e}")
            return []
    
    def get_related_concepts(self, concept_name: str, limit: int = 5) -> List[Tuple[str, float, str]]:
        """Obtener conceptos REALMENTE relacionados"""
        try:
            cursor = self.connection.cursor()
            
            # Buscar relaciones donde concept_name está involucrado
            cursor.execute("""
                SELECT concept_b, strength, context FROM relationships 
                WHERE concept_a = ? 
                ORDER BY strength DESC 
                LIMIT ?
            """, (concept_name, limit))
            
            outgoing = cursor.fetchall()
            
            # Buscar relaciones inversas
            cursor.execute("""
                SELECT concept_a, strength, context FROM relationships 
                WHERE concept_b = ? 
                ORDER BY strength DESC 
                LIMIT ?
            """, (concept_name, limit))
            
            incoming = cursor.fetchall()
            
            # Combinar y eliminar duplicados
            all_relations = {}
            for concept, strength, context in outgoing + incoming:
                if concept not in all_relations or all_relations[concept][0] < strength:
                    all_relations[concept] = (strength, context)
            
            return [(concept, strength, context) for concept, (strength, context) in 
                   sorted(all_relations.items(), key=lambda x: x[1][0], reverse=True)[:limit]]
            
        except Exception as e:
            logger.error(f"Error obteniendo relacionados reales: {e}")
            return []
    
    def get_insights_for_query(self, query: str, limit: int = 3) -> List[Dict]:
        """Obtener insights REALES relacionados con la query"""
        try:
            cursor = self.connection.cursor()
            
            search_query = f"%{query.lower()}%"
            
            cursor.execute("""
                SELECT concepts, insight_text, strength, file_reference
                FROM insights 
                WHERE LOWER(insight_text) LIKE ? 
                   OR LOWER(concepts) LIKE ?
                ORDER BY strength DESC
                LIMIT ?
            """, (search_query, search_query, limit))
            
            insights = []
            for row in cursor.fetchall():
                insights.append({
                    "concepts": row['concepts'],
                    "text": row['insight_text'],
                    "strength": row['strength'],
                    "source": row['file_reference'] or 'general'
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error obteniendo insights: {e}")
            return []
    
    def get_context_for_query(self, query: str) -> Dict:
        """Obtener contexto REAL completo para una query"""
        # Buscar conceptos relevantes
        concepts = self.search_concepts(query, limit=5)
        
        # Buscar insights relevantes
        insights = self.get_insights_for_query(query, limit=2)
        
        context = {
            "found_concepts": [],
            "related_patterns": [],
            "insights": insights,
            "categories": set(),
            "context_summary": ""
        }
        
        if not concepts:
            context["context_summary"] = f"No encontré conceptos específicos sobre '{query}' en tu memoria personal."
            return context
        
        # Procesar conceptos encontrados
        for concept in concepts:
            context["found_concepts"].append({
                "name": concept.name,
                "category": concept.category,
                "strength": concept.strength,
                "usage_count": concept.usage_count,
                "context": concept.context[:200] + "..." if len(concept.context) > 200 else concept.context
            })
            context["categories"].add(concept.category)
            
            # Buscar relacionados para cada concepto
            related = self.get_related_concepts(concept.name, limit=2)
            for rel_name, rel_strength, rel_context in related:
                context["related_patterns"].append({
                    "from": concept.name,
                    "to": rel_name,
                    "strength": rel_strength,
                    "context": rel_context[:100] + "..." if len(rel_context) > 100 else rel_context
                })
        
        # Crear resumen contextual
        context["categories"] = list(context["categories"])
        context["context_summary"] = self._generate_real_context_summary(context, query)
        
        return context
    
    def _generate_real_context_summary(self, context: Dict, query: str) -> str:
        """Generar resumen REAL del contexto encontrado"""
        concepts = context["found_concepts"]
        insights = context["insights"]
        patterns = context["related_patterns"]
        
        if not concepts:
            return f"No encontré información específica sobre '{query}' en tu memoria."
        
        summary_parts = []
        
        # Conceptos encontrados
        concept_names = [c["name"] for c in concepts[:3]]
        total_usage = sum(c["usage_count"] for c in concepts)
        
        summary_parts.append(f"Encontré {len(concepts)} conceptos relacionados con '{query}': {', '.join(concept_names)}")
        
        if total_usage > 0:
            summary_parts.append(f"Has trabajado con estos conceptos {total_usage} veces en total")
        
        # Categorías principales
        if context["categories"]:
            main_categories = list(context["categories"])[:2]
            summary_parts.append(f"Principalmente en: {', '.join(main_categories)}")
        
        # Insights
        if insights:
            summary_parts.append(f"Tengo {len(insights)} insights previos sobre este tema")
        
        # Patrones
        if patterns:
            summary_parts.append(f"Detecté {len(patterns)} conexiones con otros conceptos")
        
        return ". ".join(summary_parts) + "."
    
    def get_top_concepts(self, limit: int = 10) -> List[Dict]:
        """Obtener tus conceptos más importantes"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT name, category, strength, usage_count
                FROM concepts 
                ORDER BY strength DESC, usage_count DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "name": row['name'],
                    "category": row['category'],
                    "strength": row['strength'],
                    "usage_count": row['usage_count']
                }
                for row in cursor.fetchall()
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo top concepts: {e}")
            return []
    
    def close(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Desconectado de memoria real")

# Instancia global
_real_memory = None

def get_real_memory() -> RealLucasMemory:
    """Obtener instancia de memoria real"""
    global _real_memory
    if _real_memory is None:
        _real_memory = RealLucasMemory()
    return _real_memory