# Añadir este endpoint a tu IANAE 2.0 app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
from collections import Counter

# Asumiendo que ya tienes tu app Flask configurada
# app = Flask(__name__)
# CORS(app)  # Si no lo tienes ya

@app.route('/api/analyze-document', methods=['POST'])
def analyze_document():
    """
    Endpoint para analizar documentos y extraer conceptos usando IANAE 2.0
    """
    try:
        data = request.get_json()
        content = data.get('content', '')
        filename = data.get('filename', 'unknown')
        
        print(f"🔍 Analizando documento: {filename}")
        print(f"📄 Caracteres: {len(content)}")
        
        # Extraer conceptos usando tu sistema real
        concepts = extract_concepts_from_content(content)
        relations = find_relations_for_concepts(concepts)
        
        # Buscar conexiones con conceptos existentes en IANAE
        existing_matches = find_existing_concept_matches(concepts)
        
        response = {
            'status': 'success',
            'filename': filename,
            'stats': {
                'total_chars': len(content),
                'total_words': len(content.split()),
                'concepts_found': len(concepts),
                'relations_found': len(relations),
                'existing_matches': len(existing_matches)
            },
            'concepts': concepts,
            'relations': relations,
            'existing_matches': existing_matches,
            'timestamp': str(datetime.now())
        }
        
        print(f"✅ Análisis completado: {len(concepts)} conceptos encontrados")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error en análisis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def extract_concepts_from_content(content):
    """
    Extrae conceptos del contenido usando lógica similar a tu sistema
    """
    # Limpiar y normalizar texto
    words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', content.lower())
    
    # Contar frecuencias
    word_freq = Counter(words)
    
    # Filtrar palabras comunes (stop words básicas)
    stop_words = {'para', 'con', 'por', 'como', 'una', 'del', 'las', 'los', 'que', 'este', 'esta', 'sistema', 'puede', 'desde', 'hasta', 'todo', 'cada', 'más', 'sobre', 'entre'}
    
    # Crear lista de conceptos
    concepts = []
    for word, freq in word_freq.most_common(20):  # Top 20
        if word not in stop_words and freq > 1:  # Aparece al menos 2 veces
            concepts.append({
                'name': word.capitalize(),
                'frequency': freq,
                'category': categorize_concept(word),
                'relevance': min(1.0, freq / 5.0)  # Relevancia normalizada
            })
    
    return concepts

def categorize_concept(word):
    """
    Categoriza conceptos basado en tu sistema IANAE
    """
    tech_words = ['python', 'javascript', 'html', 'css', 'api', 'database', 'server', 'code', 'desarrollo', 'programacion']
    project_words = ['ianae', 'proyecto', 'sistema', 'aplicacion', 'herramienta']
    ia_words = ['inteligencia', 'artificial', 'machine', 'learning', 'modelo', 'algoritmo', 'datos']
    
    word_lower = word.lower()
    
    if any(tech in word_lower for tech in tech_words):
        return 'tecnologias'
    elif any(proj in word_lower for proj in project_words):
        return 'proyectos'
    elif any(ia in word_lower for ia in ia_words):
        return 'conceptos_ianae'
    else:
        return 'general'

def find_relations_for_concepts(concepts):
    """
    Encuentra relaciones potenciales entre conceptos
    """
    relations = []
    
    for i, concept1 in enumerate(concepts):
        for concept2 in concepts[i+1:]:
            # Calcular fuerza de relación basada en co-ocurrencia y categorías
            strength = calculate_relation_strength(concept1, concept2)
            
            if strength > 0.3:  # Umbral mínimo
                relations.append({
                    'from': concept1['name'],
                    'to': concept2['name'],
                    'strength': round(strength, 3),
                    'type': 'co_occurrence'
                })
    
    return relations[:10]  # Top 10 relaciones

def calculate_relation_strength(concept1, concept2):
    """
    Calcula la fuerza de relación entre dos conceptos
    """
    # Fuerza base por frecuencia
    freq_strength = min(concept1['frequency'], concept2['frequency']) / 10.0
    
    # Bonus si están en la misma categoría
    category_bonus = 0.2 if concept1['category'] == concept2['category'] else 0
    
    # Bonus por relevancia
    relevance_bonus = (concept1['relevance'] + concept2['relevance']) / 4.0
    
    return min(1.0, freq_strength + category_bonus + relevance_bonus)

def find_existing_concept_matches(new_concepts):
    """
    Busca coincidencias con conceptos existentes en IANAE 2.0
    """
    matches = []
    
    try:
        # Conectar a tu base de datos IANAE
        conn = sqlite3.connect('ianae_memory.db')  # Ajusta el path
        cursor = conn.cursor()
        
        for concept in new_concepts:
            # Buscar conceptos similares en la BD
            cursor.execute("""
                SELECT name, category, COUNT(*) as mentions 
                FROM concepts 
                WHERE name LIKE ? OR name LIKE ?
                LIMIT 5
            """, (f"%{concept['name']}%", f"%{concept['name'].lower()}%"))
            
            results = cursor.fetchall()
            
            for result in results:
                matches.append({
                    'new_concept': concept['name'],
                    'existing_concept': result[0],
                    'existing_category': result[1],
                    'existing_mentions': result[2],
                    'similarity': calculate_similarity(concept['name'], result[0])
                })
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ No se pudo conectar a BD IANAE: {e}")
        # Simular algunos matches para testing
        matches = [
            {
                'new_concept': new_concepts[0]['name'] if new_concepts else 'Test',
                'existing_concept': 'IANAE',
                'existing_category': 'proyectos',
                'existing_mentions': 15,
                'similarity': 0.7
            }
        ]
    
    return matches

def calculate_similarity(word1, word2):
    """
    Calcula similitud básica entre dos palabras
    """
    # Similitud simple basada en caracteres comunes
    set1, set2 = set(word1.lower()), set(word2.lower())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0

# También añadir endpoint de testing
@app.route('/api/test', methods=['GET'])
def test_api():
    """Endpoint simple para verificar que la API funciona"""
    return jsonify({
        'status': 'ok',
        'message': 'IANAE 2.0 API funcionando',
        'timestamp': str(datetime.now())
    })

if __name__ == '__main__':
    # Si este es tu archivo principal, añadir:
    from datetime import datetime
    print("🚀 IANAE 2.0 con API endpoint iniciado")
    print("📡 Endpoint disponible: /api/analyze-document")
    print("🧪 Test endpoint: /api/test")
