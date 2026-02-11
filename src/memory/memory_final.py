# ianae_memory_final_fix.py - Usa las tablas reales y arregla la inserción
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import pickle
from typing import Dict, List, Optional
import re

class IANAEMemorySystemFixed:
    """
    Sistema de memoria IANAE - Versión que usa las tablas reales existentes
    """
    
    def __init__(self, memory_base_path="C:/IANAE/IANAE_MEMORY"):
        """Inicializa usando la base de datos existente"""
        self.memory_base_path = memory_base_path
        self.db_path = os.path.join(memory_base_path, "ianae_index.db")  # Usar DB real
        
        print(f"📁 Conectando a base existente: {self.db_path}")
        
        # Verificar que existe
        if not os.path.exists(self.db_path):
            print(f"❌ Base de datos no encontrada: {self.db_path}")
            return
        
        # Patrones de Lucas (mejorados)
        self.lucas_patterns = {
            'locations': ['Novelda', 'Valencia', 'Alicante'],
            'hardware': ['i9-10900KF', 'RTX3060', 'RTX 3060', '32GB'],
            'personal': ['TOC', 'TDAH', 'superpoder', 'patron'],
            'tech_vba': [r'Application\.', r'Worksheet\.', r'Range\(', r'Cells\(', 'VBA', 'xlsm'],
            'tech_opencv': [r'cv2\.', 'findContours', 'HSV', 'mask', 'contour', 'OpenCV'],
            'tech_python': ['import ', 'def ', 'class ', 'numpy', 'matplotlib', 'python'],
            'projects': ['tacógrafo', 'tacografo', 'círculo', 'circulo', 'detección', 'VBA2Python', 'IANAE']
        }
        
        print("✅ Sistema inicializado correctamente")
    
    def extract_concepts_improved(self, text, source_file=""):
        """Extracción mejorada de conceptos"""
        concepts = []
        
        # Limpiar texto
        text_clean = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # 1. Patrones específicos de Lucas
        for category, patterns in self.lucas_patterns.items():
            for pattern in patterns:
                if pattern.startswith('r'):
                    # Regex
                    pattern_clean = pattern[1:]  # Remover 'r'
                    try:
                        matches = re.findall(pattern_clean, text_clean, re.IGNORECASE)
                        for match in matches[:3]:  # Max 3 por patrón
                            if match and len(match.strip()) > 2:
                                concepts.append({
                                    'name': match.strip(),
                                    'category': category,
                                    'strength': 0.8,
                                    'context': text_clean[:150]
                                })
                    except:
                        continue
                else:
                    # Búsqueda simple
                    if pattern.lower() in text_clean.lower():
                        concepts.append({
                            'name': pattern,
                            'category': category,
                            'strength': 0.7,
                            'context': text_clean[:150]
                        })
        
        # 2. Palabras técnicas (más selectivo)
        tech_patterns = [
            r'\bcv2\.\w+',           # cv2.métodos
            r'\b\w+\(\)',            # funciones()
            r'\b[A-Z]\w+\.[A-Z]\w+', # Clases.Métodos
            r'\b\w+\.py\b',          # archivos.py
            r'\b\w+\.xlsm?\b',       # archivos Excel
            r'\bimport \w+',         # imports
            r'\bfrom \w+',           # from imports
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_clean)
            for match in matches[:5]:  # Max 5 por patrón
                if len(match) > 3:
                    concepts.append({
                        'name': match,
                        'category': 'technical',
                        'strength': 0.6,
                        'context': text_clean[:150]
                    })
        
        # 3. Conceptos de proyectos (nombres propios después de palabras clave)
        project_patterns = [
            r'proyecto\s+(\w+)',
            r'desarrollar\s+(\w+)',
            r'implementar\s+(\w+)',
            r'crear\s+(\w+)',
        ]
        
        for pattern in project_patterns:
            matches = re.findall(pattern, text_clean, re.IGNORECASE)
            for match in matches:
                if len(match) > 3:
                    concepts.append({
                        'name': match,
                        'category': 'projects',
                        'strength': 0.9,
                        'context': text_clean[:150]
                    })
        
        return concepts
    
    def process_conversations_fixed(self, conversations_database_path):
        """Procesa conversaciones y las guarda correctamente"""
        print("🔍 Procesando conversaciones (versión arreglada)...")
        
        if not os.path.exists(conversations_database_path):
            print(f"❌ Directorio no encontrado: {conversations_database_path}")
            return 0, 0
        
        all_concepts = []
        concept_counts = defaultdict(int)
        file_count = 0
        
        # Procesar archivos JSON
        for filename in os.listdir(conversations_database_path):
            if filename.endswith('.json'):
                file_path = os.path.join(conversations_database_path, filename)
                file_count += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Extraer texto del JSON (diferentes estructuras)
                        text_content = self.extract_text_from_json(data)
                        
                        if text_content.strip():
                            # Extraer conceptos
                            concepts = self.extract_concepts_improved(text_content, filename)
                            
                            for concept in concepts:
                                concept['file_path'] = filename
                                concept_counts[concept['name']] += 1
                                all_concepts.append(concept)
                
                except Exception as e:
                    print(f"⚠️  Error en {filename}: {e}")
                    continue
                
                # Progress
                if file_count % 50 == 0:
                    print(f"   📊 Procesados {file_count} archivos, {len(all_concepts)} conceptos encontrados")
        
        print(f"✅ Extracción completada: {file_count} archivos, {len(all_concepts)} conceptos extraídos")
        
        # Filtrar por frecuencia mínima
        frequent_concepts = {name: count for name, count in concept_counts.items() if count >= 2}
        print(f"🔍 Conceptos con frecuencia >= 2: {len(frequent_concepts)}")
        
        if len(frequent_concepts) == 0:
            print("⚠️  Usando todos los conceptos (sin filtro de frecuencia)")
            frequent_concepts = concept_counts
        
        # Guardar en base de datos usando tablas reales
        concepts_saved = self.save_to_real_db(all_concepts, frequent_concepts)
        relationships_saved = self.build_relationships_real(all_concepts)
        
        return concepts_saved, relationships_saved
    
    def extract_text_from_json(self, data):
        """Extrae texto de diferentes estructuras JSON"""
        text_parts = []
        
        def extract_text_recursive(obj):
            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ['content', 'text', 'message', 'conversation', 'data', 'response']:
                        extract_text_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text_recursive(item)
        
        extract_text_recursive(data)
        return ' '.join(text_parts)
    
    def save_to_real_db(self, all_concepts, frequent_concepts):
        """Guarda en las tablas reales con debugging detallado"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar estructura de tabla real
            cursor.execute("PRAGMA table_info(concepts);")
            columns_info = cursor.fetchall()
            print(f"🔍 Columnas de tabla 'concepts': {[col[1] for col in columns_info]}")
            
            concepts_saved = 0
            concepts_processed = {}
            
            # Procesar conceptos únicos
            for concept in all_concepts:
                concept_name = concept['name']
                
                if concept_name in frequent_concepts:
                    if concept_name not in concepts_processed:
                        concepts_processed[concept_name] = {
                            'name': concept_name,
                            'category': concept['category'],
                            'strength': concept['strength'],
                            'files': set(),
                            'contexts': []
                        }
                    
                    concepts_processed[concept_name]['files'].add(concept['file_path'])
                    concepts_processed[concept_name]['contexts'].append(concept['context'])
                    # Actualizar strength con el máximo
                    concepts_processed[concept_name]['strength'] = max(
                        concepts_processed[concept_name]['strength'], 
                        concept['strength']
                    )
            
            print(f"🔍 Conceptos únicos a guardar: {len(concepts_processed)}")
            
            # Insertar en base de datos
            for concept_name, concept_data in concepts_processed.items():
                try:
                    # Usar las columnas reales de la tabla
                    cursor.execute('''
                        INSERT OR REPLACE INTO concepts 
                        (name, file_path, byte_start, byte_end, strength, last_used, usage_count, category, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        concept_name,
                        ','.join(list(concept_data['files'])[:5]),  # Primeros 5 archivos
                        0,  # byte_start (no lo calculamos)
                        0,  # byte_end (no lo calculamos)
                        concept_data['strength'],
                        datetime.now().isoformat(),
                        frequent_concepts[concept_name],  # usage_count = frequency
                        concept_data['category'],
                        datetime.now().isoformat()
                    ))
                    
                    concepts_saved += 1
                    
                    if concepts_saved % 100 == 0:
                        print(f"   💾 Guardados {concepts_saved} conceptos...")
                
                except Exception as e:
                    print(f"⚠️  Error guardando '{concept_name}': {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ Conceptos guardados exitosamente: {concepts_saved}")
            return concepts_saved
            
        except Exception as e:
            print(f"❌ Error en guardado: {e}")
            return 0
    
    def build_relationships_real(self, all_concepts):
        """Construye relaciones usando la tabla real"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar estructura de tabla relationships
            cursor.execute("PRAGMA table_info(relationships);")
            rel_columns = cursor.fetchall()
            print(f"🔍 Columnas de tabla 'relationships': {[col[1] for col in rel_columns]}")
            
            # Agrupar conceptos por archivo
            file_concepts = defaultdict(set)
            for concept in all_concepts:
                file_concepts[concept['file_path']].add(concept['name'])
            
            relationships_saved = 0
            processed_pairs = set()
            
            # Crear relaciones por co-ocurrencia
            for filename, concepts in file_concepts.items():
                concepts_list = list(concepts)
                
                for i, concept_a in enumerate(concepts_list):
                    for concept_b in concepts_list[i+1:]:
                        pair = tuple(sorted([concept_a, concept_b]))
                        
                        if pair not in processed_pairs:
                            processed_pairs.add(pair)
                            
                            try:
                                # Calcular strength
                                strength = 0.1  # Base
                                if any(c in concept_a.lower() for c in ['cv2', 'python', 'vba']):
                                    strength += 0.2
                                if any(c in concept_b.lower() for c in ['cv2', 'python', 'vba']):  
                                    strength += 0.2
                                
                                # Insertar relación (estructura de tabla real)
                                cursor.execute('''
                                    INSERT OR REPLACE INTO relationships 
                                    (concept_a, concept_b, strength, context_type, created_date)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (
                                    concept_a,
                                    concept_b, 
                                    strength,
                                    'file_cooccurrence',
                                    datetime.now().isoformat()
                                ))
                                
                                relationships_saved += 1
                                
                            except Exception as e:
                                # Probar estructura alternativa si falla
                                try:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO relationships 
                                        (source_concept, target_concept, strength, relationship_type, last_updated)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (
                                        concept_a,
                                        concept_b,
                                        strength,
                                        'cooccurrence',
                                        datetime.now().isoformat()
                                    ))
                                    relationships_saved += 1
                                except:
                                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ Relaciones guardadas: {relationships_saved}")
            return relationships_saved
            
        except Exception as e:
            print(f"❌ Error construyendo relaciones: {e}")
            return 0
    
    def test_query_fixed(self, concept_name):
        """Prueba de consulta usando las tablas reales"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar concepto
            cursor.execute('''
                SELECT name, usage_count, category, strength 
                FROM concepts 
                WHERE name LIKE ? 
                ORDER BY usage_count DESC, strength DESC
                LIMIT 1
            ''', (f'%{concept_name}%',))
            
            result = cursor.fetchone()
            
            if result:
                name, usage_count, category, strength = result
                
                # Buscar relacionados
                cursor.execute('''
                    SELECT concept_b, strength FROM relationships WHERE concept_a = ?
                    UNION
                    SELECT concept_a, strength FROM relationships WHERE concept_b = ?
                    ORDER BY strength DESC LIMIT 5
                ''', (name, name))
                
                related = cursor.fetchall()
                
                conn.close()
                
                return {
                    'found': True,
                    'concept': {
                        'name': name,
                        'usage_count': usage_count,
                        'category': category,
                        'strength': strength
                    },
                    'related': related
                }
            else:
                conn.close()
                return {'found': False, 'query': concept_name}
                
        except Exception as e:
            return {'found': False, 'error': str(e)}

def run_fixed_processing():
    """Ejecutar procesamiento arreglado"""
    print("🚀 EJECUTANDO PROCESAMIENTO ARREGLADO")
    print("=" * 50)
    
    # Inicializar sistema
    system = IANAEMemorySystemFixed()
    
    # Procesar conversaciones
    conversations_path = "C:/IANAE/memory/conversations_database"
    concepts_saved, relationships_saved = system.process_conversations_fixed(conversations_path)
    
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"   💾 Conceptos guardados: {concepts_saved}")
    print(f"   🔗 Relaciones guardadas: {relationships_saved}")
    
    # Pruebas de consulta
    print(f"\n🔍 PRUEBAS DE CONSULTA:")
    test_queries = ['python', 'cv2', 'vba', 'lucas', 'tacografo', 'OpenCV']
    
    for query in test_queries:
        result = system.test_query_fixed(query)
        if result['found']:
            concept = result['concept']
            print(f"✅ {query}: {concept['name']} ({concept['usage_count']}x, {concept['category']})")
            if result['related']:
                related_names = [r[0] for r in result['related'][:3]]
                print(f"   🔗 Relacionados: {', '.join(related_names)}")
        else:
            print(f"❌ {query}: No encontrado")
    
    return system

if __name__ == "__main__":
    # Ejecutar procesamiento arreglado
    system = run_fixed_processing()
