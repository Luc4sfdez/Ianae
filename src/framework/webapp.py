# v01 - ARREGLADO: Detector de formato + logs sin emojis + ventana de logs
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import tempfile
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configurar logging SIN EMOJIS para Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ianae.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="IANAE 4.0 - Procesador Universal", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def detectar_formato_mejorado(data, filename):
    """Detector de formato MEJORADO - más preciso"""
    logger.info(f"DETECTANDO FORMATO para: {filename}")
    
    # 1. CLAUDE JSON - Verificación más estricta
    if isinstance(data, list) and len(data) > 0:
        primer_elemento = data[0]
        logger.info(f"Primer elemento keys: {list(primer_elemento.keys()) if isinstance(primer_elemento, dict) else 'No es dict'}")
        
        if isinstance(primer_elemento, dict):
            # Claude tiene: uuid, name, chat_messages
            claude_keys = {'uuid', 'name', 'chat_messages'}
            elemento_keys = set(primer_elemento.keys())
            
            if claude_keys.issubset(elemento_keys):
                logger.info("DETECTADO: Claude JSON (uuid + name + chat_messages)")
                return 'claude'
            
            # ChatGPT tiene: id, title, mapping
            chatgpt_keys = {'id', 'title', 'mapping'}
            if chatgpt_keys.issubset(elemento_keys):
                logger.info("DETECTADO: ChatGPT JSON (id + title + mapping)")
                return 'chatgpt'
    
    # 2. ChatGPT object único
    if isinstance(data, dict) and 'mapping' in data:
        logger.info("DETECTADO: ChatGPT JSON (objeto único con mapping)")
        return 'chatgpt'
    
    # 3. Si llegamos aquí, es otro formato
    logger.warning("FORMATO NO RECONOCIDO - usando parser genérico")
    return 'unknown'

def procesar_claude_json(data):
    """Procesa JSON de Claude CORRECTAMENTE"""
    logger.info(f"PROCESANDO CLAUDE JSON: {len(data)} elementos")
    
    conversaciones = []
    total_mensajes = 0
    
    for i, conv_data in enumerate(data):
        try:
            # Extraer metadatos de Claude
            conv_id = conv_data.get('uuid', f'claude_conv_{i}')
            titulo = conv_data.get('name', f'Conversación {i+1}')
            created_at = conv_data.get('created_at')
            
            # Procesar mensajes de Claude
            mensajes = []
            chat_messages = conv_data.get('chat_messages', [])
            
            logger.info(f"Conv {i}: {len(chat_messages)} chat_messages")
            
            for msg in chat_messages:
                if isinstance(msg, dict) and 'text' in msg:
                    texto = msg.get('text', '').strip()
                    if texto:
                        mensajes.append({
                            'id': msg.get('uuid', f'msg_{len(mensajes)}'),
                            'role': 'human' if msg.get('sender') == 'human' else 'assistant',
                            'content': texto,
                            'timestamp': msg.get('created_at')
                        })
            
            if mensajes:
                conversaciones.append({
                    'id': conv_id,
                    'titulo': titulo,
                    'plataforma': 'claude',
                    'timestamp': created_at,
                    'mensajes': mensajes
                })
                total_mensajes += len(mensajes)
                
                if i % 50 == 0:
                    logger.info(f"Procesadas {i+1}/{len(data)} conversaciones Claude...")
                
        except Exception as e:
            logger.error(f"Error procesando conversación Claude {i}: {e}")
            continue
    
    logger.info(f"CLAUDE COMPLETADO: {len(conversaciones)} conversaciones, {total_mensajes} mensajes")
    return conversaciones

def procesar_chatgpt_json(data):
    """Procesa JSON de ChatGPT"""
    logger.info("PROCESANDO CHATGPT JSON")
    
    conversaciones = []
    
    # Si es lista de conversaciones
    if isinstance(data, list):
        for i, conv_data in enumerate(data):
            conv = procesar_conversacion_chatgpt(conv_data, i)
            if conv:
                conversaciones.append(conv)
    
    # Si es una sola conversación
    elif isinstance(data, dict):
        conv = procesar_conversacion_chatgpt(data, 0)
        if conv:
            conversaciones.append(conv)
    
    total_mensajes = sum(len(c['mensajes']) for c in conversaciones)
    logger.info(f"CHATGPT COMPLETADO: {len(conversaciones)} conversaciones, {total_mensajes} mensajes")
    return conversaciones

