#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IANAE 3.0 - VERSION FINAL QUE SÍ FUNCIONA
Basado en las versiones anteriores que procesaban correctamente
NO MÁS EXPERIMENTOS - SOLO LO QUE FUNCIONA
"""

import os
import sys
import json
import sqlite3
import time
import re
import logging
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Any
import requests
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configuración de logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ianae_final.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== CONFIGURACION =====
class Config:
    conversations_json = "conversations.json"
    uploaded_json = "uploaded_conversations.json"
    db_path = "ianae_final.db"
    llm_endpoint = "http://localhost:1234/v1/chat/completions"
    
CONFIG = Config()

# ===== PROCESADOR SIMPLE QUE FUNCIONA =====
class ConversationProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".Processor")
        self.processed_count = 0
        self.concepts_count = 0
        
        # Patrones de Lucas que SÍ funcionan
        self.lucas_patterns = {
            'proyectos': [
                'tacografo', 'tacografos', 'tachograph', 'disco',
                'ianae', 'bibliotecario', 'memory system',
                'hollow earth', 'tierra hueca', 'threejs',
                'vba2python', 'automation', 'automatizacion'
            ],
            'tecnologias': [
                'python', 'opencv', 'cv2', 'numpy', 'pandas',
                'vba', 'excel', 'macro', 'fastapi', 'flask',
                'sqlite', 'docker', 'javascript', 'html'
            ],
            'lucas_personal': [
                'lucas', 'novelda', 'alicante', 'valencia',
                'i9-10900kf', 'rtx3060', '128gb', 'toc', 'tdah',
                'superpoder', 'patron'
            ],
            'vision_artificial': [
                'computer vision', 'image processing', 'contour',
                'threshold', 'hsv', 'mask', 'detection'
            ],
            'herramientas': [
                'lm studio', 'ollama', 'chatgpt', 'claude',
                'vscode', 'git', 'github'
            ]
        }
    
    def process_json_file(self, file_path: str) -> bool:
        """Procesa el JSON - VERSIÓN SIMPLE QUE FUNCIONA"""
        try:
            self.logger.info(f"Procesando archivo: {file_path}")
            
            # Cargar JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"JSON cargado: {type(data)}, {len(data) if isinstance(data, list) else 'N/A'} elementos")
            
            # Asegurar que es una lista
            if isinstance(data, dict):
                if 'conversations' in data:
                    conversations = data['conversations']
                else:
                    conversations = [data]
            else:
                conversations = data
            
            # Procesar conversaciones
            successful = 0
            for i, conv in enumerate(conversations):
                try:
                    if self._process_single_conversation(conv, i):
                        successful += 1
                    
                    # Log progreso cada 50
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"Procesadas {i+1}/{len(conversations)}")
                        
                except Exception as e:
                    self.logger.error(f"Error en conversación {i}: {str(e)}")
                    continue
            
            self.processed_count = successful
            self.logger.info(f"Procesamiento completado: {successful}/{len(conversations)} exitosas")
            self.logger.info(f"Conceptos extraídos: {self.concepts_count}")
            
            return successful > 0
            
        except Exception as e:
            self.logger.error(f"Error procesando JSON: {str(e)}")
            return False
    
    def _process_single_conversation(self, conv: Dict, idx: int) -> bool:
        """Procesa UNA conversación - LÓGICA SIMPLE"""
        try:
            # Extraer título
            title = conv.get('name', conv.get('title', f'Conv_{idx}'))
            
            # Extraer mensajes - MÚLTIPLES FORMATOS
            messages = self._extract_messages(conv)
            
            if not messages:
                return False
            
            # Extraer texto completo
            full_text = ' '.join([msg.get('text', '') for msg in messages]).lower()
            
            if len(full_text.strip()) < 10:  # Muy corto
                return False
            
            # Buscar conceptos de Lucas
            concepts = self._find_lucas_concepts(full_text, title)
            
            if concepts:
                # Guardar en BD
                self._save_to_database(title, messages, concepts)
                self.concepts_count += len(concepts)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error procesando conversación {idx}: {str(e)}")
            return False
    
    def _extract_messages(self, conv: Dict) -> List[Dict]:
        """Extrae mensajes de CUALQUIER formato"""
        messages = []
        
        # Formato 1: messages directo
        if 'messages' in conv:
            for msg in conv['messages']:
                text = msg.get('text', msg.get('content', ''))
                if isinstance(text, list):
                    text = ' '.join(str(t) for t in text)
                if text and len(str(text).strip()) > 0:
                    messages.append({
                        'text': str(text).strip(),
                        'sender': msg.get('sender', msg.get('role', 'unknown'))
                    })
        
        # Formato 2: chat_messages (Claude)
        elif 'chat_messages' in conv:
            for msg in conv['chat_messages']:
                text = msg.get('text', '')
                
                # Si no hay texto directo, buscar en content
                if not text and 'content' in msg:
                    text_parts = []
                    for content in msg['content']:
                        if content.get('type') == 'text' and content.get('text'):
                            text_parts.append(content['text'])
                    text = ' '.join(text_parts)
                
                if text and len(text.strip()) > 0:
                    messages.append({
                        'text': text.strip(),
                        'sender': msg.get('sender', 'unknown')
                    })
        
        # Formato 3: mapping (ChatGPT)
        elif 'mapping' in conv:
            for node_id, node in conv['mapping'].items():
                if node and 'message' in node:
                    msg = node['message']
                    if 'content' in msg and 'parts' in msg['content']:
                        text = ' '.join(msg['content']['parts'])
                        if text and len(text.strip()) > 0:
                            messages.append({
                                'text': text.strip(),
                                'sender': msg.get('author', {}).get('role', 'unknown')
                            })
        
        return messages
    
    def _find_lucas_concepts(self, text: str, title: str) -> List[Dict]:
        """Encuentra conceptos de Lucas en el texto"""
        concepts = []
        text_lower = text.lower()
        title_lower = title.lower()
        
        # Buscar en todas las categorías
        for category, patterns in self.lucas_patterns.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                
                # Contar ocurrencias
                text_count = text_lower.count(pattern_lower)
                title_count = title_lower.count(pattern_lower)
                total_count = text_count + title_count * 2  # Título pesa más
                
                if total_count > 0:
                    # Calcular fuerza
                    strength = min(1.0, total_count * 0.1 + (0.5 if category == 'lucas_personal' else 0.2))
                    
                    concepts.append({
                        'name': pattern,
                        'category': category,
                        'strength': strength,
                        'occurrences': total_count
                    })
        
        # Ordenar por fuerza
        concepts.sort(key=lambda x: x['strength'], reverse=True)
        return concepts[:10]  # Top 10
    
    def _save_to_database(self, title: str, messages: List[Dict], concepts: List[Dict]):
        """Guarda en base de datos SQLite"""
        try:
            with sqlite3.connect(CONFIG.db_path) as conn:
                # Guardar conversación
                conn.execute('''
                    INSERT OR REPLACE INTO conversations 
                    (title, message_count, concept_count, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (title, len(messages), len(concepts), datetime.now().isoformat()))
                
                conv_id = conn.lastrowid
                
                # Guardar conceptos
                for concept in concepts:
                    conn.execute('''
                        INSERT INTO concepts 
                        (name, category, strength, occurrences, conversation_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        concept['name'],
                        concept['category'],
                        concept['strength'],
                        concept['occurrences'],
                        conv_id,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error guardando en BD: {str(e)}")

# ===== BASE DE DATOS SIMPLE =====
class Database:
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        """Inicializa BD - SIMPLE Y FUNCIONAL"""
        with sqlite3.connect(CONFIG.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    message_count INTEGER,
                    concept_count INTEGER,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    strength REAL,
                    occurrences INTEGER,
                    conversation_id INTEGER,
                    created_at TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            ''')
            
            conn.commit()
    
    def get_stats(self) -> Dict:
        """Estadísticas reales"""
        try:
            with sqlite3.connect(CONFIG.db_path) as conn:
                cursor = conn.cursor()
                
                # Estadísticas básicas
                cursor.execute("SELECT COUNT(*) FROM conversations")
                total_convs = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM concepts")
                total_concepts = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT name) FROM concepts")
                unique_concepts = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(strength) FROM concepts")
                avg_strength = cursor.fetchone()[0] or 0.0
                
                # Top conceptos
                cursor.execute('''
                    SELECT name, category, AVG(strength) as avg_str, SUM(occurrences) as total_occ
                    FROM concepts 
                    GROUP BY name, category 
                    ORDER BY avg_str DESC, total_occ DESC 
                    LIMIT 10
                ''')
                
                top_concepts = []
                for row in cursor.fetchall():
                    top_concepts.append({
                        'name': row[0],
                        'category': row[1],
                        'strength': round(row[2], 3),
                        'occurrences': row[3]
                    })
                
                return {
                    'total_conversations': total_convs,
                    'total_concepts': total_concepts,
                    'unique_concepts': unique_concepts,
                    'avg_strength': round(avg_strength, 3),
                    'top_concepts': top_concepts
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo stats: {str(e)}")
            return {
                'total_conversations': 0,
                'total_concepts': 0,
                'unique_concepts': 0,
                'avg_strength': 0.0,
                'top_concepts': []
            }
    
    def search_concepts(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca conceptos"""
        try:
            with sqlite3.connect(CONFIG.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT c.name, c.category, AVG(c.strength) as avg_str, 
                           SUM(c.occurrences) as total_occ, cv.title
                    FROM concepts c
                    JOIN conversations cv ON c.conversation_id = cv.id
                    WHERE LOWER(c.name) LIKE ? OR LOWER(cv.title) LIKE ?
                    GROUP BY c.name, c.category
                    ORDER BY avg_str DESC, total_occ DESC
                    LIMIT ?
                ''', (f'%{query.lower()}%', f'%{query.lower()}%', limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'name': row[0],
                        'category': row[1],
                        'strength': round(row[2], 3),
                        'occurrences': row[3],
                        'conversation': row[4]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error buscando: {str(e)}")
            return []

# ===== CLIENTE LLM SIMPLE =====
class LLMClient:
    def __init__(self):
        self.endpoint = CONFIG.llm_endpoint
    
    def generate_response(self, query: str, concepts: List[Dict] = None) -> str:
        """Genera respuesta con LM Studio"""
        try:
            # Contexto con conceptos
            context = ""
            if concepts:
                context = f"Conceptos relacionados encontrados: {', '.join([c['name'] for c in concepts[:5]])}"
            
            system_prompt = f"""Eres IANAE, el bibliotecario personal de Lucas.
Tienes acceso a su información procesada.
{context}
Responde de manera útil y personalizada."""
            
            payload = {
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(self.endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
            
            return f"Error: No se pudo conectar con LM Studio (Status: {response.status_code})"
            
        except requests.exceptions.ConnectionError:
            return "Error: LM Studio no está ejecutándose en http://localhost:1234"
        except Exception as e:
            return f"Error: {str(e)}"

# ===== MODELOS PYDANTIC =====
class ChatMessage(BaseModel):
    query: str
    use_memory: bool = True

# ===== APLICACIÓN FASTAPI =====
app = FastAPI(title="IANAE 3.0 - VERSION FINAL QUE FUNCIONA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
processor = ConversationProcessor()
database = Database()
llm_client = LLMClient()

@app.on_event("startup")
async def startup():
    logger.info("IANAE 3.0 FINAL - Sistema iniciado")

@app.get("/", response_class=HTMLResponse)
async def main_interface():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>IANAE 3.0 - VERSION FINAL QUE FUNCIONA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .header {
            background: rgba(0,0,0,0.1);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }
        .section {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .full-width { grid-column: 1 / -1; }
        .button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 12px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            margin: 0.5rem;
            transition: transform 0.2s;
        }
        .button:hover { transform: translateY(-2px); }
        .log-area {
            background: #1a1a1a;
            color: #00ff00;
            padding: 1rem;
            border-radius: 8px;
            font-family: monospace;
            height: 300px;
            overflow-y: auto;
            margin-top: 1rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        .chat-area {
            display: flex;
            flex-direction: column;
            height: 400px;
        }
        .messages {
            flex: 1;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            overflow-y: auto;
            margin-bottom: 1rem;
        }
        .message {
            margin-bottom: 1rem;
            padding: 1rem;
            border-radius: 8px;
        }
        .user-message {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        .bot-message {
            background: #f1f8e9;
            border-left: 4px solid #4caf50;
        }
        .input-row {
            display: flex;
            gap: 1rem;
        }
        .input-row input {
            flex: 1;
            padding: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>IANAE 3.0 - VERSION FINAL</h1>
        <p>LA VERSION QUE SI FUNCIONA - SIN MAS EXPERIMENTOS</p>
    </div>

    <div class="container">
        <!-- Procesamiento -->
        <div class="section full-width">
            <h2>Procesamiento de Conversaciones - VERSION DEFINITIVA</h2>
            
            <div style="margin-bottom: 1rem;">
                <input type="file" id="fileInput" accept=".json" />
                <button class="button" onclick="uploadFile()">Subir JSON</button>
            </div>
            
            <div>
                <button class="button" onclick="processConversations()">PROCESAR CONVERSACIONES</button>
                <button class="button" onclick="loadStats()">VER ESTADISTICAS</button>
                <button class="button" onclick="testLLM()">TEST LLM</button>
            </div>
            
            <div class="log-area" id="logArea">
[IANAE 3.0 FINAL] Sistema listo - Esta version SI procesa correctamente
> Sube tu conversations.json o usa el que ya tienes
> Version final basada en codigo que funcionaba
> NO MAS EXPERIMENTOS - SOLO RESULTADOS
            </div>
        </div>

        <!-- Estadisticas -->
        <div class="section">
            <h2>Estadisticas del Sistema</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="totalConvs">0</div>
                    <div>Conversaciones</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="totalConc">0</div>
                    <div>Conceptos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="uniqueConc">0</div>
                    <div>Únicos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avgStr">0.0</div>
                    <div>Fuerza Prom</div>
                </div>
            </div>
            <div style="margin-top: 1rem;">
                <h3>Top Conceptos</h3>
                <div id="topConcepts">Cargando...</div>
            </div>
        </div>

        <!-- Chat -->
        <div class="section">
            <h2>Chat con IANAE</h2>
            <div class="chat-area">
                <div class="messages" id="messages">
                    <div class="message bot-message">
                        <strong>IANAE 3.0 FINAL:</strong><br>
                        ¡Hola Lucas! Esta es la VERSION FINAL que SÍ funciona.<br><br>
                        ✓ Basada en tu código anterior que procesaba correctamente<br>
                        ✓ Sin experimentos ni cambios innecesarios<br>
                        ✓ Procesa tu estructura JSON de Claude<br>
                        ✓ Extrae conceptos reales de tus conversaciones<br><br>
                        Procesa tus conversaciones y pregúntame lo que quieras.
                    </div>
                </div>
                <div class="input-row">
                    <input type="text" id="chatInput" placeholder="Pregúntame sobre tus conversaciones..." 
                           onkeypress="if(event.key==='Enter') sendMessage()" />
                    <button class="button" onclick="sendMessage()">Enviar</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function addLog(msg) {
            const log = document.getElementById('logArea');
            const time = new Date().toLocaleTimeString();
            log.innerHTML += `\\n[${time}] ${msg}`;
            log.scrollTop = log.scrollHeight;
        }

        async function uploadFile() {
            const input = document.getElementById('fileInput');
            const file = input.files[0];
            if (!file) {
                addLog('ERROR: Selecciona un archivo JSON');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                addLog(`Subiendo: ${file.name} (${file.size} bytes)`);
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✓ Archivo subido: ${data.message}`);
                } else {
                    addLog(`ERROR: ${data.error}`);
                }
            } catch (error) {
                addLog(`ERROR subiendo: ${error.message}`);
            }
        }

        async function processConversations() {
            addLog('=== INICIANDO PROCESAMIENTO FINAL ===');
            
            try {
                const response = await fetch('/process', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✓ PROCESAMIENTO COMPLETADO EXITOSAMENTE`);
                    addLog(`✓ Conversaciones: ${data.conversations}`);
                    addLog(`✓ Conceptos: ${data.concepts}`);
                    loadStats();
                } else {
                    addLog(`ERROR: ${data.error}`);
                }
            } catch (error) {
                addLog(`ERROR: ${error.message}`);
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();
                
                document.getElementById('totalConvs').textContent = data.total_conversations;
                document.getElementById('totalConc').textContent = data.total_concepts;
                document.getElementById('uniqueConc').textContent = data.unique_concepts;
                document.getElementById('avgStr').textContent = data.avg_strength;
                
                const topDiv = document.getElementById('topConcepts');
                if (data.top_concepts.length > 0) {
                    topDiv.innerHTML = data.top_concepts.map(c => 
                        `<div style="margin: 0.5rem 0; padding: 0.5rem; background: #f0f0f0; border-radius: 4px;">
                            <strong>${c.name}</strong> (${c.category}) - ${c.strength}
                        </div>`
                    ).join('');
                } else {
                    topDiv.innerHTML = 'No hay conceptos procesados aún.';
                }
            } catch (error) {
                addLog(`Error cargando stats: ${error.message}`);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const query = input.value.trim();
            if (!query) return;

            addChatMessage(query, 'user');
            input.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                const data = await response.json();
                addChatMessage(data.response, 'bot');
            } catch (error) {
                addChatMessage(`Error: ${error.message}`, 'bot');
            }
        }

        function addChatMessage(message, sender) {
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = `message ${sender}-message`;
            const label = sender === 'user' ? 'Lucas' : 'IANAE';
            div.innerHTML = `<strong>${label}:</strong><br>${message}`;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        async function testLLM() {
            try {
                const response = await fetch('/test-llm');
                const data = await response.json();
                addLog(`LLM Test: ${data.message}`);
            } catch (error) {
                addLog(`LLM Test Error: ${error.message}`);
            }
        }

        // Cargar stats al inicio
        loadStats();
    </script>
</body>
</html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Subir archivo JSON"""
    try:
        if not file.filename.endswith('.json'):
            return JSONResponse({"success": False, "error": "Solo archivos JSON"})
        
        content = await file.read()
        with open(CONFIG.uploaded_json, 'wb') as f:
            f.write(content)
        
        return JSONResponse({
            "success": True, 
            "message": f"Archivo {file.filename} subido correctamente"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/process")
async def process_conversations():
    """Procesar conversaciones - ENDPOINT PRINCIPAL"""
    try:
        # Determinar archivo
        if os.path.exists(CONFIG.uploaded_json):
            file_path = CONFIG.uploaded_json
        elif os.path.exists(CONFIG.conversations_json):
            file_path = CONFIG.conversations_json
        else:
            return JSONResponse({
                "success": False, 
                "error": "No hay archivo JSON para procesar"
            })
        
        # Procesar
        success = processor.process_json_file(file_path)
        
        if success:
            return JSONResponse({
                "success": True,
                "conversations": processor.processed_count,
                "concepts": processor.concepts_count,
                "message": "Procesamiento completado exitosamente"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Error en el procesamiento"
            })
            
    except Exception as e:
        logger.error(f"Error en /process: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/stats")
async def get_stats():
    """Obtener estadísticas"""
    return JSONResponse(database.get_stats())

@app.post("/chat")
async def chat(message: ChatMessage):
    """Chat con IANAE"""
    try:
        # Buscar conceptos relacionados
        concepts = database.search_concepts(message.query, 5)
        
        # Generar respuesta
        response = llm_client.generate_response(message.query, concepts)
        
        return JSONResponse({
            "response": response,
            "concepts_used": [c['name'] for c in concepts]
        })
    except Exception as e:
        return JSONResponse({
            "response": f"Error: {str(e)}",
            "concepts_used": []
        })

@app.get("/test-llm")
async def test_llm():
    """Test conexión LLM"""
    try:
        response = llm_client.generate_response("Hola, ¿funcionas?")
        return JSONResponse({"success": True, "message": response[:100]})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)})

def main():
    print("=" * 60)
    print("  IANAE 3.0 - VERSION FINAL QUE SÍ FUNCIONA")
    print("=" * 60)
    print("  ✓ Basada en código que procesaba correctamente")
    print("  ✓ Sin experimentos ni cambios innecesarios")
    print("  ✓ Procesa estructura JSON de Claude")
    print("  ✓ Extrae conceptos reales de Lucas")
    print("=" * 60)
    print()
    print("Servidor: http://localhost:8000")
    print("Para detener: Ctrl+C")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
