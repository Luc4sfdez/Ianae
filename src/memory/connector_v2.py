# memory_connector.py - Conexión con memoria de Lucas
import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from config import config
import logging

logger = logging.getLogger(__name__)

@dataclass
class Concepto:
    id: int
    concepto: str
    categoria: str
    contexto: str
    activaciones: int
    ultima_activacion: str

@dataclass
class Relacion:
    concepto1: str
    concepto2: str
    peso: float
    tipo: str

class LucasMemoryConnector:
    """Conector para acceder a la memoria personal de Lucas"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establecer conexión con la base de datos"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Para acceso por nombre
            logger.info(f"✅ Conectado a memoria: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Error conectando a memoria: {e}")
            raise
    
    def get_memory_stats(self) -> Dict:
        """Obtener estadísticas de la memoria"""
        try:
            cursor = self.connection.cursor()
            
            # Contar conceptos
            cursor.execute("SELECT COUNT(*) FROM conceptos")
            concept_count = cursor.fetchone()[0]
            
            # Contar relaciones (aproximado)
            cursor.execute("SELECT COUNT(*) FROM relaciones")
            relation_count = cursor.fetchone()[0]
            
            # Categorías más populares
            cursor.execute("""
                SELECT categoria, COUNT(*) as count 
                FROM conceptos 
                GROUP BY categoria 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_categories = dict(cursor.fetchall())
            
            return {
                "concepts": concept_count,
                "relations": relation_count,
                "top_categories": top_categories,
                "status": "connected"
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return {"error": str(e), "status": "error"}
    
    def search_concepts(self, query: str, limit: int = 10) -> List[Concepto]:
        """Buscar conceptos relevantes para una consulta"""
        try:
            cursor = self.connection.cursor()
            
            # Búsqueda por múltiples campos
            search_query = f"%{query.lower()}%"
            
            cursor.execute("""
                SELECT id, concepto, categoria, contexto, activaciones, ultima_activacion
                FROM conceptos 
                WHERE LOWER(concepto) LIKE ? 
                   OR LOWER(contexto) LIKE ?
                   OR LOWER(categoria) LIKE ?
                ORDER BY activaciones DESC, LENGTH(concepto) ASC
                LIMIT ?
            """, (search_query, search_query, search_query, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(Concepto(
                    id=row['id'],
                    concepto=row['concepto'],
                    categoria=row['categoria'],
                    contexto=row['contexto'] or '',
                    activaciones=row['activaciones'] or 0,
                    ultima_activacion=row['ultima_activacion'] or ''
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando conceptos: {e}")
            return []
    
    def get_related_concepts(self, concepto: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Obtener conceptos relacionados"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT concepto2, peso FROM relaciones 
                WHERE concepto1 = ? 
                ORDER BY peso DESC 
                LIMIT ?
            """, (concepto, limit))
            
            related = cursor.fetchall()
            
            # También buscar relaciones inversas
            cursor.execute("""
                SELECT concepto1, peso FROM relaciones 
                WHERE concepto2 = ? 
                ORDER BY peso DESC 
                LIMIT ?
            """, (concepto, limit))
            
            related.extend(cursor.fetchall())
            
            # Eliminar duplicados y ordenar
            unique_related = {}
            for concept, weight in related:
                if concept not in unique_related or unique_related[concept] < weight:
                    unique_related[concept] = weight
            
            return sorted(unique_related.items(), key=lambda x: x[1], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Error obteniendo relacionados: {e}")
            return []
    
    def get_context_for_query(self, query: str) -> Dict:
        """Obtener contexto enriquecido para una consulta"""
        # Buscar conceptos relevantes
        concepts = self.search_concepts(query, limit=5)
        
        context = {
            "found_concepts": [],
            "related_patterns": [],
            "categories": set(),
            "context_summary": ""
        }
        
        if not concepts:
            return context
        
        # Procesar conceptos encontrados
        for concept in concepts:
            context["found_concepts"].append({
                "name": concept.concepto,
                "category": concept.categoria,
                "activations": concept.activaciones,
                "context": concept.contexto[:200] + "..." if len(concept.contexto) > 200 else concept.contexto
            })
            context["categories"].add(concept.categoria)
            
            # Buscar relacionados
            related = self.get_related_concepts(concept.concepto, limit=3)
            if related:
                context["related_patterns"].extend([
                    {"from": concept.concepto, "to": rel[0], "strength": rel[1]} 
                    for rel in related
                ])
        
        # Crear resumen de contexto
        context["categories"] = list(context["categories"])
        context["context_summary"] = self._generate_context_summary(context)
        
        return context
    
    def _generate_context_summary(self, context: Dict) -> str:
        """Generar resumen textual del contexto"""
        if not context["found_concepts"]:
            return "No se encontró contexto específico en tu memoria."
        
        concepts_names = [c["name"] for c in context["found_concepts"]]
        categories = context["categories"]
        
        summary = f"Encontré {len(concepts_names)} conceptos relacionados en tu memoria: "
        summary += ", ".join(concepts_names[:3])
        
        if len(concepts_names) > 3:
            summary += f" y {len(concepts_names) - 3} más"
        
        if categories:
            summary += f". Principalmente en categorías: {', '.join(categories[:2])}"
        
        if context["related_patterns"]:
            strong_patterns = [p for p in context["related_patterns"] if p["strength"] > 0.5]
            if strong_patterns:
                summary += f". Detecté {len(strong_patterns)} conexiones fuertes con otros conceptos"
        
        return summary + "."
    
    def update_concept_activation(self, concepto: str):
        """Actualizar contador de activación de un concepto"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE conceptos 
                SET activaciones = activaciones + 1,
                    ultima_activacion = datetime('now')
                WHERE concepto = ?
            """, (concepto,))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error actualizando activación: {e}")
    
    def add_new_concept(self, concepto: str, categoria: str, contexto: str = ""):
        """Añadir nuevo concepto a la memoria"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO conceptos (concepto, categoria, contexto, activaciones, ultima_activacion)
                VALUES (?, ?, ?, 1, datetime('now'))
            """, (concepto, categoria, contexto))
            self.connection.commit()
            logger.info(f"➕ Nuevo concepto añadido: {concepto}")
        except Exception as e:
            logger.error(f"Error añadiendo concepto: {e}")
    
    def get_lucas_patterns(self) -> Dict:
        """Obtener patrones específicos de Lucas"""
        try:
            cursor = self.connection.cursor()
            
            # Conceptos más activados (patrones favoritos)
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
            
            return {
                "favorite_concepts": [
                    {"name": row[0], "category": row[1], "activations": row[2]} 
                    for row in top_concepts
                ],
                "preferred_categories": [
                    {"category": row[0], "concept_count": row[1], "total_activations": row[2]}
                    for row in top_categories
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo patrones Lucas: {e}")
            return {}
    
    def close(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Desconectado de memoria")

# Singleton instance
_memory_instance = None

def get_memory_connector() -> LucasMemoryConnector:
    """Obtener instancia singleton del conector de memoria"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = LucasMemoryConnector()
    return _memory_instance