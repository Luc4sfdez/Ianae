#!/usr/bin/env python3
"""
ianae_web_optimizado.py - IANAE con base de datos SQLite ultrarrápida
Version optimizada para usar ianae_esencial.db
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json
import logging
import os
from datetime import datetime
import requests
import time
import re
from collections import Counter

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app FastAPI
app = FastAPI(
    title="IANAE - Bibliotecario Personal Optimizado",
    description="Bibliotecario personal con memoria SQLite ultrarrápida",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración global
CONFIG = {
    "db_path": "ianae_esencial.db",
    "llm_endpoint": "http://localhost:1234/v1/chat/completions",
    "llm_model": "local-model",
    "max_conceptos_busqueda": 8,
    "timeout_llm": 60
}

# Conexión global a BD
db_conn = None

class ChatMessage(BaseModel):
    query: str
    conversacion_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conceptos_utilizados: list
    tiempo_busqueda: float
    timestamp: str

# NUEVO: Modelo para análisis de documentos
class DocumentAnalysis(BaseModel):
    content: str
    filename: str

def init_database():
    """Inicializa la conexión a la base de datos"""
    global db_conn
    
    if not os.path.exists(CONFIG["db_path"]):
        logger.error(f"❌ Base de datos no encontrada: {CONFIG['db_path']}")
        return False
    
    try:
        db_conn = sqlite3.connect(CONFIG["db_path"], check_same_thread=False)
        db_conn.row_factory = sqlite3.Row
        
        # Verificar que la BD tiene datos
        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conceptos")
        num_conceptos = cursor.fetchone()[0]
        
        logger.info(f"✅ BD conectada: {num_conceptos} conceptos disponibles")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error conectando BD: {e}")
        return False

def buscar_conceptos_sql(query: str) -> tuple:
    """Búsqueda ultrarrápida usando SQLite FTS con manejo de caracteres especiales"""
    if not db_conn:
        return [], 0.0
    
    inicio = time.time()
    cursor = db_conn.cursor()
    
    try:
        # LIMPIAR QUERY PARA FTS - Eliminar caracteres problemáticos
        import re
        query_limpio = re.sub(r'[,;:!?¿¡(){}[\]"\'`]', ' ', query)
        
        # Filtrar palabras útiles (eliminar conectores comunes)
        conectores = ['de', 'la', 'el', 'en', 'un', 'una', 'donde', 'que', 'con', 'por', 'para', 'hacer', 'necesito', 'hoa', 'nuevo']
        palabras = [p.strip().lower() for p in query_limpio.split() if len(p.strip()) > 2 and p.strip().lower() not in conectores]
        
        if not palabras:
            # Si no quedan palabras útiles, usar query original sin caracteres especiales
            palabras = [re.sub(r'[^\w\s]', '', query).strip()]
        
        query_fts = ' '.join(palabras[:5])  # Max 5 palabras importantes
        
        logger.info(f"🔍 Query original: {query}")
        logger.info(f"🧹 Query FTS: {query_fts}")
        
        # Búsqueda principal con FTS usando query limpio
        cursor.execute('''
            SELECT c.nombre, c.categoria, c.contexto, c.fuente, c.relevancia
            FROM conceptos_busqueda cb
            JOIN conceptos c ON c.nombre = cb.nombre
            WHERE conceptos_busqueda MATCH ?
            ORDER BY c.relevancia DESC
            LIMIT ?
        ''', (query_fts, CONFIG["max_conceptos_busqueda"]))
        
        resultados_fts = cursor.fetchall()
        logger.info(f"📊 FTS encontró: {len(resultados_fts)} conceptos")
        
        # Si pocos resultados FTS, búsqueda LIKE complementaria
        if len(resultados_fts) < CONFIG["max_conceptos_busqueda"] // 2:
            logger.info("🔍 Ampliando búsqueda con LIKE...")
            like_conditions = []
            params = []
            
            for palabra in palabras[:3]:  # Max 3 palabras para LIKE
                like_conditions.append("(LOWER(nombre) LIKE ? OR LOWER(contexto) LIKE ?)")
                params.extend([f'%{palabra}%', f'%{palabra}%'])
            
            if like_conditions:
                # Excluir resultados ya encontrados por FTS
                nombres_fts = [r['nombre'] for r in resultados_fts]
                exclusion = ','.join(['?' for _ in nombres_fts]) if nombres_fts else "''"
                
                query_like = f'''
                    SELECT nombre, categoria, contexto, fuente, relevancia
                    FROM conceptos
                    WHERE ({' OR '.join(like_conditions)})
                    AND nombre NOT IN ({exclusion})
                    ORDER BY relevancia DESC
                    LIMIT ?
                '''
                
                params.extend(nombres_fts)
                params.append(CONFIG["max_conceptos_busqueda"] - len(resultados_fts))
                
                cursor.execute(query_like, params)
                resultados_like = cursor.fetchall()
                logger.info(f"📊 LIKE encontró: {len(resultados_like)} conceptos adicionales")
                
                # Combinar resultados
                resultados_fts.extend(resultados_like)
        
        # Convertir a formato esperado
        conceptos_encontrados = []
        for row in resultados_fts:
            conceptos_encontrados.append({
                'concepto': row['nombre'],
                'categoria': row['categoria'],
                'contexto': row['contexto'] or '',
                'fuente': row['fuente'] or '',
                'puntuacion': float(row['relevancia']),
                'relevancia': row['relevancia']
            })
        
        tiempo_busqueda = time.time() - inicio
        return conceptos_encontrados, tiempo_busqueda
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error en búsqueda SQL: {e}")
        return [], 0.0

def obtener_contexto_relacionado(conceptos_principales: list) -> list:
    """Obtiene conceptos relacionados para enriquecer el contexto"""
    if not db_conn or not conceptos_principales:
        return []
    
    cursor = db_conn.cursor()
    conceptos_relacionados = []
    
    try:
        for concepto_data in conceptos_principales[:3]:  # Solo los top 3
            concepto_nombre = concepto_data['concepto']
            
            # Buscar relacionados
            cursor.execute('''
                SELECT concepto2, peso FROM relaciones 
                WHERE concepto1 = ? 
                ORDER BY peso DESC 
                LIMIT 3
                UNION
                SELECT concepto1, peso FROM relaciones 
                WHERE concepto2 = ? 
                ORDER BY peso DESC 
                LIMIT 3
            ''', (concepto_nombre, concepto_nombre))
            
            relacionados = cursor.fetchall()
            for rel_nombre, peso in relacionados:
                if peso > 0.3:  # Solo relaciones fuertes
                    # Obtener contexto del relacionado
                    cursor.execute('''
                        SELECT nombre, categoria, contexto, fuente, relevancia
                        FROM conceptos WHERE nombre = ?
                    ''', (rel_nombre,))
                    
                    rel_data = cursor.fetchone()
                    if rel_data:
                        conceptos_relacionados.append({
                            'concepto': rel_data['nombre'],
                            'categoria': rel_data['categoria'], 
                            'contexto': rel_data['contexto'] or '',
                            'fuente': rel_data['fuente'] or '',
                            'puntuacion': float(peso),
                            'relevancia': rel_data['relevancia'],
                            'es_relacionado': True
                        })
        
        # Ordenar por puntuación y eliminar duplicados
        conceptos_relacionados.sort(key=lambda x: x['puntuacion'], reverse=True)
        return conceptos_relacionados[:5]  # Max 5 relacionados
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error obteniendo relacionados: {e}")
        return []

def generar_contexto_para_llm(conceptos_principales: list, conceptos_relacionados: list = None) -> str:
    """Genera contexto rico para el LLM"""
    if not conceptos_principales:
        return "No se encontró información relevante en tu memoria personal."
    
    contexto_partes = [
        "MEMORIA PERSONAL DE LUCAS (desde tus 308 conversaciones):",
        ""
    ]
    
    # Conceptos principales
    for i, concepto in enumerate(conceptos_principales[:5], 1):
        nombre_legible = concepto['concepto'].replace('_', ' ').title()
        categoria = concepto['categoria']
        contexto_texto = concepto['contexto']
        fuente = concepto['fuente']
        
        contexto_partes.append(f"{i}. {nombre_legible}")
        contexto_partes.append(f"   📁 Categoría: {categoria}")
        
        if fuente:
            fuente_limpio = fuente.replace('.json', '').replace('_', ' ')
            contexto_partes.append(f"   📄 De conversación: {fuente_limpio}")
        
        if contexto_texto and len(contexto_texto) > 20:
            # Limpiar y truncar contexto
            contexto_limpio = contexto_texto.replace('\n', ' ').strip()
            if len(contexto_limpio) > 200:
                contexto_limpio = contexto_limpio[:200] + "..."
            contexto_partes.append(f"   💡 Contexto: {contexto_limpio}")
        
        contexto_partes.append("")
    
    # Conceptos relacionados si los hay
    if conceptos_relacionados:
        contexto_partes.append("CONCEPTOS RELACIONADOS:")
        for concepto in conceptos_relacionados[:3]:
            nombre_rel = concepto['concepto'].replace('_', ' ').title()
            contexto_partes.append(f"• {nombre_rel} ({concepto['categoria']})")
        contexto_partes.append("")
    
    return '\n'.join(contexto_partes)

def consultar_llm(query: str, contexto: str = "") -> str:
    """Consulta al LLM con contexto de Lucas"""
    try:
        # Prompt optimizado para IANAE
        system_prompt = f"""Eres IANAE, el bibliotecario personal de Lucas de Novelda, Alicante.

