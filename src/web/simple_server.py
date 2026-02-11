# simple_server.py - Test rápido para verificar funcionamiento
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List
import uvicorn

app = FastAPI()

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

class ChatMessage(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "IANAE MVP funcionando"}

@app.get("/test")
async def test():
    return {"message": "Test OK - El servidor funciona"}

@app.get("/memory-stats")
async def get_memory_stats():
    """Stats REALES de la memoria de Lucas"""
    try:
        from real_memory_connector import get_real_memory
        memory = get_real_memory()
        stats = memory.get_memory_stats()
        
        # Formato específico para el frontend
        return {
            "concepts": stats.get("concepts", 0),
            "relations": stats.get("relations", 0),
            "insights": stats.get("insights", 0),
            "status": stats.get("status", "unknown"),
            "top_categories": stats.get("top_categories", {})
        }
    except Exception as e:
        return {
            "concepts": 0,
            "relations": 0,
            "insights": 0,
            "status": "error",
            "error": str(e)
        }

def extract_search_terms(user_message: str) -> List[str]:
    """Extraer términos de búsqueda inteligentes"""
    import re
    
    # Palabras técnicas y proyectos específicos de Lucas
    technical_terms = [
        'python', 'opencv', 'docker', 'excel', 'vba', 'qr', 'tacografos', 
        'automatizacion', 'deteccion', 'optimizacion', 'html', 'css', 'js',
        'api', 'json', 'sql', 'github', 'git', 'npm', 'pip', 'turnos'
    ]
    
    # Limpiar mensaje
    clean_message = re.sub(r'[^\w\s]', ' ', user_message.lower())
    words = clean_message.split()
    
    # Filtrar palabras útiles
    stop_words = {'que', 'como', 'donde', 'cuando', 'por', 'para', 'de', 'del', 'la', 'el', 'en', 'con', 'se', 'te', 'me', 'le', 'lo', 'un', 'una', 'es', 'son', 'esta', 'esto', 'sabes', 'ideas', 'funciona', 'necesita', 'hablame', 'archivos', 'algo'}
    
    search_terms = []
    
    # Priorizar términos técnicos
    for word in words:
        if word in technical_terms:
            search_terms.append(word)
    
    # Añadir otras palabras relevantes
    for word in words:
        if (len(word) > 3 and 
            word not in stop_words and 
            word not in search_terms and
            len(search_terms) < 3):
            search_terms.append(word)
    
    return search_terms[:3]  # Max 3 términos

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """Chat con IANAE - VERSIÓN ROBUSTA QUE FUNCIONA"""
    user_message = chat_message.message.strip()
    
    try:
        from real_memory_connector import get_real_memory
        memory = get_real_memory()
        
        # Extraer términos inteligentes
        search_terms = extract_search_terms(user_message)
        print(f"BÚSQUEDA: {user_message} → términos: {search_terms}")
        
        # Buscar por cada término
        all_concepts = []
        for term in search_terms:
            concepts = memory.search_concepts(term, limit=3)
            all_concepts.extend(concepts)
            print(f"Término '{term}' → {len(concepts)} conceptos")
        
        # Eliminar duplicados
        unique_concepts = []
        seen = set()
        for concept in all_concepts:
            if concept.name not in seen:
                seen.add(concept.name)
                unique_concepts.append(concept)
        
        if unique_concepts:
            # RESPUESTA CON CONCEPTOS ENCONTRADOS
            response_text = f"🧠 **IANAE encontró {len(unique_concepts)} conceptos:**\n\n"
            
            for i, concept in enumerate(unique_concepts[:3], 1):
                response_text += f"**{i}. {concept.name}**\n"
                response_text += f"   • Categoría: {concept.category}\n"
                response_text += f"   • Usado: {concept.usage_count} veces\n"
                response_text += f"   • Fuerza: {concept.strength:.2f}\n\n"
            
            # Buscar conexiones
            relations = memory.get_related_concepts(unique_concepts[0].name, limit=3)
            if relations:
                response_text += "🔗 **Conexiones detectadas:**\n"
                for rel_name, rel_strength, rel_context in relations:
                    response_text += f"   • {unique_concepts[0].name} → {rel_name} ({rel_strength:.2f})\n"
            
            context_info = f"Encontrados: {len(unique_concepts)} conceptos"
            
        else:
            # SIN CONCEPTOS - MOSTRAR TOP CONCEPTS
            top_concepts = memory.get_top_concepts(5)
            concept_names = [c['name'] for c in top_concepts]
            
            response_text = f"🧠 **IANAE:** No encontré '{user_message}' específicamente.\n\n"
            response_text += f"**Tus conceptos principales:** {', '.join(concept_names)}\n\n"
            response_text += f"**Sugerencia:** Intenta términos como: {', '.join(search_terms)}"
            
            context_info = "Sin conceptos específicos encontrados"
        
        return {
            "response": response_text,
            "context_info": context_info,
            "provider": "IANAE Robusta",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"🔧 **Error:** {str(e)}"
        print(f"ERROR CHAT: {e}")
        
        return {
            "response": error_msg,
            "context_info": "Error del sistema", 
            "provider": "Error Handler",
            "timestamp": datetime.now().isoformat()
        }

async def try_llm_response(user_message: str, context: Dict) -> Dict:
    """Intentar respuesta con LLM real"""
    import requests
    
    # Construir prompt inteligente
    prompt = build_lucas_prompt(user_message, context)
    
    try:
        # Intentar LM Studio
        response = requests.post("http://localhost:1234/v1/chat/completions", 
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=10
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return {
                "success": True,
                "response": content.strip(),
                "provider": "LM Studio"
            }
    except:
        pass
    
    # TODO: Intentar OpenAI si está configurado
    
    return {"success": False, "error": "No LLM available"}

def build_lucas_prompt(user_message: str, context: Dict) -> str:
    """Construir prompt específico para Lucas"""
    prompt = f"""Eres IANAE, el bibliotecario personal de Lucas. Conoces profundamente sus proyectos y forma de trabajar.

CONTEXTO DE SU MEMORIA:
{context.get('context_summary', 'Sin contexto específico.')}

CONCEPTOS ENCONTRADOS:"""
    
    for concept in context.get('found_concepts', [])[:3]:
        prompt += f"\n- {concept['name']}: usado {concept['usage_count']} veces, categoría {concept['category']}"
    
    if context.get('related_patterns'):
        prompt += f"\n\nCONEXIONES DETECTADAS:"
        for pattern in context['related_patterns'][:2]:
            prompt += f"\n- {pattern['from']} ↔ {pattern['to']} (fuerza: {pattern['strength']:.2f})"
    
    prompt += f"""

PREGUNTA DE LUCAS: {user_message}

Responde como IANAE que conoce su forma de trabajar. Sé específico, útil y referencia su contexto personal cuando sea relevante. Máximo 200 palabras."""
    
    return prompt

def generate_smart_fallback(user_message: str, context: Dict, memory) -> str:
    """Extraer términos de búsqueda inteligentes"""
    import re
    
    # Palabras técnicas y proyectos específicos de Lucas
    technical_terms = [
        'python', 'opencv', 'docker', 'excel', 'vba', 'qr', 'tacografos', 
        'automatizacion', 'deteccion', 'optimizacion', 'html', 'css', 'js',
        'api', 'json', 'sql', 'github', 'git', 'npm', 'pip'
    ]
    
    # Limpiar mensaje
    clean_message = re.sub(r'[^\w\s]', ' ', user_message.lower())
    words = clean_message.split()
    
    # Filtrar palabras útiles
    stop_words = {'que', 'como', 'donde', 'cuando', 'por', 'para', 'de', 'del', 'la', 'el', 'en', 'con', 'se', 'te', 'me', 'le', 'lo', 'un', 'una', 'es', 'son', 'esta', 'esto', 'sabes', 'ideas', 'funciona', 'necesita', 'hablame', 'archivos'}
    
    search_terms = []
    
    # Priorizar términos técnicos
    for word in words:
        if word in technical_terms:
            search_terms.append(word)
    
    # Añadir otras palabras relevantes
    for word in words:
        if (len(word) > 3 and 
            word not in stop_words and 
            word not in search_terms and
            len(search_terms) < 3):
            search_terms.append(word)
    
    return search_terms[:3]  # Max 3 términos
    """Respuesta inteligente sin LLM"""
    found_concepts = context.get('found_concepts', [])
    
    if found_concepts:
        # Respuesta con conceptos encontrados
        top_concept = found_concepts[0]
        
        response = f"🧠 **IANAE** (basándome en tu memoria):\n\n"
        response += f"Encontré información sobre **{top_concept['name']}** en tu memoria:\n\n"
        response += f"📊 **Datos**: Usado {top_concept['usage_count']} veces, categoría: {top_concept['category']}\n"
        
        if top_concept['strength'] > 0.5:
            response += f"⭐ **Relevancia alta** (fuerza: {top_concept['strength']:.2f})\n"
        
        # Añadir conceptos relacionados
        if len(found_concepts) > 1:
            other_concepts = [c['name'] for c in found_concepts[1:3]]
            response += f"\n🔗 **También relacionado con**: {', '.join(other_concepts)}\n"
        
        # Añadir conexiones
        patterns = context.get('related_patterns', [])
        if patterns:
            response += f"\n💡 **Conexiones detectadas**:\n"
            for pattern in patterns[:2]:
                response += f"• {pattern['from']} → {pattern['to']}\n"
        
        response += f"\n¿Quieres que profundice en algún aspecto específico?"
        
    else:
        # No encontró conceptos específicos
        top_concepts = memory.get_top_concepts(5)
        concept_names = [c['name'] for c in top_concepts[:3]]
        
        response = f"🧠 **IANAE**:\n\n"
        response += f"No encontré información específica sobre '{user_message}' en tu memoria.\n\n"
        response += f"🎯 **Tus conceptos principales**: {', '.join(concept_names)}\n\n"
        response += f"💡 **Sugerencia**: Intenta con términos más específicos como:\n"
        response += f"• Nombres de proyectos (ej: 'tacógrafos')\n"
        response += f"• Tecnologías (ej: 'Python', 'OpenCV')\n"
        response += f"• Procesos (ej: 'automatización')\n\n"
        response += f"¿Sobre qué tema específico te gustaría que busque?"
    
    return response

if __name__ == "__main__":
    print("🧠 IANAE Simple Test Server")
    print("🌐 http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)