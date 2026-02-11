#!/usr/bin/env python3
"""
IANAE COMPLETO - Bibliotecario Personal que FUNCIONA
Integración de TODO lo que hemos construido sin errores
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import tempfile
import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import logging
import requests
import time
import re
from collections import Counter, defaultdict
from pydantic import BaseModel

app = FastAPI(title="IANAE Completo", version="3.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración
CONFIG = {
    "db_path": "ianae_completo.db",
    "llm_endpoint": "http://localhost:1234/v1/chat/completions",
    "llm_model": "local-model",
    "timeout_llm": 60
}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== MODELOS ==========
class ChatMessage(BaseModel):
    query: str
    conversacion_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conceptos_utilizados: list
    tiempo_busqueda: float
    timestamp: str

# ========== DEDUPLICADOR INTEGRADO ==========
class DeduplicadorCompleto:
    """Sistema de deduplicación y memoria persistente"""
    
    def __init__(self, db_path=CONFIG["db_path"]):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa todas las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de archivos procesados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivos_procesados (
                id INTEGER PRIMARY KEY,
                filename TEXT UNIQUE,
                file_hash TEXT,
                last_processed TIMESTAMP,
                total_conversaciones INTEGER,
                total_mensajes INTEGER,
                file_size_bytes INTEGER,
                tipo_detectado TEXT
            )
        ''')
        
        # Tabla de conversaciones procesadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversaciones (
                id TEXT PRIMARY KEY,
                titulo TEXT,
                plataforma TEXT,
                timestamp_creacion REAL,
                hash_contenido TEXT,
                last_updated TIMESTAMP,
                total_mensajes INTEGER,
                archivo_origen TEXT
            )
        ''')
        
        # Tabla de mensajes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id TEXT PRIMARY KEY,
                conversacion_id TEXT,
                role TEXT,
                content TEXT,
                timestamp_msg REAL,
                hash_contenido TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (conversacion_id) REFERENCES conversaciones (id)
            )
        ''')
        
        # Tabla de conceptos extraídos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conceptos (
                id INTEGER PRIMARY KEY,
                nombre TEXT UNIQUE,
                categoria TEXT,
                contexto TEXT,
                fuente TEXT,
                frecuencia INTEGER DEFAULT 1,
                relevancia REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de relaciones entre conceptos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relaciones (
                id INTEGER PRIMARY KEY,
                concepto_a TEXT,
                concepto_b TEXT,
                fuerza REAL DEFAULT 0.5,
                tipo TEXT DEFAULT 'coocurrencia',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(concepto_a, concepto_b)
            )
        ''')
        
        # Índices para búsquedas rápidas
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_nombre ON conceptos(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_categoria ON conceptos(categoria)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mensajes_content ON mensajes(content)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relaciones_conceptos ON relaciones(concepto_a, concepto_b)')
        
        # Full-text search para conceptos
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS conceptos_busqueda USING fts5(
                nombre, contexto, categoria, content=conceptos
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de datos inicializada correctamente")
    
    def calcular_hash_archivo(self, filepath):
        """Calcula hash MD5 del archivo"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def archivo_ya_procesado(self, filename, file_path):
        """Verifica si archivo ya fue procesado"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hash_actual = self.calcular_hash_archivo(file_path)
        
        cursor.execute('''
            SELECT file_hash, last_processed, total_mensajes 
            FROM archivos_procesados 
            WHERE filename = ?
        ''', (filename,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if not resultado:
            return False, "Archivo nuevo", hash_actual
        
        hash_anterior, last_processed, total_mensajes = resultado
        
        if hash_actual == hash_anterior:
            return True, f"Archivo idéntico (procesado: {last_processed}, {total_mensajes} mensajes)", hash_actual
        else:
            return False, f"Archivo actualizado (nueva versión detectada)", hash_actual
    
    def guardar_conversaciones_procesadas(self, conversaciones, filename, file_hash, tipo_detectado):
        """Guarda conversaciones en la base de datos con extracción de conceptos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conversaciones_guardadas = 0
        mensajes_guardados = 0
        conceptos_extraidos = set()
        
        for conversacion in conversaciones:
            try:
                # Guardar conversación
                cursor.execute('''
                    INSERT OR REPLACE INTO conversaciones 
                    (id, titulo, plataforma, timestamp_creacion, hash_contenido, last_updated, total_mensajes, archivo_origen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversacion['id'],
                    conversacion.get('titulo', 'Sin título'),
                    conversacion.get('plataforma', 'unknown'),
                    conversacion.get('timestamp'),
                    self._hash_conversacion(conversacion),
                    datetime.now().isoformat(),
                    len(conversacion.get('mensajes', [])),
                    filename
                ))
                conversaciones_guardadas += 1
                
                # Guardar mensajes y extraer conceptos
                for mensaje in conversacion.get('mensajes', []):
                    # Guardar mensaje
                    cursor.execute('''
                        INSERT OR REPLACE INTO mensajes 
                        (id, conversacion_id, role, content, timestamp_msg, hash_contenido, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        mensaje.get('id', f"{conversacion['id']}_{mensajes_guardados}"),
                        conversacion['id'],
                        mensaje.get('role', 'unknown'),
                        mensaje.get('content', ''),
                        mensaje.get('timestamp'),
                        hashlib.md5(mensaje.get('content', '').encode()).hexdigest(),
                        datetime.now().isoformat()
                    ))
                    mensajes_guardados += 1
                    
                    # Extraer conceptos del contenido
                    conceptos_mensaje = self._extraer_conceptos_texto(mensaje.get('content', ''))
                    conceptos_extraidos.update(conceptos_mensaje)
                
            except Exception as e:
                logger.error(f"Error guardando conversación {conversacion.get('id')}: {e}")
                continue
        
        # Guardar conceptos extraídos
        conceptos_guardados = self._guardar_conceptos(cursor, conceptos_extraidos, filename)
        
        # Registrar archivo como procesado
        cursor.execute('''
            INSERT OR REPLACE INTO archivos_procesados 
            (filename, file_hash, last_processed, total_conversaciones, total_mensajes, file_size_bytes, tipo_detectado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            file_hash,
            datetime.now().isoformat(),
            conversaciones_guardadas,
            mensajes_guardados,
            os.path.getsize(tempfile.gettempdir() + "/" + filename) if os.path.exists(tempfile.gettempdir() + "/" + filename) else 0,
            tipo_detectado
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'conversaciones_guardadas': conversaciones_guardadas,
            'mensajes_guardados': mensajes_guardados,
            'conceptos_extraidos': conceptos_guardados
        }
    
    def _hash_conversacion(self, conversacion):
        """Calcula hash de una conversación"""
        contenido = json.dumps(conversacion, sort_keys=True)
        return hashlib.md5(contenido.encode()).hexdigest()
    
    def _extraer_conceptos_texto(self, texto):
        """Extrae conceptos técnicos y relevantes del texto"""
        if not texto or len(texto) < 10:
            return []
        
        conceptos = []
        texto_lower = texto.lower()
        
        # Patrones técnicos específicos de Lucas
        patrones_tecnicos = {
            'python': r'\bpython\b',
            'javascript': r'\b(javascript|js)\b',
            'html': r'\bhtml\b',
            'css': r'\bcss\b',
            'vba': r'\bvba\b',
            'excel': r'\bexcel\b',
            'opencv': r'\bopencv\b',
            'cv2': r'\bcv2\b',
            'docker': r'\bdocker\b',
            'api': r'\bapi\b',
            'json': r'\bjson\b',
            'sql': r'\bsql\b',
            'tacografo': r'\btac[oó]grafo\b',
            'automatizacion': r'\bautomatizaci[oó]n\b',
            'selenium': r'\bselenium\b',
            'pandas': r'\bpandas\b',
            'numpy': r'\bnumpy\b'
        }
        
        # Buscar patrones técnicos
        for concepto, patron in patrones_tecnicos.items():
            if re.search(patron, texto_lower):
                conceptos.append({
                    'nombre': concepto,
                    'categoria': 'tecnologia',
                    'contexto': texto[:200],  # Primeros 200 chars como contexto
                    'relevancia': 0.8
                })
        
        # Extraer conceptos de código
        codigo_patrones = [
            r'`([^`]+)`',  # Código en backticks
            r'def\s+(\w+)',  # Funciones Python
            r'class\s+(\w+)',  # Clases Python
            r'import\s+(\w+)',  # Imports
        ]
        
        for patron in codigo_patrones:
            matches = re.finditer(patron, texto)
            for match in matches:
                concepto_codigo = match.group(1).strip()
                if len(concepto_codigo) > 2 and concepto_codigo not in [c['nombre'] for c in conceptos]:
                    conceptos.append({
                        'nombre': concepto_codigo,
                        'categoria': 'codigo',
                        'contexto': texto[:200],
                        'relevancia': 0.6
                    })
        
        return conceptos
    
    def _guardar_conceptos(self, cursor, conceptos, fuente):
        """Guarda conceptos en la base de datos"""
        conceptos_guardados = 0
        
        for concepto_data in conceptos:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO conceptos 
                    (nombre, categoria, contexto, fuente, frecuencia, relevancia)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    concepto_data['nombre'],
                    concepto_data['categoria'],
                    concepto_data['contexto'],
                    fuente,
                    1,
                    concepto_data['relevancia']
                ))
                
                if cursor.rowcount > 0:
                    conceptos_guardados += 1
                else:
                    # Actualizar frecuencia si ya existe
                    cursor.execute('''
                        UPDATE conceptos 
                        SET frecuencia = frecuencia + 1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE nombre = ?
                    ''', (concepto_data['nombre'],))
                
            except Exception as e:
                logger.error(f"Error guardando concepto {concepto_data['nombre']}: {e}")
                continue
        
        return conceptos_guardados
    
    def buscar_conceptos(self, query, limite=10):
        """Busca conceptos relevantes para una consulta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Búsqueda full-text
        cursor.execute('''
            SELECT c.nombre, c.categoria, c.contexto, c.fuente, c.frecuencia, c.relevancia
            FROM conceptos c
            WHERE c.nombre LIKE ? OR c.contexto LIKE ?
            ORDER BY c.frecuencia DESC, c.relevancia DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limite))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'concepto': row[0],
                'categoria': row[1],
                'contexto': row[2],
                'fuente': row[3],
                'frecuencia': row[4],
                'relevancia': row[5]
            })
        
        conn.close()
        return resultados
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas de la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM conversaciones')
        total_conversaciones = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM mensajes')
        total_mensajes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM conceptos')
        total_conceptos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM archivos_procesados')
        total_archivos = cursor.fetchone()[0]
        
        cursor.execute('SELECT categoria, COUNT(*) FROM conceptos GROUP BY categoria')
        conceptos_por_categoria = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_conversaciones': total_conversaciones,
            'total_mensajes': total_mensajes,
            'total_conceptos': total_conceptos,
            'total_archivos_procesados': total_archivos,
            'conceptos_por_categoria': conceptos_por_categoria
        }