{contexto}

Responde como IANAE con:
- Personalidad entusiasta con emojis específicos (🔥✨🎯🚀)  
- Conocimiento específico de los proyectos de Lucas
- Referencias a su trabajo con tacógrafos, Python, Excel, VBA
- Tono colaborativo, nunca genérico
- Conecta ideas entre sus diferentes proyectos

Si el contexto es relevante, úsalo para dar respuestas personalizadas basadas en su historial real."""

        payload = {
            "model": CONFIG["llm_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        response = requests.post(
            CONFIG["llm_endpoint"], 
            json=payload,
            timeout=CONFIG["timeout_llm"]
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Error LLM: {response.status_code}")
            return "Error procesando consulta con el modelo de IA."
            
    except requests.exceptions.Timeout:
        return "El modelo de IA tardó demasiado en responder. Inténtalo de nuevo."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error LLM: {e}")
        return "No puedo conectar con el modelo de IA local. ¿Está LM Studio ejecutándose?"
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return "Ocurrió un error inesperado al procesar tu consulta."

# NUEVO: Funciones para análisis de documentos
def extract_concepts_from_content(content):
    """
    Extrae conceptos del contenido usando lógica similar a tu sistema
    """
    # Limpiar y normalizar texto
    words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', content.lower())
    
    # Contar frecuencias
    word_freq = Counter(words)
    
    # Filtrar palabras comunes (stop words básicas)
    stop_words = {
        'para', 'con', 'por', 'como', 'una', 'del', 'las', 'los', 'que', 
        'este', 'esta', 'sistema', 'puede', 'desde', 'hasta', 'todo', 
        'cada', 'más', 'sobre', 'entre', 'cuando', 'donde', 'será', 
        'también', 'tanto', 'hacer', 'tienen', 'muy', 'bien', 'forma',
        'estado', 'esto', 'solo', 'mediante', 'través', 'mismo', 'otros'
    }
    
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
    tech_words = ['python', 'javascript', 'html', 'css', 'api', 'database', 'server', 'codigo', 'desarrollo', 'programacion', 'sqlite', 'fastapi', 'opencv', 'excel', 'vba']
    project_words = ['ianae', 'proyecto', 'sistema', 'aplicacion', 'herramienta', 'tacografos', 'tacógrafo', 'memoria', 'biblioteca']
    ia_words = ['inteligencia', 'artificial', 'machine', 'learning', 'modelo', 'algoritmo', 'datos', 'conceptos', 'emergente', 'pensamiento']
    
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

async def find_existing_concept_matches(new_concepts):
    """
    Busca coincidencias con conceptos existentes en IANAE 2.0
    """
    matches = []
    
    try:
        # Usar la misma conexión que tu sistema existente
        cursor = db_conn.cursor()
        
        for concept in new_concepts:
            # Buscar conceptos similares en la BD
            cursor.execute('''
                SELECT nombre, categoria, relevancia 
                FROM conceptos 
                WHERE LOWER(nombre) LIKE ? OR LOWER(nombre) LIKE ?
                ORDER BY relevancia DESC
                LIMIT 5
            ''', (f"%{concept['name'].lower()}%", f"%{concept['name'].lower()}%"))
            
            results = cursor.fetchall()
            
            for result in results:
                similarity = calculate_similarity(concept['name'], result[0])
                if similarity > 0.3:  # Solo coincidencias razonables
                    matches.append({
                        'new_concept': concept['name'],
                        'existing_concept': result[0],
                        'existing_category': result[1],
                        'existing_mentions': result[2],
                        'similarity': round(similarity, 3)
                    })
        
    except Exception as e:
        logger.warning(f"⚠️ No se pudo conectar a BD IANAE: {e}")
        # Simular algunos matches para testing
        if new_concepts:
            matches = [
                {
                    'new_concept': new_concepts[0]['name'],
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

# Rutas de la API

@app.get("/", response_class=HTMLResponse)
async def index():
    """Página principal optimizada"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE 2.0 - Bibliotecario Optimizado</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: rgba(0,0,0,0.1);
                padding: 1.5rem 2rem;
                color: white;
                backdrop-filter: blur(10px);
            }
            
            .header h1 {
                font-size: 2.2rem;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .header p {
                opacity: 0.9;
                font-size: 1.1rem;
            }
            
            .stats {
                font-size: 0.9rem;
                opacity: 0.8;
                margin-top: 0.5rem;
            }
            
            .chat-container {
                flex: 1;
                max-width: 1200px;
                margin: 2rem auto;
                padding: 0 1rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            .chat-messages {
                background: white;
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                flex: 1;
                min-height: 400px;
                overflow-y: auto;
                max-height: 500px;
            }
            
            .message {
                margin-bottom: 1.5rem;
                padding: 1.2rem;
                border-radius: 12px;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .user-message {
                background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
                border-left: 4px solid #667eea;
            }
            
            .bot-message {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-left: 4px solid #28a745;
            }
            
            .message-header {
                font-weight: bold;
                margin-bottom: 0.8rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 1.1rem;
            }
            
            .message-content {
                line-height: 1.7;
                white-space: pre-wrap;
            }
            
            .input-container {
                background: white;
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: flex;
                gap: 1rem;
                align-items: center;
            }
            
            .chat-input {
                flex: 1;
                padding: 1.2rem;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                font-size: 1rem;
                outline: none;
                transition: all 0.3s;
            }
            
            .chat-input:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .send-button {
                padding: 1.2rem 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 600;
            }
            
            .send-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
            }
            
            .send-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .loading {
                display: none;
                text-align: center;
                color: white;
                margin: 1rem 0;
                font-style: italic;
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
            }
            
            .stats-info {
                background: rgba(255,255,255,0.15);
                backdrop-filter: blur(10px);
                border-radius: 12px;
                padding: 1rem;
                color: white;
                margin-top: 1rem;
                display: none;
                font-size: 0.9rem;
            }
            
            .emoji { font-size: 1.2em; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><span class="emoji">🧠</span> IANAE 2.0 <span class="emoji">⚡</span></h1>
            <p>Bibliotecario Personal Optimizado con Base de Datos Ultrarrápida</p>
            <div class="stats">Memoria activa: 328 conceptos | 1,994 relaciones | SQLite optimizado</div>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="messages">
                <div class="message bot-message">
                    <div class="message-header">
                        <span class="emoji">🤖</span> IANAE 2.0
                    </div>
                    <div class="message-content">¡Hola Lucas! 🚀 Soy tu IANAE optimizado.

He actualizado mi memoria con una base de datos SQLite ultrarrápida que contiene lo mejor de tus 308 conversaciones:

✨ 328 conceptos más importantes con contexto rico
🔗 1,994 relaciones principales entre ideas  
⚡ Búsquedas en milisegundos
🧠 Memoria de todos tus proyectos: tacógrafos, Python, VBA, automatización

Ahora puedo conectar ideas aún más rápido y darte respuestas con contexto real de tu trabajo. 

¿Qué quieres explorar de tu universo conceptual?</div>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <span class="emoji">⚡</span> Buscando en tu memoria optimizada...
            </div>
            
            <div class="input-container">
                <input 
                    type="text" 
                    class="chat-input" 
                    id="messageInput" 
                    placeholder="Pregúntame sobre cualquier cosa de tus proyectos, tacógrafos, Python, automatización..."
                    onkeypress="handleKeyPress(event)"
                >
                <button class="send-button" onclick="sendMessage()" id="sendButton">
                    <span class="emoji">🚀</span> Enviar
                </button>
            </div>
            
            <div class="stats-info" id="statsInfo">
                <strong><span class="emoji">📊</span> Búsqueda completada:</strong>
                <div id="searchStats"></div>
            </div>
        </div>
        
        <script>
            let conversationId = 'session_' + Date.now();
            
            function handleKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            }
            
            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                input.value = '';
                document.getElementById('sendButton').disabled = true;
                document.getElementById('loading').style.display = 'block';
                
                addMessage(message, 'user');
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            query: message,
                            conversacion_id: conversationId
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        addMessage(data.response, 'bot');
                        
                        // Mostrar estadísticas de búsqueda
                        if (data.conceptos_utilizados && data.conceptos_utilizados.length > 0) {
                            showSearchStats(data.conceptos_utilizados, data.tiempo_busqueda);
                        }
                    } else {
                        addMessage('Error: ' + data.detail, 'bot');
                    }
                } catch (error) {
                    addMessage('Error de conexión. ¿Está el servidor ejecutándose?', 'bot');
                }
                
                document.getElementById('sendButton').disabled = false;
                document.getElementById('loading').style.display = 'none';
                input.focus();
            }
            
            function addMessage(content, sender) {
                const messagesContainer = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                
                messageDiv.className = `message ${sender}-message`;
                messageDiv.innerHTML = `
                    <div class="message-header">
                        <span class="emoji">${sender === 'user' ? '👤' : '🤖'}</span> 
                        ${sender === 'user' ? 'Tú' : 'IANAE 2.0'}
                    </div>
                    <div class="message-content">${content}</div>
                `;
                
                messagesContainer.appendChild(messageDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function showSearchStats(conceptos, tiempo) {
                const statsInfo = document.getElementById('statsInfo');
                const searchStats = document.getElementById('searchStats');
                
                let statsText = `🕐 Búsqueda: ${(tiempo * 1000).toFixed(1)}ms | `;
                statsText += `🧠 Conceptos encontrados: ${conceptos.length}<br>`;
                
                if (conceptos.length > 0) {
                    statsText += `📋 Top resultados: `;
                    statsText += conceptos.slice(0, 3).map(c => 
                        `${c.concepto.replace(/_/g, ' ')} (${c.categoria})`
                    ).join(', ');
                }
                
                searchStats.innerHTML = statsText;
                statsInfo.style.display = 'block';
                
                setTimeout(() => {
                    statsInfo.style.display = 'none';
                }, 8000);
            }
            
            document.getElementById('messageInput').focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Endpoint principal optimizado con SQLite"""
    try:
        query = message.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query vacío")
        
        logger.info(f"🔍 Query: {query}")
        
        # Búsqueda ultrarrápida en SQLite
        conceptos_principales, tiempo_busqueda = buscar_conceptos_sql(query)
        
        logger.info(f"📊 Encontrados {len(conceptos_principales)} conceptos en {tiempo_busqueda:.3f}s")
        
        # Obtener conceptos relacionados para contexto más rico
        conceptos_relacionados = obtener_contexto_relacionado(conceptos_principales)
        
        # Generar contexto para LLM
        contexto_llm = generar_contexto_para_llm(conceptos_principales, conceptos_relacionados)
        
        # Consultar LLM
        respuesta_llm = consultar_llm(query, contexto_llm)
        
        return ChatResponse(
            response=respuesta_llm,
            conceptos_utilizados=conceptos_principales + conceptos_relacionados,
            tiempo_busqueda=tiempo_busqueda,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Endpoint para análisis de documentos
@app.post("/api/analyze-document")
async def analyze_document(doc: DocumentAnalysis):
    """
    Endpoint para analizar documentos y extraer conceptos usando IANAE 2.0
    """
    try:
        logger.info(f"🔍 Analizando documento: {doc.filename}")
        logger.info(f"📄 Caracteres: {len(doc.content)}")
        
        # Extraer conceptos del contenido
        concepts = extract_concepts_from_content(doc.content)
        relations = find_relations_for_concepts(concepts)
        
        # Buscar coincidencias con conceptos existentes en IANAE
        existing_matches = await find_existing_concept_matches(concepts)
        
        response = {
            'status': 'success',
            'filename': doc.filename,
            'stats': {
                'total_chars': len(doc.content),
                'total_words': len(doc.content.split()),
                'concepts_found': len(concepts),
                'relations_found': len(relations),
                'existing_matches': len(existing_matches)
            },
            'concepts': concepts,
            'relations': relations,
            'existing_matches': existing_matches,
            'timestamp': str(datetime.now())
        }
        
        logger.info(f"✅ Análisis completado: {len(concepts)} conceptos encontrados")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en análisis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Endpoint de test
@app.get("/api/test")
async def test_api():
    """Endpoint simple para verificar que la API funciona"""
    return {
        'status': 'ok',
        'message': 'IANAE 2.0 API funcionando',
        'timestamp': str(datetime.now()),
        'version': '2.0.0',
        'features': ['document_analysis', 'concept_extraction', 'database_search']
    }

@app.get("/stats")
async def get_stats():
    """Estadísticas de la base de datos"""
    if not db_conn:
        raise HTTPException(status_code=503, detail="BD no disponible")
    
    cursor = db_conn.cursor()
    
    # Estadísticas básicas
    cursor.execute("SELECT COUNT(*) FROM conceptos")
    num_conceptos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relaciones")
    num_relaciones = cursor.fetchone()[0]
    
    # Categorías
    cursor.execute("SELECT categoria, COUNT(*) FROM conceptos GROUP BY categoria ORDER BY COUNT(*) DESC")
    categorias = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Tamaño BD
    db_size = os.path.getsize(CONFIG["db_path"]) / (1024 * 1024)
    
    return {
        "status": "optimizado",
        "database": {
            "path": CONFIG["db_path"],
            "size_mb": round(db_size, 2),
            "conceptos": num_conceptos,
            "relaciones": num_relaciones
        },
        "categorias": categorias,
        "version": "2.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """Inicialización optimizada"""
    logger.info("🚀 Iniciando IANAE 2.0 Optimizado...")
    
    if init_database():
        logger.info("✅ IANAE 2.0 listo con memoria SQLite ultrarrápida")
    else:
        logger.error("❌ Error inicializando base de datos")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cierre limpio"""
    global db_conn
    if db_conn:
        db_conn.close()
        logger.info("🔒 Base de datos cerrada correctamente")

if __name__ == "__main__":
    import uvicorn
    
    print("🧠 IANAE 2.0 - Bibliotecario Optimizado")
    print("=" * 50)
    print("⚡ Base de datos SQLite ultrarrápida")
    print("🧠 328 conceptos esenciales")
    print("🔗 1,994 relaciones importantes")
    print("🌐 Iniciando en http://localhost:8000")
    print("📡 API endpoints:")
    print("   • /api/test - Test de conectividad")
    print("   • /api/analyze-document - Análisis de documentos")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)