def procesar_conversacion_chatgpt(conv_data, indice):
    """Procesa una conversación individual de ChatGPT"""
    try:
        conv_id = conv_data.get('id', f'chatgpt_conv_{indice}')
        titulo = conv_data.get('title', f'Conversación {indice + 1}')
        
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
            
            texto = " ".join(str(part) for part in parts if isinstance(part, str)).strip()
            
            if texto:
                mensajes.append({
                    'id': message_data.get('id', node_id),
                    'role': role,
                    'content': texto,
                    'timestamp': message_data.get('create_time')
                })
        
        mensajes_validos = [m for m in mensajes if m['content'].strip()]
        
        if mensajes_validos:
            return {
                'id': conv_id,
                'titulo': titulo,
                'plataforma': 'chatgpt',
                'timestamp': conv_data.get('create_time'),
                'mensajes': mensajes_validos
            }
        
    except Exception as e:
        logger.error(f"Error procesando conversación ChatGPT {indice}: {e}")
    
    return None

def procesar_cline_markdown(contenido):
    """Procesa archivos Markdown de Cline"""
    logger.info("PROCESANDO CLINE MARKDOWN")
    
    conversaciones = []
    
    if '# Cline Task' in contenido or '## Human:' in contenido:
        mensajes = []
        lineas = contenido.split('\n')
        
        mensaje_actual = {'role': None, 'content': []}
        
        for linea in lineas:
            if linea.startswith('## Human:'):
                if mensaje_actual['role']:
                    contenido_msg = '\n'.join(mensaje_actual['content']).strip()
                    if contenido_msg:
                        mensajes.append({
                            'role': mensaje_actual['role'],
                            'content': contenido_msg,
                            'timestamp': None
                        })
                mensaje_actual = {'role': 'user', 'content': []}
                
            elif linea.startswith('## Assistant:'):
                if mensaje_actual['role']:
                    contenido_msg = '\n'.join(mensaje_actual['content']).strip()
                    if contenido_msg:
                        mensajes.append({
                            'role': mensaje_actual['role'],
                            'content': contenido_msg,
                            'timestamp': None
                        })
                mensaje_actual = {'role': 'assistant', 'content': []}
                
            else:
                if mensaje_actual['role']:
                    mensaje_actual['content'].append(linea)
        
        # Guardar último mensaje
        if mensaje_actual['role'] and mensaje_actual['content']:
            contenido_msg = '\n'.join(mensaje_actual['content']).strip()
            if contenido_msg:
                mensajes.append({
                    'role': mensaje_actual['role'],
                    'content': contenido_msg,
                    'timestamp': None
                })
        
        if mensajes:
            conversaciones.append({
                'id': 'cline_task_1',
                'titulo': 'Cline Task',
                'plataforma': 'cline',
                'timestamp': None,
                'mensajes': mensajes
            })
    
    total_mensajes = sum(len(c['mensajes']) for c in conversaciones)
    logger.info(f"CLINE COMPLETADO: {len(conversaciones)} conversaciones, {total_mensajes} mensajes")
    return conversaciones

