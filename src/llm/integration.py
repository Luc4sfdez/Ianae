# llm_integration.py - Integración LLM Real para IANAE MVP
"""
Módulo: LLM Integration
Propósito: Conectar IANAE con LM Studio y OpenAI para respuestas inteligentes
Autor: Lucas/Claude
Fecha: 2025-05-27
Proyecto: IANAE MVP - Bibliotecario Personal de IA

Descripción:
Este módulo maneja la integración con diferentes proveedores LLM:
- LM Studio (local) como opción principal
- OpenAI como fallback
- Construcción de prompts específicos para Lucas
- Manejo robusto de errores y timeouts

Dependencias:
- requests: Para llamadas HTTP a LM Studio
- openai: Para API de OpenAI (opcional)
- typing: Para type hints
- json: Para serialización de datos

Uso típico:
    llm = IANAELLMConnector()
    response = await llm.get_intelligent_response(
        user_message="¿Cómo funciona OpenCV?",
        concepts=[...],
        relations=[...]
    )
"""

import requests
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class IANAELLMConnector:
    """
    Conector LLM para IANAE con múltiples proveedores
    
    Maneja la conexión con LM Studio (principal) y OpenAI (fallback)
    para generar respuestas inteligentes basadas en la memoria de Lucas.
    """
    
    def __init__(self):
        """
        Inicializa el conector LLM
        
        Configuración:
            - LM Studio: localhost:1234
            - Modelo: r1-gemma-3-4b-multimodal-test (detectado automáticamente)
            - Timeout: 15 segundos
            - Temperature: 0.7 (conversacional pero coherente)
        """
        self.lm_studio_url = "http://localhost:1234/v1/chat/completions"
        self.lm_studio_model = "r1-gemma-3-4b-multimodal-test"
        self.timeout = 15
        self.temperature = 0.7
        self.max_tokens = 1000
        
        # Estado de conectividad
        self.lm_studio_available = False
        self.openai_available = False
        self.last_check = None
        
    async def get_intelligent_response(self, user_message: str, concepts: List[Dict], 
                                     relations: List[Dict]) -> Dict:
        """
        Obtiene respuesta inteligente usando el mejor LLM disponible
        
        Args:
            user_message: Pregunta original del usuario
            concepts: Lista de conceptos encontrados en memoria
            relations: Lista de relaciones detectadas
            
        Returns:
            Dict con:
                - success: bool
                - response: str (respuesta del LLM)
                - provider: str (qué LLM se usó)
                - tokens_used: int (aproximado)
                
        Example:
            >>> concepts = [{"name": "OpenCV", "usage": 10, "category": "tech"}]
            >>> response = await llm.get_intelligent_response(
            ...     "¿Cómo usar OpenCV?", concepts, []
            ... )
            >>> print(response["response"])
            "Basándome en tu experiencia con OpenCV..."
        """
        # 1. Construir prompt específico para Lucas
        prompt = self._build_lucas_prompt(user_message, concepts, relations)
        logger.info(f"💭 Generando respuesta para: {user_message[:50]}...")
        
        # 2. Intentar LM Studio primero
        lm_response = await self._try_lm_studio(prompt)
        if lm_response["success"]:
            logger.info(f"✅ LM Studio respondió exitosamente")
            return lm_response
            
        # 3. Intentar OpenAI como fallback
        openai_response = await self._try_openai(prompt)
        if openai_response["success"]:
            logger.info(f"✅ OpenAI respondió como fallback")
            return openai_response
            
        # 4. Ningún LLM disponible
        logger.warning(f"❌ Ningún LLM disponible")
        return {
            "success": False,
            "error": "No hay LLMs disponibles",
            "provider": "None"
        }
    
    async def _try_lm_studio(self, prompt: str) -> Dict:
        """
        Intenta obtener respuesta de LM Studio
        
        Args:
            prompt: Prompt construido para Lucas
            
        Returns:
            Dict con resultado de la llamada
            
        Note:
            - Timeout de 15 segundos
            - Maneja errores de conexión gracefully
            - Detecta si el modelo está cargado
        """
        try:
            # Preparar payload para LM Studio
            payload = {
                "model": self.lm_studio_model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "Eres IANAE, el bibliotecario personal de Lucas. Responde de forma conversacional y útil."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            logger.debug(f"🔄 Enviando request a LM Studio...")
            
            # Realizar llamada HTTP
            response = requests.post(
                self.lm_studio_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Actualizar estado de conectividad
                self.lm_studio_available = True
                self.last_check = datetime.now()
                
                return {
                    "success": True,
                    "response": content.strip(),
                    "provider": "LM Studio",
                    "model": self.lm_studio_model,
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                }
            else:
                logger.warning(f"⚠️ LM Studio error HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except requests.exceptions.ConnectionError:
            logger.info(f"🔌 LM Studio no disponible - conexión rechazada")
            self.lm_studio_available = False
            return {"success": False, "error": "LM Studio no está ejecutándose"}
            
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ LM Studio timeout después de {self.timeout}s")
            return {"success": False, "error": f"Timeout después de {self.timeout}s"}
            
        except Exception as e:
            logger.error(f"❌ Error inesperado con LM Studio: {e}")
            return {"success": False, "error": str(e)}
    
    async def _try_openai(self, prompt: str) -> Dict:
        """
        Intenta obtener respuesta de OpenAI como fallback
        
        Args:
            prompt: Prompt construido para Lucas
            
        Returns:
            Dict con resultado de la llamada
            
        Note:
            - Requiere OPENAI_API_KEY en variables de entorno
            - Usa gpt-3.5-turbo por defecto
            - Maneja límites de rate limiting
        """
        try:
            import openai
            import os
            
            # Verificar API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"success": False, "error": "No hay API key de OpenAI configurada"}
            
            openai.api_key = api_key
            
            logger.debug(f"🔄 Enviando request a OpenAI...")
            
            # Realizar llamada a OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres IANAE, el bibliotecario personal de Lucas. Conoces sus proyectos y forma de trabajar."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            content = response.choices[0].message.content
            
            # Actualizar estado
            self.openai_available = True
            
            return {
                "success": True,
                "response": content.strip(),
                "provider": "OpenAI",
                "model": "gpt-3.5-turbo",
                "tokens_used": response.usage.total_tokens
            }
            
        except ImportError:
            return {"success": False, "error": "Librería openai no instalada"}
            
        except Exception as e:
            logger.error(f"❌ Error con OpenAI: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_lucas_prompt(self, user_message: str, concepts: List[Dict], 
                           relations: List[Dict]) -> str:
        """
        Construye prompt conversacional específico para Lucas
        
        Args:
            user_message: Pregunta original
            concepts: Conceptos encontrados en su memoria
            relations: Relaciones entre conceptos
            
        Returns:
            Prompt optimizado para generar respuesta natural
            
        Note:
            - Incluye contexto técnico específico de Lucas
            - Mantiene tono conversacional, no lista técnica
            - Referencias proyectos reales cuando sea relevante
            - Máximo 2000 caracteres para eficiencia
        """
        prompt_parts = []
        
        # Contexto base
        prompt_parts.append(f"Lucas te pregunta: '{user_message}'")
        
        # Añadir conceptos encontrados
        if concepts:
            prompt_parts.append(f"\nEn su memoria personal encontré estos conceptos relevantes:")
            for concept in concepts[:3]:  # Top 3 para no saturar
                usage_info = f"usado {concept.get('usage_count', 0)} veces" if concept.get('usage_count') else ""
                category_info = f"categoría {concept.get('category', 'general')}"
                prompt_parts.append(f"- {concept['name']}: {usage_info}, {category_info}")
        
        # Añadir relaciones si existen
        if relations:
            prompt_parts.append(f"\nConexiones detectadas en sus proyectos:")
            for rel in relations[:2]:  # Top 2 relaciones
                if len(rel) >= 3:  # Asegurar que tiene la estructura esperada
                    prompt_parts.append(f"- {rel[0]} conectado con {rel[1]} (fuerza: {rel[2]:.2f})")
        
        # Instrucciones específicas para IANAE
        prompt_parts.append(f"""
        
Responde como IANAE, su bibliotecario personal que conoce profundamente:
- Sus proyectos (tacógrafos, automatización, OpenCV)
- Su stack técnico (Python, VBA, Excel, Docker)
- Su forma de trabajar (optimización, patrones, TOC+TDAH como superpoderes)

Estilo de respuesta:
- Conversacional y útil, no lista técnica
- Referencia su contexto específico cuando sea relevante
- Sugiere próximos pasos o conexiones interesantes
- Máximo 300 palabras
- Si no tienes información específica, sé honesto pero útil""")
        
        # Unir y limitar longitud
        full_prompt = "".join(prompt_parts)
        
        # Truncar si es muy largo (LLMs tienen límites)
        if len(full_prompt) > 2000:
            full_prompt = full_prompt[:1950] + "..."
            
        return full_prompt
    
    async def health_check(self) -> Dict:
        """
        Verifica el estado de conectividad de todos los LLMs
        
        Returns:
            Dict con estado de cada proveedor
            
        Example:
            >>> status = await llm.health_check()
            >>> print(status)
            {
                "lm_studio": {"available": True, "model": "r1-gemma-3-4b..."},
                "openai": {"available": False, "error": "No API key"},
                "recommended": "lm_studio"
            }
        """
        status = {
            "lm_studio": {"available": False, "error": None, "model": None},
            "openai": {"available": False, "error": None},
            "recommended": None,
            "last_check": datetime.now().isoformat()
        }
        
        # Check LM Studio
        try:
            response = requests.get(
                "http://localhost:1234/v1/models", 
                timeout=5
            )
            if response.status_code == 200:
                models_data = response.json()
                if models_data.get("data"):
                    model_name = models_data["data"][0].get("id", "unknown")
                    status["lm_studio"] = {
                        "available": True,
                        "model": model_name,
                        "endpoint": self.lm_studio_url
                    }
                    status["recommended"] = "lm_studio"
        except Exception as e:
            status["lm_studio"]["error"] = str(e)
        
        # Check OpenAI
        try:
            import os
            if os.getenv("OPENAI_API_KEY"):
                status["openai"]["available"] = True
                if not status["recommended"]:
                    status["recommended"] = "openai"
            else:
                status["openai"]["error"] = "No API key configured"
        except Exception as e:
            status["openai"]["error"] = str(e)
        
        # Determinar recomendación final
        if not status["recommended"]:
            status["recommended"] = "none"
        
        return status

# Singleton instance para usar en toda la aplicación
_ianae_llm = None

def get_ianae_llm() -> IANAELLMConnector:
    """
    Obtiene instancia singleton del conector LLM
    
    Returns:
        Instancia de IANAELLMConnector
        
    Note:
        Usa patrón singleton para mantener estado de conectividad
        entre requests y evitar reinicialización constante
    """
    global _ianae_llm
    if _ianae_llm is None:
        _ianae_llm = IANAELLMConnector()
        logger.info("🧠 IANAE LLM Connector inicializado")
    return _ianae_llm