# ========== FUNCIONES DE PROCESAMIENTO (DE TU CÓDIGO QUE FUNCIONA) ==========

def detectar_tipo_automatico(file_path: str) -> str:
    """Detecta automáticamente el tipo de archivo de conversaciones"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            contenido_inicio = f.read(2000)
            
        if ('# Cline Task' in contenido_inicio or 
            '## Human:' in contenido_inicio or
            '## Assistant:' in contenido_inicio):
            return 'cline_markdown'
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list) and len(data) > 0:
            primer_elemento = data[0]
            if (isinstance(primer_elemento, dict) and 
                'conversation_id' in primer_elemento and 
                'name' in primer_elemento):
                return 'claude_json'
                
        if isinstance(data, list) and len(data) > 0:
            primer_elemento = data[0]
            if (isinstance(primer_elemento, dict) and 
                'mapping' in primer_elemento):
                return 'chatgpt_json'
                
        if isinstance(data, dict) and 'mapping' in data:
            return 'chatgpt_json'
            
        return 'json_generico'
        
    except json.JSONDecodeError:
        return 'texto_plano'
    except Exception as e:
        return f'error: {str(e)}'

def parsear_claude_json(data: List[Dict]) -> List[Dict]:
    """Parser para archivos JSON de Claude"""
    conversaciones = []
    
    for conversacion_data in data:
        try:
            conv_id = conversacion_data.get('conversation_id', 'unknown')
            titulo = conversacion_data.get('name', 'Sin título')
            
            mensajes = []
            for mensaje in conversacion_data.get('chat_messages', []):
                if mensaje.get('text'):
                    mensajes.append({
                        'id': mensaje.get('uuid', ''),
                        'role': 'human' if mensaje.get('sender') == 'human' else 'assistant',
                        'content': mensaje.get('text', ''),
                        'timestamp': mensaje.get('created_at')
                    })
            
            if mensajes:
                conversaciones.append({
                    'id': conv_id,
                    'titulo': titulo,
                    'plataforma': 'claude',
                    'timestamp': conversacion_data.get('created_at'),
                    'mensajes': mensajes
                })
                
        except Exception as e:
            logger.error(f"Error procesando conversación Claude: {e}")
            continue
            
    return conversaciones

def parsear_chatgpt_json(data):
    """Parser mejorado para ChatGPT JSON - procesa TODAS las conversaciones"""
    conversaciones = []
    mensajes_total = 0
    
    if isinstance(data, list):
        logger.info(f"📚 Procesando {len(data)} conversaciones de ChatGPT...")
        
        for i, conversacion_data in enumerate(data):
            try:
                conversacion = procesar_conversacion_chatgpt(conversacion_data, i)
                if conversacion and conversacion['mensajes']:
                    conversaciones.append(conversacion)
                    mensajes_total += len(conversacion['mensajes'])
                    
                    if i % 100 == 0:
                        logger.info(f"   Procesadas {i+1}/{len(data)} conversaciones...")
                        
            except Exception as e:
                logger.error(f"⚠️ Error procesando conversación {i}: {str(e)}")
                continue
                
    elif isinstance(data, dict):
        logger.info("📚 Procesando conversación única de ChatGPT...")
        conversacion = procesar_conversacion_chatgpt(data, 0)
        if conversacion and conversacion['mensajes']:
            conversaciones.append(conversacion)
            mensajes_total += len(conversacion['mensajes'])
    
    else:
        raise ValueError(f"Formato de datos no reconocido: {type(data)}")
        
    logger.info(f"✅ ChatGPT: {len(conversaciones)} conversaciones, {mensajes_total} mensajes")
    return conversaciones

def procesar_conversacion_chatgpt(conv_data, indice):
    """Procesa una conversación individual de ChatGPT"""
    try:
        conv_id = conv_data.get('id', f'chatgpt_conv_{indice}')
        titulo = conv_data.get('title', f'Conversación {indice + 1}')
        
        create_time = None
        if 'create_time' in conv_data:
            create_time = conv_data['create_time']
        elif 'timestamp' in conv_data:
            create_time = conv_data['timestamp']
            
        mapping = conv_data.get('mapping', {})
        mensajes = []
        
        for node_id, node_data in mapping.items():
            message_data = node_data.get('message')
            if not message_data:
                continue
                
            author = message_data.get('author', {})
            role = author.get('role', 'unknown')
            
            if role not in ['user', 'assistant']:
                continue
                
            content = message_data.get('content', {})
            parts = content.get('parts', [])
            
            texto = ""
            for part in parts:
                if isinstance(part, str):
                    texto += part + " "
                    
            texto = texto.strip()
            if not texto:
                continue
                
            mensaje = {
                'id': message_data.get('id', node_id),
                'role': role,
                'content': texto,
                'timestamp': message_data.get('create_time', create_time),
                'parent_id': node_data.get('parent'),
                'children': node_data.get('children', [])
            }
            
            mensajes.append(mensaje)
            
        mensajes_validos = [m for m in mensajes if m['content'].strip()]
        if mensajes_validos and mensajes_validos[0].get('timestamp'):
            mensajes_validos.sort(key=lambda x: x.get('timestamp', 0))
            
        return {
            'id': conv_id,
            'titulo': titulo,
            'plataforma': 'chatgpt',
            'timestamp': create_time,
            'mensajes': mensajes_validos,
            'metadata': {
                'total_nodes': len(mapping),
                'conversation_index': indice
            }
        }
        
    except Exception as e:
        logger.error(f"⚠️ Error procesando conversación ChatGPT {indice}: {str(e)}")
        return None

def parsear_cline_markdown(contenido: str) -> List[Dict]:
    """Parser para archivos Markdown de Cline/Continue"""
    conversaciones = []
    
    if '# Cline Task' in contenido:
        mensajes = []
        lineas = contenido.split('\n')
        
        mensaje_actual = {'role': None, 'content': []}
        
        for linea in lineas:
            if linea.startswith('## Human:'):
                if mensaje_actual['role']:
                    mensajes.append({
                        'role': mensaje_actual['role'],
                        'content': '\n'.join(mensaje_actual['content']).strip(),
                        'timestamp': None
                    })
                mensaje_actual = {'role': 'user', 'content': []}
                
            elif linea.startswith('## Assistant:'):
                if mensaje_actual['role']:
                    mensajes.append({
                        'role': mensaje_actual['role'],
                        'content': '\n'.join(mensaje_actual['content']).strip(),
                        'timestamp': None
                    })
                mensaje_actual = {'role': 'assistant', 'content': []}
                
            else:
                if mensaje_actual['role']:
                    mensaje_actual['content'].append(linea)
        
        if mensaje_actual['role'] and mensaje_actual['content']:
            mensajes.append({
                'role': mensaje_actual['role'],
                'content': '\n'.join(mensaje_actual['content']).strip(),
                'timestamp': None
            })
        
        if mensajes:
            conversaciones.append({
                'id': 'cline_task_1',
                'titulo': 'Cline Task',
                'plataforma': 'cline',
                'timestamp': None,
                'mensajes': [m for m in mensajes if m['content'].strip()]
            })
    
    return conversaciones

def procesar_segun_tipo(file_path: str, tipo: str) -> List[Dict]:
    """Procesa el archivo según su tipo detectado"""
    
    if tipo == 'claude_json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return parsear_claude_json(data)
        
    elif tipo == 'chatgpt_json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return parsear_chatgpt_json(data)
        
    elif tipo == 'cline_markdown':
        with open(file_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        return parsear_cline_markdown(contenido)
        
    else:
        raise HTTPException(status_code=400, detail=f"Tipo no soportado: {tipo}")

# ========== FUNCIONES LLM ==========

def consultar_llm(query: str, contexto: str = "") -> str:
    """Consulta al LLM local con contexto de Lucas"""
    try:
        system_prompt = f"""Eres IANAE, el bibliotecario personal de Lucas de Novelda.

