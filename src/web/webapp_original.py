#!/usr/bin/env python3
"""
ianae_web.py - Interface Web para IANAE Bibliotecario Personal
Conecta ConceptosLucas + LLM en una interface web fluida
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
import os
from datetime import datetime
import requests
from conceptos_lucas import ConceptosLucas

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app FastAPI
app = FastAPI(
    title="IANAE - Bibliotecario Personal de IA",
    description="El primer bibliotecario personal que conoce tu universo conceptual",
    version="1.0.0"
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración global
CONFIG = {
    "llm_endpoint": "http://localhost:1234/v1/chat/completions",
    "llm_model": "local-model",
    "conceptos_file": "conceptos_lucas_poblado.json",
    "max_conceptos_busqueda": 5,
    "umbral_similitud": 0.3
}

# Sistema global
SISTEMA_LUCAS = None

# Modelos Pydantic
class ChatMessage(BaseModel):
    query: str
    conversacion_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conceptos_utilizados: list
    fuentes: list
    timestamp: str

# Inicialización del sistema
def inicializar_sistema():
    """Inicializa o carga el sistema de conceptos de Lucas"""
    global SISTEMA_LUCAS
    
    try:
        if os.path.exists(CONFIG["conceptos_file"]):
            SISTEMA_LUCAS = ConceptosLucas.cargar_extendido(CONFIG["conceptos_file"])
            logger.info(f"✅ Sistema cargado con {len(SISTEMA_LUCAS.conceptos)} conceptos")
        else:
            logger.warning("❌ No se encontró archivo de conceptos. Crear sistema vacío.")
            SISTEMA_LUCAS = ConceptosLucas(dim_vector=15)
    except Exception as e:
        logger.error(f"Error inicializando sistema: {e}")
        SISTEMA_LUCAS = ConceptosLucas(dim_vector=15)

# Funciones auxiliares
def consultar_llm(query, contexto=""):
    """
    Consulta al LLM local (LM Studio) con contexto de Lucas
    """
    try:
        payload = {
            "model": CONFIG["llm_model"],
            "messages": [
                {
                    "role": "system", 
                    "content": f"""Eres IANAE, el bibliotecario personal de Lucas. 

{contexto}

Responde de manera natural y conversacional, usando el contexto proporcionado de las conversaciones previas de Lucas. Si el contexto es relevante, úsalo para dar respuestas más personalizadas y específicas."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        response = requests.post(
            CONFIG["llm_endpoint"], 
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Error LLM: {response.status_code} - {response.text}")
            return "Lo siento, no pude procesar tu consulta en este momento."
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error conectando con LLM: {e}")
        return "No puedo conectar con el sistema de IA local. ¿Está ejecutándose LM Studio?"
    except Exception as e:
        logger.error(f"Error inesperado en LLM: {e}")
        return "Ocurrió un error inesperado al procesar tu consulta."

def buscar_contexto_relevante(query):
    """
    Busca contexto relevante en el universo conceptual de Lucas
    """
    if not SISTEMA_LUCAS:
        return [], ""
    
    try:
        # Buscar conceptos relevantes
        conceptos_encontrados = SISTEMA_LUCAS.buscar_conceptos_por_contexto(
            query, 
            umbral_similitud=CONFIG["umbral_similitud"]
        )
        
        # Limitar resultados
        conceptos_top = conceptos_encontrados[:CONFIG["max_conceptos_busqueda"]]
        
        # Generar contexto para LLM
        contexto_llm = SISTEMA_LUCAS.generar_contexto_para_llm(conceptos_top)
        
        return conceptos_top, contexto_llm
        
    except Exception as e:
        logger.error(f"Error buscando contexto: {e}")
        return [], ""

# Rutas de la API