def procesar_archivo_universal(file_path, filename):
    """Procesador universal MEJORADO"""
    logger.info(f"INICIANDO PROCESAMIENTO: {file_path}")
    
    try:
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        logger.info(f"Archivo leído: {len(contenido)} caracteres")
        logger.info(f"Primeros 200 chars: {contenido[:200]}")
        
        # Intentar parsear como JSON
        try:
            data = json.loads(contenido)
            logger.info("DETECTADO COMO JSON")
            logger.info(f"JSON parseado correctamente: {type(data)}")
            
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Primer elemento de la lista: {list(data[0].keys()) if isinstance(data[0], dict) else 'No es dict'}")
            elif isinstance(data, dict):
                logger.info(f"Objeto JSON con keys: {list(data.keys())}")
            
            # Detectar formato específico
            formato = detectar_formato_mejorado(data, filename)
            
            if formato == 'claude':
                conversaciones = procesar_claude_json(data)
                return {
                    'format': 'claude',
                    'confidence': 0.95,
                    'conversations': conversaciones,
                    'total_conversations': len(conversaciones),
                    'total_messages': sum(len(c['mensajes']) for c in conversaciones)
                }
            
            elif formato == 'chatgpt':
                conversaciones = procesar_chatgpt_json(data)
                return {
                    'format': 'chatgpt',
                    'confidence': 0.95,
                    'conversations': conversaciones,
                    'total_conversations': len(conversaciones),
                    'total_messages': sum(len(c['mensajes']) for c in conversaciones)
                }
            
            else:
                logger.warning("JSON no reconocido como ChatGPT o Claude")
                return {
                    'format': 'unknown_json',
                    'confidence': 0.3,
                    'conversations': [],
                    'total_conversations': 0,
                    'total_messages': 0,
                    'error': 'Formato JSON no reconocido'
                }
                
        except json.JSONDecodeError:
            logger.info("PROCESANDO COMO TEXTO/MARKDOWN (CLINE)")
            # Procesar como texto/markdown
            conversaciones = procesar_cline_markdown(contenido)
            return {
                'format': 'cline',
                'confidence': 0.8,
                'conversations': conversaciones,
                'total_conversations': len(conversaciones),
                'total_messages': sum(len(c['mensajes']) for c in conversaciones)
            }
            
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        return {
            'format': 'error',
            'confidence': 0.0,
            'conversations': [],
            'total_conversations': 0,
            'total_messages': 0,
            'error': str(e)
        }