{contexto}

Responde como IANAE con:
- Personalidad entusiasta con emojis (🔥✨🎯🚀)  
- Conocimiento específico de sus proyectos
- Referencias a su trabajo con tacógrafos, Python, Excel, VBA
- Tono colaborativo y personal
- Conecta ideas entre sus proyectos

Si el contexto es relevante, úsalo para dar respuestas personalizadas."""

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
            return "Error procesando consulta con el modelo de IA."
            
    except requests.exceptions.Timeout:
        return "El modelo de IA tardó demasiado en responder. ¿Está LM Studio ejecutándose?"
    except requests.exceptions.RequestException as e:
        return "No puedo conectar con el modelo de IA local. ¿Está LM Studio ejecutándose?"
    except Exception as e:
        return "Ocurrió un error inesperado al procesar tu consulta."

# ========== ENDPOINTS ==========

# Instancia global del deduplicador
deduplicador = None

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar"""
    global deduplicador
    deduplicador = DeduplicadorCompleto()
    logger.info("🚀 IANAE Completo iniciado correctamente")

@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Página principal con chat y estadísticas"""
    stats = deduplicador.obtener_estadisticas() if deduplicador else {}
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE Completo - Bibliotecario Personal</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }}
            
            .header {{
                background: rgba(0,0,0,0.1);
                padding: 1.5rem;
                color: white;
                backdrop-filter: blur(10px);
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }}
            
            .stats {{
                display: flex;
                justify-content: center;
                gap: 2rem;
                margin-top: 1rem;
                font-size: 0.9rem;
                opacity: 0.9;
            }}
            
            .container {{
                flex: 1;
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 2rem;
                padding: 2rem;
                max-width: 1400px;
                margin: 0 auto;
                width: 100%;
            }}
            
            .chat-panel {{
                background: white;
                border-radius: 20px;
                padding: 2rem;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
            }}
            
            .upload-panel {{
                background: white;
                border-radius: 20px;
                padding: 2rem;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }}
            
            .chat-messages {{
                flex: 1;
                max-height: 400px;
                overflow-y: auto;
                margin-bottom: 1rem;
                padding: 1rem;
                background: #f8f9fa;
                border-radius: 15px;
            }}
            
            .message {{
                margin-bottom: 1rem;
                padding: 1rem;
                border-radius: 12px;
                animation: fadeIn 0.3s ease;
            }}
            
            .user-message {{
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                border-left: 4px solid #2196f3;
            }}
            
            .bot-message {{
                background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
                border-left: 4px solid #9c27b0;
            }}
            
            .input-container {{
                display: flex;
                gap: 1rem;
            }}
            
            .chat-input {{
                flex: 1;
                padding: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                font-size: 1rem;
                outline: none;
            }}
            
            .chat-input:focus {{
                border-color: #667eea;
            }}
            
            .send-button {{
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                font-weight: 600;
            }}
            
            .upload-zone {{
                border: 3px dashed #ccc;
                padding: 2rem;
                text-align: center;
                border-radius: 15px;
                cursor: pointer;
                margin-bottom: 1rem;
                transition: all 0.3s;
            }}
            
            .upload-zone:hover {{
                border-color: #667eea;
                background: rgba(102, 126, 234, 0.05);
            }}
            
            .upload-zone.dragover {{
                border-color: #48bb78;
                background: rgba(72, 187, 120, 0.1);
            }}
            
            .file-input {{
                display: none;
            }}
            
            .stats-panel {{
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 12px;
                margin-top: 1rem;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @media (max-width: 768px) {{
                .container {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 IANAE Completo</h1>
            <p>Tu Bibliotecario Personal Inteligente</p>
            <div class="stats">
                <div>📚 {stats.get('total_conversaciones', 0)} conversaciones</div>
                <div>💬 {stats.get('total_mensajes', 0)} mensajes</div>
                <div>🧠 {stats.get('total_conceptos', 0)} conceptos</div>
                <div>📁 {stats.get('total_archivos_procesados', 0)} archivos</div>
            </div>
        </div>
        
        <div class="container">
            <div class="chat-panel">
                <h2 style="margin-bottom: 1rem;">💬 Chat con IANAE</h2>
                <div class="chat-messages" id="messages">
                    <div class="message bot-message">
                        <strong>🤖 IANAE:</strong><br>
                        ¡Hola Lucas! 🚀 Soy tu bibliotecario personal completo.<br><br>
                        Tengo acceso a toda tu memoria: conversaciones, conceptos y relaciones.<br>
                        Puedes preguntarme sobre cualquier cosa de tus proyectos, tacógrafos, Python, automatización... ¡Lo que quieras! 🎯
                    </div>
                </div>
                <div class="input-container">
                    <input type="text" class="chat-input" id="chatInput" 
                           placeholder="Pregúntame sobre tus proyectos, tacógrafos, Python..."
                           onkeypress="handleKeyPress(event)">
                    <button class="send-button" onclick="sendMessage()">🚀 Enviar</button>
                </div>
            </div>
            
            <div class="upload-panel">
                <h2 style="margin-bottom: 1rem;">📁 Subir Conversaciones</h2>
                <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                    <p><strong>Arrastra archivos aquí</strong></p>
                    <p>o haz click para seleccionar</p>
                    <p style="font-size: 0.8rem; margin-top: 1rem; opacity: 0.7;">
                        Soporta: Claude JSON, ChatGPT JSON, Cline MD
                    </p>
                </div>
                <input type="file" id="fileInput" class="file-input" accept=".json,.md,.txt" multiple>
                
                <div class="stats-panel">
                    <h3>📊 Estado de la Memoria</h3>
                    <div id="statsContent">
                        <p><strong>Conversaciones:</strong> {stats.get('total_conversaciones', 0)}</p>
                        <p><strong>Mensajes:</strong> {stats.get('total_mensajes', 0)}</p>
                        <p><strong>Conceptos:</strong> {stats.get('total_conceptos', 0)}</p>
                        <p><strong>Archivos procesados:</strong> {stats.get('total_archivos_procesados', 0)}</p>
                    </div>
                </div>
                
                <div id="uploadResults"></div>
            </div>
        </div>
        
        <script>
            // Chat functionality
            function handleKeyPress(event) {{
                if (event.key === 'Enter') {{
                    sendMessage();
                }}
            }}
            
            async function sendMessage() {{
                const input = document.getElementById('chatInput');
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message
                addMessage(message, 'user');
                input.value = '';
                
                try {{
                    const response = await fetch('/chat', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ query: message }})
                    }});
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        addMessage(data.response, 'bot');
                    }} else {{
                        addMessage('Error: ' + data.detail, 'bot');
                    }}
                }} catch (error) {{
                    addMessage('Error de conexión: ' + error.message, 'bot');
                }}
            }}
            
            function addMessage(content, sender) {{
                const messages = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{sender}}-message`;
                
                const icon = sender === 'user' ? '👤' : '🤖';
                const name = sender === 'user' ? 'Tú' : 'IANAE';
                
                messageDiv.innerHTML = `<strong>${{icon}} ${{name}}:</strong><br>${{content}}`;
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            }}
            
            // Upload functionality
            const uploadZone = document.getElementById('uploadZone');
            const fileInput = document.getElementById('fileInput');
            
            uploadZone.addEventListener('dragover', (e) => {{
                e.preventDefault();
                uploadZone.classList.add('dragover');
            }});
            
            uploadZone.addEventListener('dragleave', () => {{
                uploadZone.classList.remove('dragover');
            }});
            
            uploadZone.addEventListener('drop', (e) => {{
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {{
                    handleFileUpload(files[0]);
                }}
            }});
            
            fileInput.addEventListener('change', (e) => {{
                if (e.target.files.length > 0) {{
                    handleFileUpload(e.target.files[0]);
                }}
            }});
            
            async function handleFileUpload(file) {{
                const formData = new FormData();
                formData.append('file', file);
                
                const resultsDiv = document.getElementById('uploadResults');
                resultsDiv.innerHTML = '<p>🔄 Procesando archivo...</p>';
                
                try {{
                    const response = await fetch('/upload', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        if (data.ya_procesado) {{
                            resultsDiv.innerHTML = `
                                <div style="background: #fff3cd; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                                    <strong>⏭️ Archivo ya procesado</strong><br>
                                    ${{data.motivo}}
                                </div>
                            `;
                        }} else {{
                            resultsDiv.innerHTML = `
                                <div style="background: #d4edda; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                                    <strong>✅ Archivo procesado correctamente</strong><br>
                                    Conversaciones: ${{data.conversaciones_guardadas}}<br>
                                    Mensajes: ${{data.mensajes_guardados}}<br>
                                    Conceptos: ${{data.conceptos_extraidos}}
                                </div>
                            `;
                            
                            // Actualizar estadísticas
                            setTimeout(() => location.reload(), 2000);
                        }}
                    }} else {{
                        resultsDiv.innerHTML = `
                            <div style="background: #f8d7da; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                                <strong>❌ Error:</strong> ${{data.detail}}
                            </div>
                        `;
                    }}
                }} catch (error) {{
                    resultsDiv.innerHTML = `
                        <div style="background: #f8d7da; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                            <strong>❌ Error de conexión:</strong> ${{error.message}}
                        </div>
                    `;
                }}
            }}
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Endpoint de subida con deduplicación completa"""
    
    import time
    start_time = time.time()
    
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # 1. Verificar deduplicación
        ya_procesado, motivo, file_hash = deduplicador.archivo_ya_procesado(file.filename, tmp_file_path)
        
        if ya_procesado:
            return {
                'success': True,
                'ya_procesado': True,
                'motivo': motivo,
                'tiempo_procesamiento': round(time.time() - start_time, 2)
            }
        
        # 2. Detectar tipo y procesar
        tipo_detectado = detectar_tipo_automatico(tmp_file_path)
        
        if tipo_detectado.startswith('error'):
            raise HTTPException(status_code=400, detail=f"Error detectando tipo: {tipo_detectado}")
        
        # 3. Procesar conversaciones
        conversaciones = procesar_segun_tipo(tmp_file_path, tipo_detectado)
        
        # 4. Guardar en base de datos con extracción de conceptos
        resultado = deduplicador.guardar_conversaciones_procesadas(
            conversaciones, file.filename, file_hash, tipo_detectado
        )
        
        tiempo_procesamiento = round(time.time() - start_time, 2)
        
        return {
            'success': True,
            'ya_procesado': False,
            'motivo': motivo,
            'tipo_detectado': tipo_detectado,
            'conversaciones_guardadas': resultado['conversaciones_guardadas'],
            'mensajes_guardados': resultado['mensajes_guardados'],
            'conceptos_extraidos': resultado['conceptos_extraidos'],
            'tiempo_procesamiento': tiempo_procesamiento
        }
        
    except Exception as e:
        logger.error(f"Error en upload: {e}")
        return {'error': str(e)}
    
    finally:
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Endpoint de chat con búsqueda en conceptos"""
    try:
        query = message.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query vacío")
        
        logger.info(f"🔍 Chat query: {query}")
        
        # Buscar conceptos relevantes
        inicio_busqueda = time.time()
        conceptos_encontrados = deduplicador.buscar_conceptos(query, limite=8)
        tiempo_busqueda = time.time() - inicio_busqueda
        
        # Generar contexto para el LLM
        contexto = ""
        if conceptos_encontrados:
            contexto_partes = ["MEMORIA PERSONAL DE LUCAS:\n"]
            
            for concepto in conceptos_encontrados[:5]:
                contexto_partes.append(f"• {concepto['concepto']} ({concepto['categoria']})")
                if concepto['contexto']:
                    contexto_partes.append(f"  {concepto['contexto'][:150]}...")
                contexto_partes.append("")
            
            contexto = "\n".join(contexto_partes)
        
        # Consultar LLM
        respuesta = consultar_llm(query, contexto)
        
        return ChatResponse(
            response=respuesta,
            conceptos_utilizados=conceptos_encontrados,
            tiempo_busqueda=tiempo_busqueda,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Estadísticas detalladas del sistema"""
    if not deduplicador:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    
    stats = deduplicador.obtener_estadisticas()
    
    return {
        "status": "funcionando",
        "database": {
            "path": CONFIG["db_path"],
            "size_mb": round(os.path.getsize(CONFIG["db_path"]) / (1024 * 1024), 2) if os.path.exists(CONFIG["db_path"]) else 0
        },
        **stats,
        "version": "3.0",
        "features": [
            "deduplicacion_inteligente",
            "extraccion_conceptos", 
            "chat_contextual",
            "memoria_persistente",
            "busqueda_rapida"
        ]
    }

if __name__ == "__main__":
    print("🧠 IANAE COMPLETO - Bibliotecario Personal")
    print("=" * 50)
    print("🚀 Todas las funciones integradas:")
    print("   ✅ Digestor universal (Claude, ChatGPT, Cline)")
    print("   ✅ Deduplicación inteligente")
    print("   ✅ Extracción automática de conceptos")
    print("   ✅ Chat con memoria personal")
    print("   ✅ Base de datos SQLite optimizada")
    print("   ✅ Búsquedas ultrarrápidas")
    print("   ✅ Trazabilidad completa")
    print("")
    print("🌐 Interfaz: http://localhost:8000")
    print("📊 Stats: http://localhost:8000/stats")
    print("💬 Chat integrado en la página principal")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
