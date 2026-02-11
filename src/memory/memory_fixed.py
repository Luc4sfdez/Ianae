# ianae_memory_system_fixed.py - Versión corregida con mejor debug
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import pickle
from typing import Dict, List, Optional
import re

class IANAEMemorySystem:
    """
    Sistema de memoria inteligente para IANAE - VERSIÓN CORREGIDA
    """
    
    def __init__(self, memory_base_path="C:/IANAE/IANAE_MEMORY"):
        """Inicializa el sistema de memoria con debugging mejorado"""
        self.memory_base_path = memory_base_path
        self.db_path = os.path.join(memory_base_path, "concept_memory.db")
        self.indices_path = os.path.join(memory_base_path, "indices")
        
        # Crear directorios si no existen
        os.makedirs(memory_base_path, exist_ok=True)
        os.makedirs(self.indices_path, exist_ok=True)
        
        print(f"📁 Sistema inicializado en: {memory_base_path}")
        print(f"💾 Base de datos: {self.db_path}")
        
        # Índices en memoria
        self.concept_index = defaultdict(dict)
        self.relationship_index = defaultdict(set)
        self.usage_stats = defaultdict(int)
        
        # Patrones específicos para Lucas
        self.lucas_patterns = {
            'locations': ['Novelda', 'Valencia', 'Alicante'],
            'hardware': ['i9-10900KF', 'RTX3060', 'RTX 3060', '32GB'],
            'personal': ['TOC', 'TDAH', 'superpoder', 'patron'],
            'tech_vba': [r'Application\.', r'Worksheet\.', r'Range\(', r'Cells\(', 'VBA'],
            'tech_opencv': [r'cv2\.', 'findContours', 'HSV', 'mask', 'contour'],
            'tech_python': ['import ', 'def ', 'class ', 'numpy', 'matplotlib'],
            'projects': ['tacógrafo', 'tacografo', 'círculo', 'circulo', 'detección', 'VBA2Python']
        }
        
        # Inicializar base de datos
        self.init_database()
        
    def init_database(self):
        """Inicializa la base de datos SQLite con debugging"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla de conceptos con más campos para debugging
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS concept_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    category TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context_snippet TEXT,
                    source_files TEXT,
                    strength REAL DEFAULT 0.0
                )
            ''')
            
            # Tabla de relaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS concept_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept_a TEXT NOT NULL,
                    concept_b TEXT NOT NULL,
                    strength REAL DEFAULT 0.0,
                    co_occurrence INTEGER DEFAULT 1,
                    context_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(concept_a, concept_b)
                )
            ''')
            
            # Índices para rendimiento
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_concept_name ON concept_index(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_concept_frequency ON concept_index(frequency)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationship_strength ON concept_relationships(strength)')
            
            conn.commit()
            conn.close()
            print("✅ Base de datos inicializada correctamente")
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")
    
    def extract_concepts_from_text(self, text, source_file=""):
        """Extrae conceptos de texto con mejores patrones"""
        concepts = defaultdict(list)
        
        # Limpiar texto
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # 1. Patrones técnicos específicos de Lucas
        for category, patterns in self.lucas_patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str) and not pattern.startswith('r'):
                    # Búsqueda simple
                    if pattern.lower() in text.lower():
                        concepts[category].append(pattern)
                else:
                    # Regex pattern
                    pattern_clean = pattern.replace('r', '') if pattern.startswith('r') else pattern
                    matches = re.findall(pattern_clean, text, re.IGNORECASE)
                    concepts[category].extend(matches[:3])  # Máximo 3 por patrón
        
        # 2. Palabras técnicas generales (más flexible)
        tech_words = []
        words = re.findall(r'\b[A-Za-z][A-Za-z0-9_\.]{2,15}\b', text)
        
        for word in words:
            word_lower = word.lower()
            # Filtrar palabras técnicas relevantes
            if (len(word) >= 3 and
                ('cv2' in word_lower or 
                 'python' in word_lower or
                 'vba' in word_lower or
                 'excel' in word_lower or
                 'opencv' in word_lower or
                 word_lower.endswith('.py') or
                 word_lower.endswith('.xlsm') or
                 word.count('.') == 1)):  # Métodos con punto
                tech_words.append(word)
        
        concepts['technical'] = list(set(tech_words))[:10]  # Top 10 únicos
        
        # 3. Conceptos de proyectos (basado en contexto)
        project_indicators = []
        if any(word in text.lower() for word in ['proyecto', 'desarrollar', 'implementar', 'crear']):
            # Buscar nombres propios después de estos indicadores
            project_matches = re.findall(r'\b[A-Z][a-z]{3,12}\b', text)
            project_indicators.extend(project_matches[:5])
        
        concepts['projects'] = project_indicators
        
        return concepts
    
    def process_rag_conversations(self, conversations_database_path):
        """Procesa conversaciones con mejor extracción y debugging"""
        print("🔍 Procesando conversaciones del RAG...")
        
        if not os.path.exists(conversations_database_path):
            print(f"❌ Directorio no encontrado: {conversations_database_path}")
            return
        
        total_concepts_extracted = 0
        concept_frequency = defaultdict(int)
        concept_contexts = defaultdict(list)
        file_count = 0
        
        try:
            for filename in os.listdir(conversations_database_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(conversations_database_path, filename)
                    file_count += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # Procesar diferentes estructuras JSON
                            text_content = ""
                            if isinstance(data, dict):
                                # Buscar contenido de texto en diferentes campos
                                for key in ['content', 'text', 'message', 'conversation', 'data']:
                                    if key in data:
                                        if isinstance(data[key], str):
                                            text_content += data[key] + " "
                                        elif isinstance(data[key], list):
                                            for item in data[key]:
                                                if isinstance(item, dict):
                                                    for subkey in ['content', 'text', 'message']:
                                                        if subkey in item and isinstance(item[subkey], str):
                                                            text_content += item[subkey] + " "
                                                elif isinstance(item, str):
                                                    text_content += item + " "
                            elif isinstance(data, list):
                                for item in data:
                                    if isinstance(item, str):
                                        text_content += item + " "
                                    elif isinstance(item, dict):
                                        for key in ['content', 'text', 'message']:
                                            if key in item and isinstance(item[key], str):
                                                text_content += item[key] + " "
                            
                            # Extraer conceptos del texto
                            if text_content.strip():
                                concepts = self.extract_concepts_from_text(text_content, filename)
                                
                                for category, concept_list in concepts.items():
                                    for concept in concept_list:
                                        if concept and len(concept.strip()) > 2:
                                            concept_clean = concept.strip()
                                            concept_frequency[concept_clean] += 1
                                            concept_contexts[concept_clean].append({
                                                'file': filename,
                                                'category': category,
                                                'snippet': text_content[:100] + "..." if len(text_content) > 100 else text_content
                                            })
                                            total_concepts_extracted += 1
                    
                    except Exception as e:
                        print(f"⚠️  Error procesando {filename}: {e}")
                        continue
                    
                    # Progress cada 50 archivos
                    if file_count % 50 == 0:
                        print(f"   📊 Procesados {file_count} archivos, {total_concepts_extracted} conceptos extraídos")
        
        except Exception as e:
            print(f"❌ Error general en procesamiento: {e}")
            return
        
        print(f"✅ Procesamiento completado: {file_count} conversaciones, {total_concepts_extracted} conceptos totales")
        
        # DEBUGGING: Mostrar stats antes del filtrado
        print(f"🔍 DEBUG: Conceptos únicos antes de filtrar: {len(concept_frequency)}")
        top_concepts = sorted(concept_frequency.items(), key=lambda x: x[1], reverse=True)[:20]
        print(f"🔍 DEBUG: Top 20 conceptos por frecuencia:")
        for concept, freq in top_concepts[:10]:
            print(f"   • {concept}: {freq} veces")
        
        # Filtrar conceptos por frecuencia (MENOS RESTRICTIVO)
        filtered_concepts = {k: v for k, v in concept_frequency.items() if v >= 2}  # Mínimo 2 apariciones
        print(f"🔍 DEBUG: Conceptos después de filtrar (freq >= 2): {len(filtered_concepts)}")
        
        if len(filtered_concepts) == 0:
            print("⚠️  ADVERTENCIA: No hay conceptos con frecuencia >= 2")
            # Usar todos los conceptos que aparecen al menos una vez
            filtered_concepts = concept_frequency
            print(f"🔄 Usando todos los conceptos: {len(filtered_concepts)}")
        
        # Guardar en base de datos
        concepts_saved = self.save_concepts_to_db(filtered_concepts, concept_contexts)
        print(f"💾 Conceptos guardados en DB: {concepts_saved}")
        
        # Construir relaciones
        relationships_built = self.build_relationships_from_contexts(concept_contexts)
        print(f"🔗 Relaciones construidas: {relationships_built}")
        
        return len(filtered_concepts), relationships_built
    
    def save_concepts_to_db(self, concept_frequency, concept_contexts):
        """Guarda conceptos en la base de datos con debugging"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            concepts_saved = 0
            
            for concept, frequency in concept_frequency.items():
                try:
                    # Determinar categoría principal
                    categories = [ctx['category'] for ctx in concept_contexts.get(concept, [])]
                    main_category = max(set(categories), key=categories.count) if categories else 'general'
                    
                    # Contexto de muestra
                    sample_context = concept_contexts.get(concept, [{}])[0].get('snippet', '')
                    
                    # Archivos fuente
                    source_files = ','.join(set([ctx['file'] for ctx in concept_contexts.get(concept, [])]))
                    
                    # Calcular strength basado en frecuencia y categoría
                    strength = min(1.0, frequency / 10.0)  # Normalizar a 0-1
                    if main_category in ['tech_python', 'tech_opencv', 'tech_vba']:
                        strength *= 1.2  # Boost para conceptos técnicos
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO concept_index 
                        (name, frequency, category, context_snippet, source_files, strength, last_used)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (concept, frequency, main_category, sample_context, source_files, strength, datetime.now()))
                    
                    concepts_saved += 1
                    
                except Exception as e:
                    print(f"⚠️  Error guardando concepto '{concept}': {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            return concepts_saved
            
        except Exception as e:
            print(f"❌ Error guardando conceptos: {e}")
            return 0
    
    def build_relationships_from_contexts(self, concept_contexts):
        """Construye relaciones basadas en co-ocurrencia en contextos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            relationships_built = 0
            
            # Agrupar por archivo para encontrar co-ocurrencias
            file_concepts = defaultdict(set)
            
            for concept, contexts in concept_contexts.items():
                for ctx in contexts:
                    file_concepts[ctx['file']].add(concept)
            
            # Construir relaciones por co-ocurrencia
            for filename, concepts in file_concepts.items():
                concepts_list = list(concepts)
                
                for i, concept_a in enumerate(concepts_list):
                    for concept_b in concepts_list[i+1:]:
                        if concept_a != concept_b:
                            try:
                                # Calcular strength basado en co-ocurrencia
                                strength = 0.1  # Base strength
                                
                                # Boost si ambos son técnicos
                                if any(c in concept_a.lower() for c in ['cv2', 'python', 'vba']) and \
                                   any(c in concept_b.lower() for c in ['cv2', 'python', 'vba']):
                                    strength = 0.3
                                
                                cursor.execute('''
                                    INSERT OR REPLACE INTO concept_relationships 
                                    (concept_a, concept_b, strength, co_occurrence, context_type)
                                    VALUES (?, ?, ?, 1, ?)
                                ''', (concept_a, concept_b, strength, 'file_cooccurrence'))
                                
                                relationships_built += 1
                                
                            except Exception as e:
                                continue
            
            conn.commit()
            conn.close()
            
            return relationships_built
            
        except Exception as e:
            print(f"❌ Error construyendo relaciones: {e}")
            return 0
    
    def smart_query(self, concept_name, max_context_bytes=3500):
        """Consulta inteligente con límite de contexto y debugging"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar concepto principal (búsqueda flexible)
            cursor.execute('''
                SELECT name, frequency, category, context_snippet, strength 
                FROM concept_index 
                WHERE name LIKE ? OR name LIKE ?
                ORDER BY frequency DESC, strength DESC
                LIMIT 1
            ''', (f'%{concept_name}%', concept_name))
            
            main_concept = cursor.fetchone()
            
            if not main_concept:
                conn.close()
                return {
                    'concept': None,
                    'related_concepts': [],
                    'context_used': 0,
                    'debug_info': f'No se encontró concepto similar a: {concept_name}'
                }
            
            name, frequency, category, snippet, strength = main_concept
            
            # Buscar conceptos relacionados
            cursor.execute('''
                SELECT concept_b, strength FROM concept_relationships 
                WHERE concept_a = ?
                UNION
                SELECT concept_a, strength FROM concept_relationships 
                WHERE concept_b = ?
                ORDER BY strength DESC
                LIMIT 10
            ''', (name, name))
            
            related = cursor.fetchall()
            
            conn.close()
            
            # Construir respuesta respetando límite de contexto
            result = {
                'concept': {
                    'name': name,
                    'frequency': frequency,
                    'category': category,
                    'strength': strength,
                    'snippet': snippet[:200] if snippet else 'Sin contexto'
                },
                'related_concepts': [{'name': r[0], 'strength': r[1]} for r in related],
                'context_used': len(str(main_concept)) + sum(len(str(r)) for r in related),
                'debug_info': f'Concepto encontrado: {name} (freq: {frequency})'
            }
            
            return result
            
        except Exception as e:
            return {
                'concept': None,
                'related_concepts': [],
                'context_used': 0,
                'debug_info': f'Error en consulta: {e}'
            }

def initialize_ianae_memory_fixed(conversations_database_path):
    """
    Función principal CORREGIDA para inicializar el sistema de memoria IANAE
    """
    print("🚀 INICIALIZANDO SISTEMA DE MEMORIA IANAE - VERSIÓN CORREGIDA")
    print("=" * 60)
    
    # Crear sistema de memoria
    memory_system = IANAEMemorySystem()
    
    # Procesar conversaciones
    concepts_count, relationships_count = memory_system.process_rag_conversations(conversations_database_path)
    
    print("✅ Sistema de memoria IANAE listo")
    print(f"📊 Estadísticas finales:")
    print(f"   • Conceptos procesados: {concepts_count}")
    print(f"   • Relaciones construidas: {relationships_count}")
    
    # Prueba de consulta mejorada
    print("\n🔍 PRUEBA DE CONSULTA INTELIGENTE:")
    
    test_queries = ['python', 'cv2', 'vba', 'lucas', 'tacografo']
    
    for query in test_queries:
        result = memory_system.smart_query(query)
        print(f"\n🔎 Consulta '{query}':")
        if result['concept']:
            print(f"   ✅ Encontrado: {result['concept']['name']} (freq: {result['concept']['frequency']})")
            print(f"   📊 Conceptos relacionados: {len(result['related_concepts'])}")
        else:
            print(f"   ❌ {result['debug_info']}")
    
    return memory_system

if __name__ == "__main__":
    # Configurar path
    conversations_path = "C:/IANAE/memory/conversations_database"
    
    # Inicializar sistema corregido
    system = initialize_ianae_memory_fixed(conversations_path)