@app.get("/", response_class=HTMLResponse)
async def index():
    """Página principal de IANAE"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE - Tu Bibliotecario Personal</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: rgba(0,0,0,0.1);
                padding: 1rem 2rem;
                color: white;
                backdrop-filter: blur(10px);
            }
            
            .header h1 {
                font-size: 2rem;
                margin-bottom: 0.5rem;
            }
            
            .header p {
                opacity: 0.9;
                font-size: 1.1rem;
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
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                flex: 1;
                min-height: 400px;
                overflow-y: auto;
                max-height: 500px;
            }
            
            .message {
                margin-bottom: 1.5rem;
                padding: 1rem;
                border-radius: 10px;
            }
            
            .user-message {
                background: #f0f8ff;
                border-left: 4px solid #667eea;
            }
            
            .bot-message {
                background: #f8f9fa;
                border-left: 4px solid #28a745;
            }
            
            .message-header {
                font-weight: bold;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .message-content {
                line-height: 1.6;
                white-space: pre-wrap;
            }
            
            .input-container {
                background: white;
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                display: flex;
                gap: 1rem;
                align-items: center;
            }
            
            .chat-input {
                flex: 1;
                padding: 1rem;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                font-size: 1rem;
                outline: none;
                transition: border-color 0.3s;
            }
            
            .chat-input:focus {
                border-color: #667eea;
            }
            
            .send-button {
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                cursor: pointer;
                transition: transform 0.2s;
            }
            
            .send-button:hover {
                transform: translateY(-2px);
            }
            
            .send-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .status {
                text-align: center;
                color: white;
                margin: 1rem 0;
                font-style: italic;
            }
            
            .conceptos-info {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 10px;
                padding: 1rem;
                color: white;
                margin-top: 1rem;
            }
            
            .loading {
                display: none;
                text-align: center;
                color: #667eea;
                font-style: italic;
            }
            
            .emoji {
                font-size: 1.2em;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><span class="emoji">🧠</span> IANAE - Bibliotecario Personal</h1>
            <p>El primer asistente de IA que conoce tu universo conceptual completo</p>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="messages">
                <div class="message bot-message">
                    <div class="message-header">
                        <span class="emoji">🤖</span> IANAE
                    </div>
                    <div class="message-content">¡Hola Lucas! Soy IANAE, tu bibliotecario personal de IA. 

He analizado todas tus 308 conversaciones anteriores y conozco tus proyectos, preferencias y patrones de trabajo. 

Puedes preguntarme sobre:
• Tus proyectos anteriores (tacógrafos, automatización, IA)
• Problemas que ya has resuelto
• Código que has desarrollado
• Patrones y conexiones entre tus ideas

¿En qué puedo ayudarte hoy?</div>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <span class="emoji">🧠</span> Buscando en tu universo conceptual...
            </div>
            
            <div class="input-container">
                <input 
                    type="text" 
                    class="chat-input" 
                    id="messageInput" 
                    placeholder="Pregúntame sobre cualquier cosa de tus proyectos o conversaciones anteriores..."
                    onkeypress="handleKeyPress(event)"
                >
                <button class="send-button" onclick="sendMessage()" id="sendButton">
                    <span class="emoji">🚀</span> Enviar
                </button>
            </div>
            
            <div class="conceptos-info" id="conceptosInfo" style="display: none;">
                <strong><span class="emoji">📊</span> Conceptos utilizados:</strong>
                <div id="conceptosList"></div>
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
                
                // Limpiar input y deshabilitar botón
                input.value = '';
                document.getElementById('sendButton').disabled = true;
                document.getElementById('loading').style.display = 'block';
                
                // Añadir mensaje del usuario
                addMessage(message, 'user');
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            query: message,
                            conversacion_id: conversationId
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        // Añadir respuesta del bot
                        addMessage(data.response, 'bot');
                        
                        // Mostrar conceptos utilizados
                        if (data.conceptos_utilizados && data.conceptos_utilizados.length > 0) {
                            showConceptos(data.conceptos_utilizados);
                        }
                    } else {
                        addMessage('Lo siento, ocurrió un error: ' + data.detail, 'bot');
                    }
                } catch (error) {
                    addMessage('Error de conexión. ¿Está ejecutándose el servidor?', 'bot');
                }
                
                // Rehabilitar controles
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
                        ${sender === 'user' ? 'Tú' : 'IANAE'}
                    </div>
                    <div class="message-content">${content}</div>
                `;
                
                messagesContainer.appendChild(messageDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function showConceptos(conceptos) {
                const conceptosInfo = document.getElementById('conceptosInfo');
                const conceptosList = document.getElementById('conceptosList');
                
                conceptosList.innerHTML = conceptos.map(c => 
                    `<div>• <strong>${c.concepto}</strong> (${c.categoria}) - ${c.puntuacion.toFixed(2)}</div>`
                ).join('');
                
                conceptosInfo.style.display = 'block';
                
                // Ocultar después de 5 segundos
                setTimeout(() => {
                    conceptosInfo.style.display = 'none';
                }, 5000);
            }
            
            // Enfocar input al cargar
            document.getElementById('messageInput').focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Endpoint principal de chat con IANAE
    """
    try:
        if not SISTEMA_LUCAS:
            raise HTTPException(status_code=503, detail="Sistema no inicializado")
        
        query = message.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query vacío")
        
        logger.info(f"🔍 Query recibido: {query}")
        
        # Buscar contexto relevante
        conceptos_relevantes, contexto_llm = buscar_contexto_relevante(query)
        
        logger.info(f"📊 Encontrados {len(conceptos_relevantes)} conceptos relevantes")
        
        # Consultar LLM con contexto
        respuesta_llm = consultar_llm(query, contexto_llm)
        
        # Preparar respuesta
        fuentes = []
        for concepto in conceptos_relevantes:
            if concepto['fuente'] and concepto['fuente'] not in fuentes:
                fuentes.append(concepto['fuente'])
        
        return ChatResponse(
            response=respuesta_llm,
            conceptos_utilizados=conceptos_relevantes,
            fuentes=fuentes,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    """Estado del sistema IANAE"""
    if not SISTEMA_LUCAS:
        return {"status": "error", "message": "Sistema no inicializado"}
    
    return {
        "status": "ok",
        "sistema_inicializado": True,
        "conceptos_cargados": len(SISTEMA_LUCAS.conceptos),
        "categorias": list(SISTEMA_LUCAS.categorias.keys()),
        "metadata": SISTEMA_LUCAS.metadata_lucas,
        "configuracion": CONFIG
    }

@app.get("/conceptos")
async def listar_conceptos(categoria: str = None, limite: int = 50):
    """Lista conceptos del sistema"""
    if not SISTEMA_LUCAS:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    
    conceptos = []
    for nombre, datos in SISTEMA_LUCAS.conceptos.items():
        contexto = SISTEMA_LUCAS.contextos.get(nombre, {})
        
        if categoria and contexto.get('categoria') != categoria:
            continue
            
        conceptos.append({
            "nombre": nombre,
            "categoria": contexto.get('categoria', 'sin_categoria'),
            "activaciones": datos['activaciones'],
            "fuente": SISTEMA_LUCAS.fuentes.get(nombre, ''),
            "palabras_clave": contexto.get('palabras_clave', [])
        })
    
    # Ordenar por activaciones
    conceptos.sort(key=lambda x: x['activaciones'], reverse=True)
    
    return {
        "total": len(conceptos),
        "conceptos": conceptos[:limite]
    }

@app.post("/rebuild")
async def rebuild_system():
    """Reconstruye el sistema desde los resúmenes v6"""
    try:
        resumenes_dir = "resumenes_tematicos_v6"
        
        if not os.path.exists(resumenes_dir):
            raise HTTPException(status_code=404, detail=f"Directorio {resumenes_dir} no encontrado")
        
        # Recrear sistema
        global SISTEMA_LUCAS
        SISTEMA_LUCAS = ConceptosLucas(dim_vector=15)
        conceptos_importados = SISTEMA_LUCAS.importar_desde_resumenes_v6(resumenes_dir)
        
        if conceptos_importados > 0:
            SISTEMA_LUCAS.guardar_extendido(CONFIG["conceptos_file"])
            return {
                "status": "success",
                "message": f"Sistema reconstruido con {conceptos_importados} conceptos",
                "conceptos_importados": conceptos_importados
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudieron importar conceptos")
            
    except Exception as e:
        logger.error(f"Error reconstruyendo sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Inicialización al arrancar
@app.on_event("startup")
async def startup_event():
    """Inicializa el sistema al arrancar la aplicación"""
    logger.info("🚀 Iniciando IANAE...")
    inicializar_sistema()
    
    if SISTEMA_LUCAS:
        logger.info(f"✅ IANAE listo con {len(SISTEMA_LUCAS.conceptos)} conceptos")
    else:
        logger.warning("⚠️ IANAE iniciado pero sin conceptos cargados")

if __name__ == "__main__":
    import uvicorn
    
    print("🧠 Iniciando IANAE - Bibliotecario Personal de IA")
    print("=" * 50)
    print("📋 Checklist de inicialización:")
    print("1. ¿Está LM Studio ejecutándose en puerto 1234? ✓")
    print("2. ¿Existe el archivo conceptos_lucas_poblado.json? ✓")
    print("3. ¿Tienes los resúmenes v6 generados? ✓")
    print()
    print("🌐 Servidor iniciando en http://localhost:8000")
    print("📚 Tu bibliotecario personal estará listo en unos segundos...")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
