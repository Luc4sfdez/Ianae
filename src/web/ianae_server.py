# ianae_server.py - Servidor Principal MVP
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import logging
from datetime import datetime
import asyncio
import uvicorn

# Imports locales
from config import config
from memory_connector import get_memory_connector
from llm_connector import get_llm_connector

# Configurar logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="IANAE MVP",
    description="Bibliotecario Personal de IA - Minimum Viable Product",
    version="1.0.0"
)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# Modelos Pydantic
class ChatMessage(BaseModel):
    message: str
    timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    context_info: Optional[str] = None
    provider: Optional[str] = None
    timestamp: str

# Variables globales
memory_connector = None
llm_connector = None

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar el servidor"""
    global memory_connector, llm_connector
    
    logger.info("🚀 Iniciando IANAE MVP...")
    
    try:
        # Inicializar conectores
        memory_connector = get_memory_connector()
        llm_connector = get_llm_connector()
        
        # Verificar memoria
        stats = memory_connector.get_memory_stats()
        logger.info(f"📚 Memoria cargada: {stats.get('concepts', 0)} conceptos")
        
        # Verificar LLMs
        llm_status = llm_connector.health_check()
        logger.info(f"🤖 LLM Status: {llm_status['recommended']}")
        
        logger.info(f"✅ IANAE MVP iniciado en http://{config.HOST}:{config.PORT}")
        
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar el servidor"""
    logger.info("🔌 Cerrando IANAE MVP...")
    if memory_connector:
        memory_connector.close()

# Rutas principales
@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    """Página principal del chat"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    try:
        # Verificar memoria
        memory_stats = memory_connector.get_memory_stats()
        
        # Verificar LLM
        llm_status = llm_connector.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "connected": memory_stats.get("status") == "connected",
                "concepts": memory_stats.get("concepts", 0)
            },
            "llm": llm_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory-stats")
async def get_memory_stats():
    """Obtener estadísticas de memoria"""
    try:
        stats = memory_connector.get_memory_stats()
        return stats
    except Exception as e:
        logger.error(f"Memory stats error: {e}")
        return {"error": str(e)}

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """Endpoint principal de chat con IANAE"""
    try:
        user_message = chat_message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mensaje vacío")
        
        logger.info(f"💬 Usuario: {user_message[:100]}...")
        
        # 1. Obtener contexto de memoria
        context = memory_connector.get_context_for_query(user_message)
        
        # 2. Actualizar activaciones de conceptos encontrados
        for concept in context.get('found_concepts', []):
            memory_connector.update_concept_activation(concept['name'])
        
        # 3. Generar respuesta con LLM
        llm_response = llm_connector.generate_ianae_response(user_message, context)
        
        if not llm_response["success"]:
            logger.warning(f"LLM Error: {llm_response.get('error', 'Unknown')}")
        
        # 4. Preparar respuesta
        response = ChatResponse(
            response=llm_response["response"],
            context_info=f"Contexto: {len(context.get('found_concepts', []))} conceptos encontrados | Provider: {llm_response.get('provider', 'Unknown')}",
            provider=llm_response.get("provider"),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"🧠 IANAE respondió ({llm_response.get('provider', 'Unknown')})")
        
        return response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        
        # Respuesta de error amigable
        error_response = {
            "response": f"🔧 Error interno: {str(e)}\n\nVerifica que:\n- La base de datos esté en database/ianae_memory.db\n- LM Studio esté ejecutándose (opcional)\n- Los logs para más detalles",
            "context_info": "Error del sistema",
            "provider": "Error Handler",
            "timestamp": datetime.now().isoformat()
        }
        
        return error_response

@app.get("/patterns")
async def get_lucas_patterns():
    """Obtener patrones específicos de Lucas"""
    try:
        patterns = memory_connector.get_lucas_patterns()
        return patterns
    except Exception as e:
        logger.error(f"Patterns error: {e}")
        return {"error": str(e)}

@app.post("/concept")
async def add_concept(concept_data: dict):
    """Añadir nuevo concepto a la memoria"""
    try:
        concepto = concept_data.get("concepto")
        categoria = concept_data.get("categoria", "nuevo")
        contexto = concept_data.get("contexto", "")
        
        if not concepto:
            raise HTTPException(status_code=400, detail="Concepto requerido")
        
        memory_connector.add_new_concept(concepto, categoria, contexto)
        
        return {
            "status": "success",
            "message": f"Concepto '{concepto}' añadido",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Add concept error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de debug (solo desarrollo)
if config.DEBUG:
    @app.get("/debug/memory/{query}")
    async def debug_memory_search(query: str):
        """Debug: buscar en memoria"""
        try:
            concepts = memory_connector.search_concepts(query, limit=10)
            return {
                "query": query,
                "results": [
                    {
                        "concepto": c.concepto,
                        "categoria": c.categoria,
                        "activaciones": c.activaciones,
                        "contexto": c.contexto[:200] + "..." if len(c.contexto) > 200 else c.contexto
                    }
                    for c in concepts
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/debug/llm-status")
    async def debug_llm_status():
        """Debug: estado de LLMs"""
        return llm_connector.health_check()

# Manejo de errores
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint no encontrado", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)}
    )

# Función principal
def main():
    """Función principal para ejecutar el servidor"""
    print("🧠 IANAE MVP - Bibliotecario Personal de IA")
    print("="*50)
    print(f"🌐 Servidor: http://{config.HOST}:{config.PORT}")
    print(f"📚 Base de datos: {config.DATABASE_PATH}")
    print(f"🤖 LM Studio: {config.LM_STUDIO_URL}")
    print(f"📝 Logs: {config.LOG_FILE}")
    print("="*50)
    print("🚀 Iniciando servidor...")
    print("   Ctrl+C para detener")
    print()
    
    try:
        uvicorn.run(
            "ianae_server:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        print("👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    main()