# ianae_memory_working.py - VERSIÓN QUE ACCEDE AL TEXTO REAL
import json
import os
import sqlite3
from datetime import datetime
from collections import defaultdict
import re

class IANAEMemoryWorking:
    """
    Versión que accede correctamente al texto en messages[].content
    """
    
    def __init__(self, memory_base_path="C:/IANAE/IANAE_MEMORY"):
        self.memory_base_path = memory_base_path
        self.db_path = os.path.join(memory_base_path, "ianae_index.db")
        
        print(f"📁 Conectando a: {self.db_path}")
        
        # Patrones optimizados para Lucas
        self.patterns = {
            'tech_opencv': [
                r'cv2\.\w+', r'findContours', r'HSV', r'mask', r'contour',
                'OpenCV', 'imread', 'imshow', 'waitKey'
            ],
            'tech_python': [
                r'import \w+', r'from \w+', r'def \w+', r'class \w+', 
                'numpy', 'matplotlib', 'pandas', '.py'
            ],
            'tech_vba': [
                r'Application\.\w+', r'Worksheet\.\w+', r'Range\(', r'Cells\(',
                'VBA', '.xlsm', 'Excel', 'Macro'
            ],
            'projects': [
                'tacógrafo', 'tacografo', 'círculo', 'circulo', 'detección',
                'VBA2Python', 'IANAE', 'Docker', 'GPU'
            ],
            'lucas_personal': [
                'Lucas', 'Novelda', 'Valencia', 'i9-10900KF', 'RTX3060',
                'TOC', 'TDAH', 'superpoder', 'patrón'
            ]
        }
    
    def extract_text_from_conversation(self, conversation_data):
        """Extrae texto correctamente de la estructura messages"""
        texts = []
        
        if 'messages' in conversation_data:
            for message in conversation_data['messages']:
                if isinstance(message, dict) and 'text' in message:
                    text_content = message['text']
                    if isinstance(text_content, str) and len(text_content.strip()) > 10:
                        texts.append(text_content.strip())
        
        # También extraer de otros campos si existen
        for field in ['memory_bank_summary', 'title']:
            if field in conversation_data and isinstance(conversation_data[field], str):
                texts.append(conversation_data[field])
        
        return ' '.join(texts)
    
    def extract_concepts_from_text(self, text, source_file):
        """Extrae conceptos usando patrones optimizados"""
        concepts = []
        text_lower = text.lower()
        
        # Buscar cada patrón
        for category, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                if pattern.startswith('r'):
                    # Regex pattern  
                    try:
                        matches = re.findall(pattern[1:], text, re.IGNORECASE)
                        for match in matches[:5]:  # Max 5 por patrón
                            if match and len(match.strip()) > 2:
                                concepts.append({
                                    'name': match.strip(),
                                    'category': category,
                                    'file': source_file,
                                    'strength': 0.8
                                })
                    except:
                        continue
                else:
                    # Búsqueda simple
                    if pattern.lower() in text_lower:
                        concepts.append({
                            'name': pattern,
                            'category': category,
                            'file': source_file,
                            'strength': 0.7
                        })
        
        # Palabras técnicas adicionales
        tech_words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_.]{2,20}\b', text)
        for word in tech_words:
            # Filtros específicos
            if (word.lower().startswith(('cv2', 'np.', 'plt.')) or
                word.endswith(('.py', '.xlsm', '.xlsx')) or
                word.count('.') == 1 and len(word) > 4):
                concepts.append({
                    'name': word,
                    'category': 'technical',
                    'file': source_file,
                    'strength': 0.6
                })
        
        return concepts
    
    def process_conversations_working(self, conversations_path):
        """Procesa conversaciones accediendo correctamente al texto"""
        print("🔍 Procesando conversaciones (acceso correcto al texto)...")
        
        all_concepts = []
        concept_counts = defaultdict(int)
        files_processed = 0
        
        for filename in os.listdir(conversations_path):
            if filename.endswith('.json'):
                file_path = os.path.join(conversations_path, filename)
                files_processed += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # ACCESO CORRECTO AL TEXTO
                    text_content = self.extract_text_from_conversation(data)
                    
                    if text_content and len(text_content.strip()) > 20:  # Reducir filtro
                        # Extraer conceptos
                        concepts = self.extract_concepts_from_text(text_content, filename)
                        
                        # Contar y agregar
                        for concept in concepts:
                            concept_counts[concept['name']] += 1
                            all_concepts.append(concept)
                        
                        # Debug cada 50 archivos
                        if files_processed % 50 == 0:
                            unique_concepts = len(set(c['name'] for c in all_concepts))
                            print(f"   📊 {files_processed} archivos, {len(all_concepts)} conceptos, {unique_concepts} únicos")
                            
                            # Mostrar algunos conceptos encontrados
                            if len(all_concepts) > 0:
                                recent_concepts = [c['name'] for c in all_concepts[-10:]]
                                print(f"   🔍 Últimos conceptos: {', '.join(recent_concepts[:5])}...")
                
                except Exception as e:
                    print(f"⚠️  Error en {filename}: {e}")
                    continue
        
        print(f"✅ Procesamiento completado:")
        print(f"   📁 Archivos: {files_processed}")
        print(f"   📊 Conceptos totales: {len(all_concepts)}")
        print(f"   🎯 Conceptos únicos: {len(concept_counts)}")
        
        # Mostrar top conceptos
        if concept_counts:
            top_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            print(f"   🏆 Top 15 conceptos:")
            for concept, count in top_concepts:
                print(f"      • {concept}: {count}x")
        
        # Filtrar por frecuencia mínima
        frequent_concepts = {k: v for k, v in concept_counts.items() if v >= 2}
        print(f"   ✅ Conceptos con freq >= 2: {len(frequent_concepts)}")
        
        if len(frequent_concepts) == 0:
            print("   ⚠️  Usando todos los conceptos (sin filtro)")
            frequent_concepts = concept_counts
        
        # Guardar en base de datos
        saved_concepts = self.save_concepts_working(all_concepts, frequent_concepts)
        saved_relations = self.build_relations_working(all_concepts)
        
        return saved_concepts, saved_relations
    
    def save_concepts_working(self, all_concepts, frequent_concepts):
        """Guarda conceptos en la base de datos real"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Preparar conceptos únicos
            unique_concepts = {}
            for concept in all_concepts:
                name = concept['name']
                if name in frequent_concepts:
                    if name not in unique_concepts:
                        unique_concepts[name] = {
                            'name': name,
                            'category': concept['category'],
                            'strength': concept['strength'],
                            'files': set(),
                            'usage_count': frequent_concepts[name]
                        }
                    
                    unique_concepts[name]['files'].add(concept['file'])
                    # Actualizar strength máxima
                    unique_concepts[name]['strength'] = max(
                        unique_concepts[name]['strength'],
                        concept['strength']
                    )
            
            print(f"💾 Guardando {len(unique_concepts)} conceptos únicos...")
            
            saved_count = 0
            for concept_data in unique_concepts.values():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO concepts 
                        (name, file_path, byte_start, byte_end, strength, last_used, usage_count, category, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        concept_data['name'],
                        ','.join(list(concept_data['files'])[:5]),  # Primeros 5 archivos
                        0,
                        0,
                        concept_data['strength'],
                        datetime.now().isoformat(),
                        concept_data['usage_count'],
                        concept_data['category'],
                        datetime.now().isoformat()
                    ))
                    saved_count += 1
                    
                except Exception as e:
                    print(f"⚠️  Error guardando {concept_data['name']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ Conceptos guardados: {saved_count}")
            return saved_count
            
        except Exception as e:
            print(f"❌ Error guardando conceptos: {e}")
            return 0
    
    def build_relations_working(self, all_concepts):
        """Construye relaciones por co-ocurrencia en archivos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Agrupar por archivo
            file_concepts = defaultdict(set)
            for concept in all_concepts:
                file_concepts[concept['file']].add(concept['name'])
            
            print(f"🔗 Construyendo relaciones desde {len(file_concepts)} archivos...")
            
            relations_saved = 0
            processed_pairs = set()
            
            for filename, concepts in file_concepts.items():
                concepts_list = list(concepts)
                
                # Crear pares de conceptos que co-ocurren
                for i, concept_a in enumerate(concepts_list):
                    for concept_b in concepts_list[i+1:]:
                        pair_key = tuple(sorted([concept_a, concept_b]))
                        
                        if pair_key not in processed_pairs:
                            processed_pairs.add(pair_key)
                            
                            # Calcular strength
                            strength = 0.1
                            
                            # Bonus por categorías técnicas
                            tech_indicators = ['cv2', 'python', 'vba', 'import', 'def']
                            if any(ind in concept_a.lower() for ind in tech_indicators):
                                strength += 0.15
                            if any(ind in concept_b.lower() for ind in tech_indicators):
                                strength += 0.15
                            
                            try:
                                cursor.execute('''
                                    INSERT OR REPLACE INTO relationships 
                                    (concept_a, concept_b, strength, discovery_date, context)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (
                                    concept_a,
                                    concept_b,
                                    strength,
                                    datetime.now().isoformat(),
                                    f'cooccurrence_in_{filename}'
                                ))
                                relations_saved += 1
                                
                            except Exception as e:
                                continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ Relaciones guardadas: {relations_saved}")
            return relations_saved
            
        except Exception as e:
            print(f"❌ Error construyendo relaciones: {e}")
            return 0
    
    def test_queries_working(self):
        """Prueba las consultas en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("🔍 PRUEBAS DE CONSULTA:")
            
            # Ver totales
            cursor.execute("SELECT COUNT(*) FROM concepts")
            total_concepts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM relationships")
            total_relations = cursor.fetchone()[0]
            
            print(f"📊 Base de datos: {total_concepts} conceptos, {total_relations} relaciones")
            
            # Pruebas específicas
            test_queries = ['python', 'cv2', 'vba', 'lucas', 'tacografo', 'OpenCV', 'import']
            
            for query in test_queries:
                cursor.execute('''
                    SELECT name, usage_count, category, strength 
                    FROM concepts 
                    WHERE name LIKE ? 
                    ORDER BY usage_count DESC, strength DESC 
                    LIMIT 3
                ''', (f'%{query}%',))
                
                results = cursor.fetchall()
                
                if results:
                    print(f"✅ '{query}':")
                    for name, usage, cat, strength in results:
                        print(f"   • {name} ({usage}x, {cat}, {strength:.2f})")
                        
                        # Buscar relacionados
                        cursor.execute('''
                            SELECT concept_b, strength FROM relationships 
                            WHERE concept_a = ? 
                            ORDER BY strength DESC LIMIT 3
                        ''', (name,))
                        
                        related = cursor.fetchall()
                        if related:
                            related_names = [r[0] for r in related]
                            print(f"     🔗 {', '.join(related_names)}")
                else:
                    print(f"❌ '{query}': No encontrado")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error en consultas: {e}")

def run_working_version():
    """Ejecutar la versión que funciona"""
    print("🚀 EJECUTANDO VERSIÓN QUE ACCEDE AL TEXTO REAL")
    print("=" * 60)
    
    system = IANAEMemoryWorking()
    
    conversations_path = "C:/IANAE/memory/conversations_database"
    concepts_saved, relations_saved = system.process_conversations_working(conversations_path)
    
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"   💾 Conceptos guardados: {concepts_saved}")
    print(f"   🔗 Relaciones guardadas: {relations_saved}")
    
    # Pruebas
    print(f"\n" + "="*50)
    system.test_queries_working()
    
    return system

if __name__ == "__main__":
    system = run_working_version()
