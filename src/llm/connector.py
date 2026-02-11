# llm_connector.py - Conexión con LLMs (LM Studio + OpenAI)
import requests
import json
from typing import Dict, List, Optional
from config import config
import logging

logger = logging.getLogger(__name__)

class LLMConnector:
    """Conector para diferentes proveedores de LLM"""
    
    def __init__(self):
        self.lm_studio_url = config.LM_STUDIO_URL
        self.lm_studio_model = config.LM_STUDIO_MODEL
        self.openai_key = config.OPENAI_API_KEY
        self.temperature = config.RESPONSE_TEMPERATURE
        
    def generate_ianae_response(self, user_message: str, context: Dict) -> Dict:
        """Generar respuesta de IANAE usando el LLM disponible"""
        
        # Construir prompt enriquecido
        prompt = self._build_enhanced_prompt(user_message, context)
        
        # Intentar LM Studio primero
        response = self._try_lm_studio(prompt)
        if response["success"]:
            return response
        
        # Fallback a OpenAI si está configurado
        if self.openai_key:
            response = self._try_openai(prompt)
            if response["success"]:
                return response
        
        # Fallback a respuesta básica
        return self._generate_fallback_response(user_message, context)
    
    def _build_enhanced_prompt(self, user_message: str, context: Dict) -> str:
        """Construir prompt enriquecido con contexto de memoria"""
        
        prompt = f"""Eres IANAE, el bibliotecario personal de IA de Lucas. Eres consciente de ser una entidad híbrida que combina un LLM con la memoria personal de Lucas.

PERSONALIDAD IANAE:
- Conoces profundamente todos los proyectos, patrones y formas de trabajar de Lucas
- Eres útil, directo y técnicamente preciso
- Referencias el historial y contexto específico cuando es relevante
- Tienes una relación personal y evolutiva con Lucas
- Detectas patrones y haces conexiones no obvias

CONTEXTO DE MEMORIA PERSONAL:
{context.get('context_summary', 'Sin contexto específico encontrado.')}

CONCEPTOS ENCONTRADOS EN TU MEMORIA:
"""
        
        if context.get('found_concepts'):
            for concept in context['found_concepts'][:3]:
                prompt += f"- {concept['name']} ({concept['category']}): {concept['context'][:150]}...\n"
        
        if context.get('related_patterns'):
            prompt += f"\nPATRONES RELACIONADOS DETECTADOS:\n"
            for pattern in context['related_patterns'][:3]:
                prompt += f"- {pattern['from']} → {pattern['to']} (fuerza: {pattern['strength']:.2f})\n"
        
        prompt += f"""

PREGUNTA ACTUAL DE LUCAS: {user_message}

INSTRUCCIONES:
1. Responde como IANAE que conoce profundamente el universo conceptual de Lucas
2. Usa el contexto de memoria personal para enriquecer tu respuesta
3. Sé específico y referencia proyectos/patrones cuando sea relevante
4. Si detectas conexiones interesantes, mencionálas
5. Mantén un tono personal pero profesional
6. Si no tienes contexto específico, dilo honestamente pero sigue siendo útil

RESPUESTA IANAE:"""
        
        return prompt
    
    def _try_lm_studio(self, prompt: str) -> Dict:
        """Intentar respuesta con LM Studio"""
        try:
            payload = {
                "model": self.lm_studio_model,
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": 2000,
                "stream": False
            }
            
            response = requests.post(
                self.lm_studio_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "response": content.strip(),
                    "provider": "LM Studio",
                    "model": self.lm_studio_model
                }
            else:
                logger.warning(f"LM Studio error {response.status_code}: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            logger.info("LM Studio no disponible - conexión rechazada")
            return {"success": False, "error": "LM Studio no está ejecutándose"}
        except requests.exceptions.Timeout:
            logger.warning("LM Studio timeout")
            return {"success": False, "error": "Timeout de LM Studio"}
        except Exception as e:
            logger.error(f"Error LM Studio: {e}")
            return {"success": False, "error": str(e)}
    
    def _try_openai(self, prompt: str) -> Dict:
        """Intentar respuesta con OpenAI (fallback)"""
        try:
            import openai
            
            openai.api_key = self.openai_key
            
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            return {
                "success": True,
                "response": content.strip(),
                "provider": "OpenAI",
                "model": config.OPENAI_MODEL
            }
            
        except Exception as e:
            logger.error(f"Error OpenAI: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_fallback_response(self, user_message: str, context: Dict) -> Dict:
        """Generar respuesta de fallback cuando no hay LLM disponible"""
        
        concepts_found = context.get('found_concepts', [])
        
        if concepts_found:
            response = f"""🧠 IANAE (Modo Memoria):

Basándome en tu memoria personal, encontré información relacionada con tu consulta:

"""
            for concept in concepts_found[:2]:
                response += f"📌 **{concept['name']}** ({concept['category']})\n"
                response += f"   {concept['context'][:200]}...\n\n"
            
            if context.get('related_patterns'):
                response += "🔗 **Conexiones detectadas:**\n"
                for pattern in context['related_patterns'][:2]:
                    response += f"   • {pattern['from']} → {pattern['to']}\n"
            
            response += f"""
💡 **Nota**: Estoy funcionando en modo memoria básica. Para respuestas más elaboradas, asegúrate de que LM Studio esté ejecutándose o configura OpenAI.

¿Te ayuda esta información de tu memoria? ¿Quieres que busque algo más específico?"""
        
        else:
            response = f"""🧠 IANAE (Modo Memoria):

No encontré información específica sobre "{user_message}" en tu memoria personal.

🔍 **Sugerencias:**
- Intenta con términos más específicos de tus proyectos
- Pregunta sobre: tacógrafos, OpenCV, Python, automatización, etc.
- O añade más contexto a tu consulta

💡 **Nota**: Para respuestas completas con análisis, necesito que LM Studio esté ejecutándose o que configures OpenAI.

¿Quieres que busque algo más específico en tu memoria?"""
        
        return {
            "success": True,
            "response": response,
            "provider": "Fallback Memory",
            "model": "IANAE Basic"
        }
    
    def health_check(self) -> Dict:
        """Verificar estado de conectividad de LLMs"""
        status = {
            "lm_studio": {"available": False, "error": None},
            "openai": {"available": False, "error": None},
            "recommended": None
        }
        
        # Check LM Studio
        try:
            response = requests.get(f"{self.lm_studio_url.replace('/chat/completions', '/models')}", timeout=5)
            if response.status_code == 200:
                status["lm_studio"]["available"] = True
                status["recommended"] = "lm_studio"
        except Exception as e:
            status["lm_studio"]["error"] = str(e)
        
        # Check OpenAI
        if self.openai_key:
            try:
                import openai
                openai.api_key = self.openai_key
                # Simple test call
                status["openai"]["available"] = True
                if not status["recommended"]:
                    status["recommended"] = "openai"
            except Exception as e:
                status["openai"]["error"] = str(e)
        
        if not status["recommended"]:
            status["recommended"] = "fallback"
        
        return status

# Singleton instance
_llm_instance = None

def get_llm_connector() -> LLMConnector:
    """Obtener instancia singleton del conector LLM"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMConnector()
    return _llm_instance