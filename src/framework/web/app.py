# FastAPI app 
#!/usr/bin/env python3
"""
IANAE Web Application
Aplicación web principal con FastAPI para IANAE
¡INTERFAZ WEB COMPLETA! 🚀🌐
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Imports de IANAE
from core.config import get_config, get_web_config
from core.database import get_database_manager, ConversationData, MessageData
from processors.auto_detector import detect_file_format, FormatType
from processors.ai_platforms.claude import ClaudeProcessor

logger = logging.getLogger(__name__)


# === MODELOS PYDANTIC ===

class ChatRequest(BaseModel):
    """Modelo para requests de chat"""
    query: str
    conversation_id: Optional[str] = None
    context_limit: Optional[int] = 5


class ChatResponse(BaseModel):
    """Modelo para responses de chat"""
    response: str
    conversation_id: str
    context_used: List[Dict[str, Any]]
    processing_time: float
    timestamp: str


class UploadResponse(BaseModel):
    """Modelo para responses de upload"""
    success: bool
    file_id: str
    format_detected: str
    platform: str
    total_conversations: int
    total_messages: int
    processing_time: float
    errors: List[str] = []


class SearchRequest(BaseModel):
    """Modelo para requests de búsqueda"""
    query: str
    platform: Optional[str] = None
    limit: Optional[int] = 20


class SearchResponse(BaseModel):
    """Modelo para responses de búsqueda"""
    results: List[Dict[str, Any]]
    total_found: int
    processing_time: float


# === APLICACIÓN FASTAPI ===

def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI"""
    
    config = get_config()
    web_config = get_web_config()
    
    app = FastAPI(
        title="IANAE - Intelligent Memory System",
        description="Sistema inteligente de gestión de memoria conversacional",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # === MIDDLEWARE ===
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=web_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # === STATIC FILES & TEMPLATES ===
    
    # Verificar que existen los directorios
    static_dir = Path("web/static")
    templates_dir = Path("web/templates")
    
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    templates = Jinja2Templates(directory=str(templates_dir)) if templates_dir.exists() else None
    
    # === DEPENDENCIAS ===
    
    def get_db():
        """Dependency para obtener database manager"""
        return get_database_manager()
    
    def get_processors():
        """Dependency para obtener procesadores disponibles"""
        return {
            "claude": ClaudeProcessor(),
            # Aquí se añadirían más procesadores
        }
    
    # === ROUTES PRINCIPALES ===
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Página principal"""
        
        if templates:
            # Obtener estadísticas para mostrar en la página
            db = get_database_manager()
            stats = db.get_database_stats()
            
            return templates.TemplateResponse("index.html", {
                "request": request,
                "stats": stats,
                "title": "IANAE - Intelligent Memory System"
            })
        else:
            # Fallback HTML si no hay templates
            return HTMLResponse(content=get_fallback_html(), status_code=200)
    
    @app.post("/api/upload", response_model=UploadResponse)
    async def upload_file(
        file: UploadFile = File(...),
        db = Depends(get_db),
        processors = Depends(get_processors)
    ):
        """
        Endpoint para subir y procesar archivos de conversaciones
        """
        start_time = time.time()
        
        # Validar archivo
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
        
        # Verificar tamaño
        web_config = get_web_config()
        if file.size and file.size > web_config.max_upload_size:
            raise HTTPException(
                status_code=413, 
                detail=f"Archivo muy grande. Máximo: {web_config.max_upload_size / (1024*1024):.1f}MB"
            )
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Detectar formato
            logger.info(f"🔍 Procesando upload: {file.filename}")
            detection_result = detect_file_format(tmp_path, content.decode('utf-8', errors='ignore'))
            
            if detection_result.format_type == FormatType.UNKNOWN:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de archivo no soportado: {file.filename}"
                )
            
            # Seleccionar procesador apropiado
            processor = None
            if detection_result.format_type == FormatType.CLAUDE_JSON:
                processor = processors["claude"]
            
            if not processor:
                raise HTTPException(
                    status_code=501,
                    detail=f"Procesador no disponible para formato: {detection_result.format_type.value}"
                )
            
            # Procesar archivo
            logger.info(f"⚡ Procesando con {processor.__class__.__name__}")
            processing_result = processor.process(tmp_path)
            
            if not processing_result.success:
                raise HTTPException(
                    status_code=422,
                    detail=f"Error procesando archivo: {'; '.join(processing_result.errors)}"
                )
            
            # Guardar en base de datos
            conversations_saved = 0
            messages_saved = 0
            
            for conversation in processing_result.conversations:
                if db.insert_conversation(conversation):
                    conversations_saved += 1
            
            for message in processing_result.messages:
                if db.insert_message(message):
                    messages_saved += 1
            
            # Marcar archivo como procesado
            file_hash = db.calculate_content_hash(content.decode('utf-8', errors='ignore'))
            db.mark_file_processed(
                filename=file.filename,
                file_hash=file_hash,
                file_size=len(content),
                format_type=detection_result.format_type.value,
                conversations_count=conversations_saved,
                messages_count=messages_saved
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Upload completado: {conversations_saved} conv, {messages_saved} msg en {processing_time:.2f}s")
            
            return UploadResponse(
                success=True,
                file_id=file_hash[:16],
                format_detected=detection_result.format_type.value,
                platform=detection_result.platform,
                total_conversations=conversations_saved,
                total_messages=messages_saved,
                processing_time=processing_time,
                errors=processing_result.errors
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error procesando upload: {e}")
            raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
        
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        db = Depends(get_db)
    ):
        """
        Endpoint para chat con el sistema usando contexto de conversaciones
        """
        start_time = time.time()
        
        try:
            # Buscar contexto relevante
            search_results = db.search_messages_content(
                query=request.query,
                limit=request.context_limit or 5
            )
            
            # Construir contexto para LLM
            context_messages = []
            for result in search_results:
                context_messages.append({
                    "conversation_title": result["conversation_title"],
                    "platform": result["platform"],
                    "role": result["role"],
                    "content": result["content"][:500],  # Limitar longitud
                    "timestamp": result["timestamp"]
                })
            
            # Por ahora, respuesta simulada (aquí iría integración con LLM)
            response_text = f"""Basándome en tu memoria de conversaciones, encontré {len(context_messages)} resultados relevantes para tu consulta sobre: "{request.query}"

Contexto encontrado:
"""
            
            for i, ctx in enumerate(context_messages[:3], 1):
                response_text += f"{i}. De '{ctx['conversation_title']}' ({ctx['platform']}): {ctx['content'][:100]}...\n"
            
            response_text += f"\n¿Te gustaría que profundice en algún aspecto específico?"
            
            processing_time = time.time() - start_time
            
            return ChatResponse(
                response=response_text,
                conversation_id=request.conversation_id or f"chat_{int(time.time())}",
                context_used=context_messages,
                processing_time=processing_time,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except Exception as e:
            logger.error(f"❌ Error en chat: {e}")
            raise HTTPException(status_code=500, detail=f"Error procesando chat: {str(e)}")
    
    @app.post("/api/search", response_model=SearchResponse)
    async def search(
        request: SearchRequest,
        db = Depends(get_db)
    ):
        """
        Endpoint para búsqueda en conversaciones y mensajes
        """
        start_time = time.time()
        
        try:
            # Buscar conversaciones
            conversations = db.search_conversations(
                query=request.query,
                platform=request.platform,
                limit=request.limit or 20
            )
            
            # Buscar en contenido de mensajes
            messages = db.search_messages_content(
                query=request.query,
                limit=request.limit or 20
            )
            
            # Combinar resultados
            results = []
            
            # Agregar conversaciones
            for conv in conversations:
                results.append({
                    "type": "conversation",
                    "id": conv.id,
                    "title": conv.title,
                    "platform": conv.platform,
                    "created_at": conv.created_at,
                    "total_messages": conv.total_messages,
                    "relevance": "title_match"
                })
            
            # Agregar mensajes
            for msg in messages:
                results.append({
                    "type": "message",
                    "id": msg["message_id"],
                    "conversation_id": msg["conversation_id"],
                    "conversation_title": msg["conversation_title"],
                    "platform": msg["platform"],
                    "role": msg["role"],
                    "content": msg["content"][:300],  # Preview
                    "timestamp": msg["timestamp"],
                    "relevance": "content_match"
                })
            
            processing_time = time.time() - start_time
            
            return SearchResponse(
                results=results,
                total_found=len(results),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")
    
    @app.get("/api/stats")
    async def get_stats(db = Depends(get_db)):
        """
        Endpoint para obtener estadísticas del sistema
        """
        try:
            stats = db.get_database_stats()
            return JSONResponse(content=stats)
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": time.time()}
    
    # === ERROR HANDLERS ===
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "Endpoint no encontrado"}
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        logger.error(f"Error interno: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"}
        )
    
    return app


def get_fallback_html() -> str:
    """HTML de fallback si no hay templates"""
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE - Intelligent Memory System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', system-ui, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; display: flex; flex-direction: column;
                color: white;
            }
            .header { padding: 2rem; text-align: center; }
            .header h1 { font-size: 3rem; margin-bottom: 1rem; }
            .header p { font-size: 1.2rem; opacity: 0.9; }
            .main { flex: 1; padding: 2rem; max-width: 1200px; margin: 0 auto; }
            .card { 
                background: rgba(255,255,255,0.1); 
                border-radius: 15px; padding: 2rem; margin: 1rem 0;
                backdrop-filter: blur(10px);
            }
            .upload-zone {
                border: 3px dashed rgba(255,255,255,0.3);
                border-radius: 10px; padding: 3rem; text-align: center;
                cursor: pointer; transition: all 0.3s ease;
            }
            .upload-zone:hover { border-color: white; background: rgba(255,255,255,0.1); }
            .api-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
            .endpoint { background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; }
            .endpoint h3 { color: #4ECDC4; margin-bottom: 0.5rem; }
            .endpoint code { background: rgba(0,0,0,0.3); padding: 0.3rem; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 IANAE</h1>
            <p>Intelligent Memory System - Sistema Inteligente de Gestión de Memoria</p>
        </div>
        
        <div class="main">
            <div class="card">
                <h2>📁 Subir Archivos de Conversaciones</h2>
                <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
                    <input type="file" id="fileInput" style="display:none" accept=".json,.md,.txt" />
                    <h3>📤 Arrastra archivos aquí o haz clic</h3>
                    <p>Soporta: Claude JSON, ChatGPT JSON, Cline Markdown, y más</p>
                </div>
            </div>
            
            <div class="card">
                <h2>🚀 API Endpoints Disponibles</h2>
                <div class="api-info">
                    <div class="endpoint">
                        <h3>POST /api/upload</h3>
                        <p>Subir y procesar archivos de conversaciones</p>
                        <code>multipart/form-data</code>
                    </div>
                    <div class="endpoint">
                        <h3>POST /api/chat</h3>
                        <p>Chat con contexto de tu memoria</p>
                        <code>{"query": "tu pregunta"}</code>
                    </div>
                    <div class="endpoint">
                        <h3>POST /api/search</h3>
                        <p>Buscar en conversaciones y mensajes</p>
                        <code>{"query": "términos de búsqueda"}</code>
                    </div>
                    <div class="endpoint">
                        <h3>GET /api/stats</h3>
                        <p>Estadísticas del sistema</p>
                        <code>GET request</code>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>📚 Documentación API</h2>
                <p>Accede a la documentación completa:</p>
                <p>• <a href="/api/docs" style="color: #4ECDC4;">Swagger UI</a> - Interfaz interactiva</p>
                <p>• <a href="/api/redoc" style="color: #4ECDC4;">ReDoc</a> - Documentación detallada</p>
            </div>
        </div>
        
        <script>
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Mostrar progreso
            document.querySelector('.upload-zone').innerHTML = '<h3>🔄 Procesando...</h3>';
            
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelector('.upload-zone').innerHTML = `
                        <h3>✅ ¡Procesado Exitosamente!</h3>
                        <p>Formato: ${data.format_detected}</p>
                        <p>Conversaciones: ${data.total_conversations}</p>
                        <p>Mensajes: ${data.total_messages}</p>
                    `;
                } else {
                    document.querySelector('.upload-zone').innerHTML = `
                        <h3>❌ Error procesando archivo</h3>
                        <p>${data.errors ? data.errors.join(', ') : 'Error desconocido'}</p>
                    `;
                }
            })
            .catch(error => {
                document.querySelector('.upload-zone').innerHTML = `
                    <h3>❌ Error de conexión</h3>
                    <p>${error.message}</p>
                `;
            });
        });
        </script>
    </body>
    </html>
    """


# === INSTANCIA DE APLICACIÓN ===

app = create_app()


# === FUNCIÓN PRINCIPAL ===

def main():
    """Función principal para ejecutar la aplicación"""
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Obtener configuración
    web_config = get_web_config()
    
    logger.info("🚀 Iniciando IANAE Web Application")
    logger.info(f"🌐 Servidor: {web_config.host}:{web_config.port}")
    logger.info(f"🔧 Debug: {web_config.debug}")
    
    # Ejecutar servidor
    uvicorn.run(
        "web.app:app",
        host=web_config.host,
        port=web_config.port,
        debug=web_config.debug,
        reload=web_config.reload,
        workers=web_config.workers if not web_config.debug else 1
    )


if __name__ == "__main__":
    main()