@app.get("/", response_class=HTMLResponse)
async def get_main_interface():
    """Interfaz principal con ventana de logs"""
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE 4.0 - Procesador Universal</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            
            .container {
                display: grid;
                grid-template-columns: 1fr 400px;
                grid-template-rows: auto 1fr;
                height: 100vh;
                gap: 20px;
                padding: 20px;
            }
            
            .header {
                grid-column: 1 / -1;
                background: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
            }
            
            .main-panel {
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
            }
            
            .logs-panel {
                background: #1a1a1a;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
                resize: both;
                overflow: hidden;
                min-width: 300px;
                min-height: 400px;
            }
            
            .logs-header {
                color: #00ff00;
                font-weight: bold;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #333;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .logs-content {
                flex: 1;
                background: #000;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 15px;
                border-radius: 8px;
                overflow-y: auto;
                white-space: pre-wrap;
                line-height: 1.4;
            }
            
            .upload-zone {
                border: 3px dashed #ddd;
                border-radius: 15px;
                padding: 60px 20px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                margin-bottom: 30px;
            }
            
            .upload-zone:hover { border-color: #667eea; background: rgba(102, 126, 234, 0.05); }
            .upload-zone.dragover { border-color: #48bb78; background: rgba(72, 187, 120, 0.1); }
            
            .upload-icon { font-size: 4rem; margin-bottom: 20px; opacity: 0.5; }
            
            .file-input { display: none; }
            
            .results {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }
            
            .stat-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .stat-value {
                font-size: 2rem;
                font-weight: bold;
                color: #667eea;
                display: block;
            }
            
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
            
            .clear-btn {
                background: #dc3545;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
            }
            
            .processing {
                opacity: 0.7;
                pointer-events: none;
            }
            
            .success { color: #28a745; }
            .error { color: #dc3545; }
            .warning { color: #ffc107; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>IANAE 4.0 - Procesador Universal de Conversaciones</h1>
                <p>Soporte para Claude, ChatGPT, Cline y más formatos</p>
            </div>
            
            <div class="main-panel">
                <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
                    <div class="upload-icon">📁</div>
                    <h3>Arrastra o selecciona tu archivo</h3>
                    <p>Soporta: JSON (Claude/ChatGPT), Markdown (Cline), TXT</p>
                    <input type="file" id="fileInput" class="file-input" accept=".json,.md,.txt" />
                </div>
                
                <div id="results" class="results" style="display: none;"></div>
            </div>
            
            <div class="logs-panel">
                <div class="logs-header">
                    <span>LOGS EN TIEMPO REAL</span>
                    <button class="clear-btn" onclick="clearLogs()">Limpiar</button>
                </div>
                <div class="logs-content" id="logsContent">
                    [IANAE 4.0] Sistema iniciado...\n
                    [INFO] Esperando archivos para procesar...\n
                </div>
            </div>
        </div>
        
        <script>
            const uploadZone = document.getElementById('uploadZone');
            const fileInput = document.getElementById('fileInput');
            const results = document.getElementById('results');
            const logsContent = document.getElementById('logsContent');
            
            function addLog(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const logLine = `[${timestamp}] ${message}\n`;
                logsContent.textContent += logLine;
                logsContent.scrollTop = logsContent.scrollHeight;
            }
            
            function clearLogs() {
                logsContent.textContent = '[IANAE 4.0] Logs limpiados...\n';
            }
            
            // Drag and drop
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });
            
            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0]);
                }
            });
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFile(e.target.files[0]);
                }
            });
            
            async function handleFile(file) {
                addLog(`ARCHIVO RECIBIDO: ${file.name} (${(file.size/1024/1024).toFixed(2)} MB)`);
                
                uploadZone.classList.add('processing');
                results.style.display = 'none';
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    addLog('Enviando archivo para procesamiento...');
                    
                    const response = await fetch('/api/process', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        displayResults(result);
                        addLog(`PROCESAMIENTO EXITOSO: ${result.total_conversations} conversaciones, ${result.total_messages} mensajes`);
                    } else {
                        addLog(`ERROR: ${result.detail || 'Error desconocido'}`, 'error');
                    }
                    
                } catch (error) {
                    addLog(`ERROR DE CONEXIÓN: ${error.message}`, 'error');
                }
                
                uploadZone.classList.remove('processing');
            }
            
            function displayResults(data) {
                results.style.display = 'block';
                
                let statusClass = 'success';
                if (data.total_conversations === 0) statusClass = 'warning';
                if (data.format === 'error') statusClass = 'error';
                
                results.innerHTML = `
                    <h3 class="${statusClass}">Procesamiento Completado</h3>
                    
                    <div class="stat-grid">
                        <div class="stat-card">
                            <span class="stat-value">${data.format}</span>
                            <div class="stat-label">Formato Detectado</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${data.total_conversations}</span>
                            <div class="stat-label">Conversaciones</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${data.total_messages}</span>
                            <div class="stat-label">Mensajes</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${(data.confidence * 100).toFixed(0)}%</span>
                            <div class="stat-label">Confianza</div>
                        </div>
                    </div>
                    
                    ${data.error ? `<div class="error" style="margin-top: 20px;"><strong>Error:</strong> ${data.error}</div>` : ''}
                `;
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/process")
async def process_file(file: UploadFile = File(...)):
    """Procesa archivo subido"""
    
    logger.info(f"NUEVO ARCHIVO RECIBIDO: {file.filename}")
    
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    logger.info(f"Archivo guardado temporalmente: {tmp_file_path}")
    logger.info(f"Tamaño del archivo: {len(content)} bytes")
    
    try:
        logger.info("Iniciando procesamiento...")
        
        # Procesar archivo
        resultado = procesar_archivo_universal(tmp_file_path, file.filename)
        
        logger.info(f"Procesamiento completado: {resultado}")
        logger.info(f"RESULTADO FINAL: {resultado['format']} - {resultado['total_conversations']} conversaciones - {resultado['total_messages']} mensajes")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(tmp_file_path)
            logger.info(f"Archivo temporal eliminado: {tmp_file_path}")
        except:
            pass

if __name__ == "__main__":
    print("INICIANDO IANAE 4.0 (SIN EMOJIS)...")
    print("Servidor: http://localhost:8000")
    print("Logs: ianae.log + interfaz web")
    uvicorn.run(app, host="0.0.0.0", port=8000)