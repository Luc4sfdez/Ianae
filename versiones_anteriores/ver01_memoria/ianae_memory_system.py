# ianae_memory_system.py - Sistema de memoria inteligente para IANAE
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import pickle
from typing import Dict, List, Optional, Tuple
import numpy as np

class IANAEMemorySystem:
    """
    Sistema de memoria inteligente que gestiona contexto sin agotarlo
    """
    
    def __init__(self, memory_path="IANAE_MEMORY"):
        """Inicializa el sistema de memoria inteligente de IANAE.
        
        Args:
            memory_path (str): Ruta base para almacenar los datos de memoria
            
        Attributes:
            memory_path (str): Ruta base de almacenamiento
            concept_index (dict): Índice de conceptos (nombre → ubicación)
            relationship_index (dict): Índice de relaciones
            usage_index (dict): Estadísticas de uso de conceptos
            temporal_index (dict): Índice temporal de descubrimientos
            max_context_size (int): Límite de bytes para contexto (default: 3500)
            priority_concepts (set): Conceptos que siempre permanecen en memoria
            db_path (str): Ruta a la base de datos SQLite
        """
        self.memory_path = memory_path
        self.ensure_directories()
        
        # Índices ligeros en memoria (solo lo esencial)
        self.concept_index = {}      # concepto → ubicación física
        self.relationship_index = {} # concepto → conceptos relacionados
        self.usage_index = {}        # concepto → estadísticas de uso
        self.temporal_index = {}     # fecha → conceptos descubiertos
        
        # Configuración de contexto
        self.max_context_size = 3500  # bytes máximos para contexto
        self.priority_concepts = set()  # conceptos que siempre están en memoria
        
        # Base de datos SQLite para consultas rápidas
        self.db_path = os.path.join(memory_path, "ianae_index.db")
        self.init_database()
        
        # Cargar índices
        self.load_indices()
        
    def ensure_directories(self):
        """
        Crea la estructura de directorios necesaria
        """
        directories = [
            self.memory_path,
            os.path.join(self.memory_path, "conversations_processed"),
            os.path.join(self.memory_path, "discovery_layers"),
            os.path.join(self.memory_path, "evolution_snapshots"),
            os.path.join(self.memory_path, "indices")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def init_database(self):
        """
        Inicializa la base de datos SQLite para índices rápidos
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    name TEXT PRIMARY KEY,
                    file_path TEXT,
                    byte_start INTEGER,
                    byte_end INTEGER,
                    strength REAL,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    category TEXT,
                    created_date TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    concept_a TEXT,
                    concept_b TEXT,
                    strength REAL,
                    discovery_date TEXT,
                    context TEXT,
                    PRIMARY KEY (concept_a, concept_b)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    concepts TEXT,  -- JSON array
                    insight_text TEXT,
                    strength REAL,
                    discovery_date TEXT,
                    file_reference TEXT
                )
            ''')
            
            # Índices para consultas rápidas
            conn.execute('CREATE INDEX IF NOT EXISTS idx_concept_strength ON concepts(strength DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_relationship_strength ON relationships(strength DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_used ON concepts(last_used DESC)')
            
    def process_rag_conversations(self, conversations_database_path):
        """Procesa conversaciones del RAG para extraer conceptos técnicos.
        
        Args:
            conversations_database_path (str): Ruta a la base de datos de conversaciones
            
        Returns:
            None: Actualiza los índices internos
            
        Side Effects:
            - Procesa archivos JSON en el directorio especificado
            - Extrae conceptos técnicos y específicos de Lucas
            - Actualiza la base de datos SQLite
            - Construye índices de relaciones
            
        Example:
            >>> memory = IANAEMemorySystem()
            >>> memory.process_rag_conversations("path/to/conversations")
        """
        print("🔍 Procesando conversaciones del RAG...")
        
        # Usar directamente el path de conversations_database
        conversations_path = conversations_database_path
        
        if not os.path.exists(conversations_path):
            print(f"❌ No se encontró: {conversations_path}")
            return
            
        processed_count = 0
        concepts_extracted = 0
        
        for filename in os.listdir(conversations_path):
            if filename.endswith('.json'):
                file_path = os.path.join(conversations_path, filename)
                
                try:
                    # Procesar archivo individual
                    new_concepts = self.process_single_conversation(file_path, filename)
                    concepts_extracted += len(new_concepts)
                    processed_count += 1
                    
                    if processed_count % 50 == 0:
                        print(f"   📊 Procesados {processed_count} archivos, {concepts_extracted} conceptos extraídos")
                        
                except Exception as e:
                    print(f"   ⚠️ Error procesando {filename}: {e}")
                    
        print(f"✅ Procesamiento completado: {processed_count} conversaciones, {concepts_extracted} conceptos totales")
        
        # Construir índices finales
        self.build_relationship_index()
        self.save_indices()
        
    def process_single_conversation(self, file_path, filename):
        """
        Procesa una conversación individual extrayendo conceptos ligeros
        """
        new_concepts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Leer archivo en chunks para evitar agotar memoria
                file_size = os.path.getsize(file_path)
                
                if file_size > 50000:  # Archivos grandes (>50KB)
                    concepts = self.process_large_file(f, file_path, filename)
                else:
                    # Archivos pequeños - carga completa
                    data = json.load(f)
                    concepts = self.extract_concepts_from_data(data, file_path, filename)
                
                new_concepts.extend(concepts)
                
        except Exception as e:
            print(f"   ❌ Error en {filename}: {e}")
            
        return new_concepts
    
    def process_large_file(self, file_handle, file_path, filename):
        """
        Procesa archivos grandes en chunks para no agotar contexto
        """
        concepts = []
        
        # Estrategia: leer archivo por partes, extraer conceptos clave
        chunk_size = 8192  # 8KB chunks
        current_chunk = ""
        byte_position = 0
        
        while True:
            chunk = file_handle.read(chunk_size)
            if not chunk:
                break
                
            current_chunk += chunk
            
            # Buscar conceptos técnicos en el chunk
            chunk_concepts = self.extract_technical_concepts(
                current_chunk, file_path, byte_position
            )
            concepts.extend(chunk_concepts)
            
            byte_position += len(chunk)
            
        return concepts
    
    def extract_technical_concepts(self, text, file_path, start_byte):
        """
        Extrae conceptos técnicos específicos de un texto
        """
        concepts = []
        
        # Patrones técnicos específicos de Lucas
        technical_patterns = {
            # Python/OpenCV
            r'cv2\.\w+': 'opencv_function',
            r'np\.\w+': 'numpy_function', 
            r'pd\.\w+': 'pandas_function',
            
            # VBA
            r'Application\.\w+': 'vba_application',
            r'Worksheet\.\w+': 'vba_worksheet',
            r'Range\(\w+\)': 'vba_range',
            
            # Proyectos específicos
            r'tacógrafo[s]?': 'tacografos_project',
            r'círculo[s]?.*detec': 'circle_detection',
            r'HSV.*mask': 'hsv_processing',
            r'ROI.*detect': 'roi_detection',
            
            # Docker/Containers
            r'docker.*run': 'docker_command',
            r'dockerfile': 'docker_config',
            
            # IA/ML
            r'LM.*Studio': 'llm_local',
            r'model.*load': 'model_loading',
            r'embedding[s]?': 'embeddings'
        }
        
        import re
        
        for pattern, concept_type in technical_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                concept_text = match.group()
                byte_start = start_byte + match.start()
                byte_end = start_byte + match.end()
                
                # Crear concepto ligero
                concept = {
                    'name': concept_text.lower(),
                    'type': concept_type,
                    'file_path': file_path,
                    'byte_start': byte_start,
                    'byte_end': byte_end,
                    'strength': self.calculate_concept_strength(concept_text, text),
                    'context_snippet': text[max(0, match.start()-50):match.end()+50],
                    'discovered_date': datetime.now().isoformat()
                }
                
                concepts.append(concept)
                
        return concepts
    
    def extract_concepts_from_data(self, data, file_path, filename):
        """
        Extrae conceptos de datos JSON ya cargados
        """
        concepts = []
        
        # Convertir JSON a texto para análisis
        if isinstance(data, dict):
            text_content = json.dumps(data, ensure_ascii=False)
        else:
            text_content = str(data)
            
        # Extraer conceptos técnicos
        extracted = self.extract_technical_concepts(text_content, file_path, 0)
        concepts.extend(extracted)
        
        # Extraer conceptos de Lucas específicos
        lucas_concepts = self.extract_lucas_specific_concepts(text_content, file_path)
        concepts.extend(lucas_concepts)
        
        return concepts
    
    def extract_lucas_specific_concepts(self, text, file_path):
        """
        Extrae conceptos específicos del universo de Lucas
        """
        concepts = []
        
        # Conceptos específicos de Lucas
        lucas_keywords = {
            # Ubicación
            'novelda': 'lucas_location',
            'alicante': 'lucas_location',
            
            # Hardware
            'i9-10900kf': 'lucas_hardware',
            'rtx3060': 'lucas_hardware',
            '128gb': 'lucas_hardware',
            
            # Proyectos
            'hollow earth': 'lucas_project',
            'vba2python': 'lucas_project', 
            'rag system': 'lucas_project',
            
            # Patrones mentales
            'toc': 'lucas_cognitive',
            'tdah': 'lucas_cognitive',
            'patrón': 'pattern_recognition',
            'automati': 'automation_focus',
            'optimiz': 'optimization_focus'
        }
        
        text_lower = text.lower()
        
        for keyword, concept_type in lucas_keywords.items():
            if keyword in text_lower:
                # Encontrar posiciones
                import re
                matches = re.finditer(re.escape(keyword), text_lower)
                
                for match in matches:
                    concept = {
                        'name': keyword,
                        'type': concept_type,
                        'file_path': file_path,
                        'byte_start': match.start(),
                        'byte_end': match.end(),
                        'strength': 0.8,  # Alta relevancia para conceptos de Lucas
                        'context_snippet': text[max(0, match.start()-30):match.end()+30],
                        'discovered_date': datetime.now().isoformat()
                    }
                    
                    concepts.append(concept)
                    
        return concepts
    
    def calculate_concept_strength(self, concept_text, context):
        """
        Calcula la fuerza/relevancia de un concepto en su contexto
        """
        strength = 0.5  # Base
        
        # Factores que aumentan la fuerza
        if len(concept_text) > 3:
            strength += 0.1
            
        # Si aparece múltiples veces en el contexto
        occurrences = context.lower().count(concept_text.lower())
        strength += min(0.3, occurrences * 0.05)
        
        # Si está en mayúsculas (probablemente importante)
        if concept_text.isupper():
            strength += 0.2
            
        # Si contiene números (específico técnico)
        if any(c.isdigit() for c in concept_text):
            strength += 0.1
            
        return min(1.0, strength)
    
    def store_concept_in_db(self, concept):
        """
        Almacena un concepto en la base de datos SQLite
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO concepts 
                (name, file_path, byte_start, byte_end, strength, last_used, usage_count, category, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                concept['name'],
                concept['file_path'],
                concept['byte_start'],
                concept['byte_end'],
                concept['strength'],
                datetime.now().isoformat(),
                1,  # usage_count inicial
                concept['type'],
                concept['discovered_date']
            ))
    
    def build_relationship_index(self):
        """
        Construye el índice de relaciones entre conceptos
        """
        print("🔗 Construyendo índice de relaciones...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Obtener todos los conceptos
            concepts = conn.execute('SELECT name, file_path FROM concepts').fetchall()
            
            relationships_found = 0
            
            # Buscar co-ocurrencias en archivos
            file_concepts = defaultdict(list)
            for concept_name, file_path in concepts:
                file_concepts[file_path].append(concept_name)
            
            # Calcular relaciones por co-ocurrencia
            for file_path, file_concept_list in file_concepts.items():
                if len(file_concept_list) > 1:
                    # Crear relaciones entre conceptos del mismo archivo
                    for i, concept_a in enumerate(file_concept_list):
                        for concept_b in file_concept_list[i+1:]:
                            # Calcular fuerza de relación
                            strength = self.calculate_relationship_strength(
                                concept_a, concept_b, file_path
                            )
                            
                            if strength > 0.3:  # Solo relaciones significativas
                                self.store_relationship(concept_a, concept_b, strength, file_path)
                                relationships_found += 1
                                
        print(f"✅ Índice de relaciones construido: {relationships_found} relaciones")
    
    def calculate_relationship_strength(self, concept_a, concept_b, file_path):
        """
        Calcula la fuerza de relación entre dos conceptos
        """
        # Factores para calcular fuerza de relación
        base_strength = 0.4
        
        # Si ambos son del mismo tipo técnico
        with sqlite3.connect(self.db_path) as conn:
            types = conn.execute('''
                SELECT category FROM concepts 
                WHERE name IN (?, ?) AND file_path = ?
            ''', (concept_a, concept_b, file_path)).fetchall()
            
            if len(types) == 2 and types[0][0] == types[1][0]:
                base_strength += 0.2  # Mismo tipo técnico
                
        # Si son conceptos específicos de Lucas
        lucas_types = ['lucas_location', 'lucas_hardware', 'lucas_project', 'lucas_cognitive']
        if any(t in str(types) for t in lucas_types):
            base_strength += 0.3
            
        return min(1.0, base_strength)
    
    def store_relationship(self, concept_a, concept_b, strength, file_context):
        """
        Almacena una relación en la base de datos
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO relationships 
                (concept_a, concept_b, strength, discovery_date, context)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                concept_a, concept_b, strength,
                datetime.now().isoformat(),
                file_context
            ))
    
    def smart_query(self, query_concept, max_context_bytes=3000):
        """
        Consulta inteligente que respeta límites de contexto
        """
        result = {
            'concept_info': None,
            'related_concepts': [],
            'context_snippets': [],
            'total_context_size': 0
        }
        
        # 1. Información básica del concepto (siempre ligera)
        concept_info = self.get_concept_info(query_concept)
        if not concept_info:
            return result
            
        result['concept_info'] = concept_info
        current_size = len(json.dumps(concept_info))
        
        # 2. Conceptos relacionados (ligeros)
        if current_size < max_context_bytes * 0.3:  # Usar solo 30% para relaciones
            related = self.get_related_concepts(query_concept, limit=5)
            result['related_concepts'] = related
            current_size += len(json.dumps(related))
        
        # 3. Snippets de contexto (si queda espacio)
        remaining_bytes = max_context_bytes - current_size
        if remaining_bytes > 500:  # Mínimo para snippets útiles
            snippets = self.get_context_snippets(query_concept, max_bytes=remaining_bytes)
            result['context_snippets'] = snippets
            current_size += len(json.dumps(snippets))
        
        result['total_context_size'] = current_size
        
        # Actualizar estadísticas de uso
        self.update_usage_stats(query_concept)
        
        return result
    
    def get_concept_info(self, concept_name):
        """
        Obtiene información básica de un concepto (ligera)
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute('''
                SELECT name, strength, category, usage_count, last_used, created_date
                FROM concepts 
                WHERE name = ?
                ORDER BY strength DESC
                LIMIT 1
            ''', (concept_name,)).fetchone()
            
            if result:
                return {
                    'name': result[0],
                    'strength': result[1],
                    'category': result[2], 
                    'usage_count': result[3],
                    'last_used': result[4],
                    'created_date': result[5]
                }
        return None
    
    def get_related_concepts(self, concept_name, limit=5):
        """
        Obtiene conceptos relacionados (solo nombres y fuerzas)
        """
        with sqlite3.connect(self.db_path) as conn:
            # Buscar relaciones donde el concepto aparece
            related = conn.execute('''
                SELECT 
                    CASE 
                        WHEN concept_a = ? THEN concept_b 
                        ELSE concept_a 
                    END as related_concept,
                    strength
                FROM relationships 
                WHERE concept_a = ? OR concept_b = ?
                ORDER BY strength DESC
                LIMIT ?
            ''', (concept_name, concept_name, concept_name, limit)).fetchall()
            
            return [{'name': r[0], 'strength': r[1]} for r in related]
    
    def get_context_snippets(self, concept_name, max_bytes=1000):
        """
        Obtiene snippets de contexto respetando límite de bytes
        """
        snippets = []
        current_bytes = 0
        
        with sqlite3.connect(self.db_path) as conn:
            # Obtener ubicaciones del concepto
            locations = conn.execute('''
                SELECT file_path, byte_start, byte_end, strength
                FROM concepts 
                WHERE name = ?
                ORDER BY strength DESC
                LIMIT 3
            ''', (concept_name,)).fetchall()
            
            for file_path, byte_start, byte_end, strength in locations:
                if current_bytes >= max_bytes:
                    break
                    
                # Leer snippet del archivo
                try:
                    snippet = self.read_file_snippet(file_path, byte_start, byte_end)
                    snippet_data = {
                        'text': snippet[:200],  # Máximo 200 chars por snippet
                        'file': os.path.basename(file_path),
                        'strength': strength
                    }
                    
                    snippet_bytes = len(json.dumps(snippet_data))
                    if current_bytes + snippet_bytes <= max_bytes:
                        snippets.append(snippet_data)
                        current_bytes += snippet_bytes
                        
                except Exception as e:
                    continue  # Skip problematic files
                    
        return snippets
    
    def read_file_snippet(self, file_path, byte_start, byte_end):
        """
        Lee un snippet específico de un archivo
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.seek(max(0, byte_start - 100))  # Contexto antes
                text = f.read(byte_end - byte_start + 200)  # Contexto después
                return text
        except:
            return ""
    
    def update_usage_stats(self, concept_name):
        """
        Actualiza estadísticas de uso de un concepto
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE concepts 
                SET usage_count = usage_count + 1, last_used = ?
                WHERE name = ?
            ''', (datetime.now().isoformat(), concept_name))
    
    def save_indices(self):
        """
        Guarda índices ligeros para carga rápida
        """
        indices_path = os.path.join(self.memory_path, "indices")
        
        # Índice de conceptos prioritarios (siempre en memoria)
        priority_concepts = self.get_priority_concepts()
        
        with open(os.path.join(indices_path, "priority_concepts.json"), 'w') as f:
            json.dump(priority_concepts, f, indent=2)
            
        # Estadísticas generales
        stats = self.get_system_stats()
        
        with open(os.path.join(indices_path, "system_stats.json"), 'w') as f:
            json.dump(stats, f, indent=2)
            
        print(f"💾 Índices guardados en {indices_path}")
    
    def get_priority_concepts(self):
        """
        Identifica conceptos prioritarios para mantener en memoria
        """
        with sqlite3.connect(self.db_path) as conn:
            # Top conceptos por fuerza y uso
            priority = conn.execute('''
                SELECT name, strength, usage_count, category
                FROM concepts 
                WHERE strength > 0.7 OR usage_count > 5
                ORDER BY (strength * 0.5 + usage_count * 0.1) DESC
                LIMIT 50
            ''').fetchall()
            
            return [
                {
                    'name': p[0],
                    'strength': p[1], 
                    'usage_count': p[2],
                    'category': p[3]
                }
                for p in priority
            ]
    
    def get_system_stats(self):
        """
        Obtiene estadísticas generales del sistema
        """
        with sqlite3.connect(self.db_path) as conn:
            total_concepts = conn.execute('SELECT COUNT(*) FROM concepts').fetchone()[0]
            total_relationships = conn.execute('SELECT COUNT(*) FROM relationships').fetchone()[0]
            
            categories = conn.execute('''
                SELECT category, COUNT(*) 
                FROM concepts 
                GROUP BY category
            ''').fetchall()
            
            return {
                'total_concepts': total_concepts,
                'total_relationships': total_relationships,
                'categories': dict(categories),
                'last_updated': datetime.now().isoformat(),
                'memory_size_estimate': f"{(total_concepts * 200 + total_relationships * 100) // 1024}KB"
            }
    
    def load_indices(self):
        """
        Carga índices ligeros al iniciar
        """
        indices_path = os.path.join(self.memory_path, "indices")
        
        # Cargar conceptos prioritarios
        priority_file = os.path.join(indices_path, "priority_concepts.json")
        if os.path.exists(priority_file):
            with open(priority_file, 'r') as f:
                priority_data = json.load(f)
                self.priority_concepts = {p['name'] for p in priority_data}
                
        print(f"🧠 Índices cargados: {len(self.priority_concepts)} conceptos prioritarios")


def initialize_ianae_memory(conversations_database_path):
    """
    Función principal para inicializar el sistema de memoria IANAE
    """
    print("🚀 INICIALIZANDO SISTEMA DE MEMORIA IANAE")
    print("=" * 50)
    
    # Crear sistema de memoria
    memory_system = IANAEMemorySystem()
    
    # Procesar conversaciones del RAG
    memory_system.process_rag_conversations(conversations_database_path)
    
    print("\n✅ Sistema de memoria IANAE listo")
    print(f"📊 Estadísticas: {memory_system.get_system_stats()}")
    
    return memory_system


if __name__ == "__main__":
    # Inicializar con el path CORRECTO de las conversaciones de Lucas
    conversations_path = "C:\\IANAE\\memory\\conversations_database"
    memory_system = initialize_ianae_memory(conversations_path)
    
    # Prueba de consulta inteligente
    print("\n🔍 PRUEBA DE CONSULTA INTELIGENTE:")
    result = memory_system.smart_query("python", max_context_bytes=2000)
    print(f"Información de 'python': {result['concept_info']}")
    print(f"Conceptos relacionados: {len(result['related_concepts'])}")
    print(f"Contexto total usado: {result['total_context_size']} bytes")
