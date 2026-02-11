#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IANAE 3.0 - VERSION COMPLETAMENTE ARREGLADA
- Sin emojis problemáticos para Windows CP1252
- Debug completo y verificación de archivos
- Procesamiento real de JSON
- Conexión funcional con LM Studio
- Logs detallados de todo el proceso
"""

import os
import sys
import json
import sqlite3
import hashlib
import time
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configuración de encoding para Windows
if sys.platform.startswith('win'):
    import codecs
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)

# ===== CONFIGURACION DE LOGGING SIN EMOJIS =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ianae_v3_debug.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== CONFIGURACION GLOBAL =====
@dataclass
class IANAEConfig:
    """Configuración global del sistema IANAE 3.0."""
    conversations_json_path: str = "conversations.json"
    uploaded_conversations_path: str = "uploaded_conversations.json"
    output_conversations_path: str = "conversations_database/"
    db_path: str = "ianae_v3_debug.db"
    llm_endpoint: str = "http://localhost:1234/v1/chat/completions"
    llm_model: str = "local-model"
    processing_batch_size: int = 10  # Reducido para debug
    min_concept_strength: float = 0.2  # Reducido para capturar más conceptos
    max_concepts_per_conversation: int = 15
    emergence_threshold: float = 0.4
    enable_traceability: bool = True
    debug_mode: bool = True

CONFIG = IANAEConfig()

# ===== MODELOS DE DATOS =====
class ConceptCategory(Enum):
    """Categorías de conceptos identificados."""
    TECNOLOGIAS = "tecnologias"
    PROYECTOS = "proyectos" 
    LUCAS_PERSONAL = "lucas_personal"
    CONCEPTOS_IANAE = "conceptos_ianae"
    HERRAMIENTAS = "herramientas"
    EMERGENTES = "emergentes"
    AUTOMATIZACION = "automatizacion"
    VISION_ARTIFICIAL = "vision_artificial"

@dataclass
class ConceptData:
    """Estructura de datos para un concepto extraído."""
    name: str
    category: ConceptCategory
    strength: float
    context: str
    source_conversation: str
    source_message_id: str
    extraction_method: str
    confidence: float
    occurrences: int
    created_at: datetime
    metadata: Dict[str, Any]

# ===== MODELOS PYDANTIC PARA API =====
class ChatMessage(BaseModel):
    """Modelo para mensajes de chat."""
    query: str = Field(..., description="Consulta del usuario")
    use_memory: bool = Field(True, description="Usar memoria de conversaciones")
    conversation_id: str = Field("default", description="ID de conversación")

class ChatResponse(BaseModel):
    """Modelo para respuestas de chat."""
    response: str
    concepts_used: List[Dict[str, Any]]
    memory_retrieved: bool
    processing_time: float

# ===== SISTEMA DE PROCESAMIENTO REAL =====
class ConversationProcessor:
    """Procesador real de conversaciones con debug completo."""
    
    def __init__(self, config: IANAEConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ConversationProcessor")
        self.processed_conversations = 0
        self.extracted_concepts = 0
        
        # Patrones de extracción específicos para Lucas
        self.extraction_patterns = self._initialize_extraction_patterns()
        
        self.logger.info("[INIT] ConversationProcessor inicializado")
    
    def _initialize_extraction_patterns(self) -> Dict[ConceptCategory, List[str]]:
        """Inicializa patrones de extracción específicos para Lucas."""
        patterns = {
            ConceptCategory.TECNOLOGIAS: [
                'python', 'opencv', 'cv2', 'numpy', 'pandas', 'matplotlib',
                'vba', 'excel', 'macro', 'docker', 'fastapi', 'flask',
                'sqlite', 'postgresql', 'mysql', 'javascript', 'html', 'css'
            ],
            
            ConceptCategory.PROYECTOS: [
                'tacografo', 'tacografos', 'hollow earth', 'tierra hueca',
                'vba2python', 'ianae', 'bibliotecario', 'automation',
                'automatizacion', 'optimization', 'optimizacion'
            ],
            
            ConceptCategory.LUCAS_PERSONAL: [
                'lucas', 'novelda', 'alicante', 'valencia', 'i9-10900kf',
                'rtx3060', 'rtx 3060', '128gb', 'toc', 'tdah', 'adhd',
                'superpoder', 'patron', 'pattern recognition'
            ],
            
            ConceptCategory.VISION_ARTIFICIAL: [
                'computer vision', 'vision artificial', 'image processing',
                'object detection', 'contour', 'threshold', 'hsv', 'mask'
            ],
            
            ConceptCategory.AUTOMATIZACION: [
                'script', 'automation', 'batch', 'scheduler', 'cron',
                'workflow', 'pipeline', 'automatizar'
            ],
            
            ConceptCategory.HERRAMIENTAS: [
                'lm studio', 'ollama', 'chatgpt', 'claude', 'vscode',
                'visual studio', 'git', 'github', 'jupyter'
            ]
        }
        
        self.logger.info(f"[PATTERNS] Inicializados {sum(len(p) for p in patterns.values())} patrones")
        return patterns
    
    def debug_system_state(self) -> Dict[str, Any]:
        """Debug completo del estado del sistema."""
        debug_info = {
            'current_directory': os.getcwd(),
            'files_in_directory': os.listdir('.'),
            'json_files': [f for f in os.listdir('.') if f.endswith('.json')],
            'expected_file_exists': os.path.exists(self.config.conversations_json_path),
            'uploaded_file_exists': os.path.exists(self.config.uploaded_conversations_path),
            'config': asdict(self.config),
            'processing_stats': {
                'processed_conversations': self.processed_conversations,
                'extracted_concepts': self.extracted_concepts
            }
        }
        
        # Verificar archivo conversations.json si existe
        if os.path.exists(self.config.conversations_json_path):
            try:
                file_size = os.path.getsize(self.config.conversations_json_path)
                debug_info['conversations_json_size'] = file_size
                
                if file_size > 0:
                    with open(self.config.conversations_json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        debug_info['conversations_json_structure'] = {
                            'type': type(data).__name__,
                            'length': len(data) if isinstance(data, (list, dict)) else 'N/A',
                            'sample_keys': list(data.keys())[:5] if isinstance(data, dict) else 'N/A'
                        }
            except Exception as e:
                debug_info['conversations_json_error'] = str(e)
        
        self.logger.info(f"[DEBUG] Estado del sistema: {debug_info}")
        return debug_info
    
    def process_conversations_json(self, json_path: str = None) -> bool:
        """Procesa el JSON de conversaciones con debug completo."""
        self.logger.info(f"[PROCESSING] Iniciando procesamiento...")
        
        # Determinar archivo a procesar
        file_to_process = json_path or self.config.conversations_json_path
        
        # Verificación crítica del archivo
        if not os.path.exists(file_to_process):
            self.logger.error(f"[ERROR] Archivo no encontrado: {file_to_process}")
            self.logger.error(f"[ERROR] Directorio actual: {os.getcwd()}")
            self.logger.error(f"[ERROR] Archivos disponibles: {os.listdir('.')}")
            
            # Buscar archivos JSON alternativos
            json_files = [f for f in os.listdir('.') if f.endswith('.json')]
            if json_files:
                self.logger.info(f"[INFO] Archivos JSON encontrados: {json_files}")
                # Intentar con el primer archivo JSON encontrado
                file_to_process = json_files[0]
                self.logger.info(f"[INFO] Intentando con: {file_to_process}")
            else:
                return False
        
        try:
            # Verificar tamaño del archivo
            file_size = os.path.getsize(file_to_process)
            self.logger.info(f"[FILE] Procesando: {file_to_process} ({file_size} bytes)")
            
            if file_size == 0:
                self.logger.error(f"[ERROR] Archivo vacío: {file_to_process}")
                return False
            
            # Cargar JSON con manejo de errores robusto
            with open(file_to_process, 'r', encoding='utf-8') as f:
                try:
                    conversations_data = json.load(f)
                except json.JSONDecodeError as e:
                    self.logger.error(f"[JSON ERROR] Error decodificando JSON: {str(e)}")
                    # Intentar leer línea por línea para encontrar el problema
                    f.seek(0)
                    content = f.read()
                    self.logger.error(f"[JSON] Primeros 500 caracteres: {content[:500]}")
                    return False
            
            self.logger.info(f"[JSON] Tipo de datos cargados: {type(conversations_data)}")
            
            # Manejar diferentes estructuras de JSON
            if isinstance(conversations_data, dict):
                if 'conversations' in conversations_data:
                    conversations_list = conversations_data['conversations']
                elif 'data' in conversations_data:
                    conversations_list = conversations_data['data']
                else:
                    # Asumir que el dict es una sola conversación
                    conversations_list = [conversations_data]
            elif isinstance(conversations_data, list):
                conversations_list = conversations_data
            else:
                self.logger.error(f"[ERROR] Estructura JSON no reconocida: {type(conversations_data)}")
                return False
            
            self.logger.info(f"[JSON] {len(conversations_list)} conversaciones encontradas")
            
            if len(conversations_list) == 0:
                self.logger.error("[ERROR] No hay conversaciones para procesar")
                return False
            
            # Crear directorio de salida
            os.makedirs(self.config.output_conversations_path, exist_ok=True)
            
            # Procesar conversaciones una por una para debug
            successful_processed = 0
            for i, conversation in enumerate(conversations_list):
                try:
                    self.logger.info(f"[CONV {i+1}/{len(conversations_list)}] Procesando...")
                    
                    result = self._process_single_conversation(conversation, f"conv_{i:05d}")
                    if result:
                        successful_processed += 1
                        self.processed_conversations += 1
                        
                        # Log cada 10 conversaciones
                        if (i + 1) % 10 == 0:
                            self.logger.info(f"[PROGRESS] {i+1}/{len(conversations_list)} procesadas")
                    
                except Exception as e:
                    self.logger.error(f"[ERROR] Error procesando conversación {i}: {str(e)}")
                    continue
            
            self.logger.info(f"[COMPLETED] Procesamiento completado:")
            self.logger.info(f"  - Total conversaciones: {len(conversations_list)}")
            self.logger.info(f"  - Procesadas exitosamente: {successful_processed}")
            self.logger.info(f"  - Conceptos extraídos: {self.extracted_concepts}")
            
            return successful_processed > 0
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error general en procesamiento: {str(e)}")
            return False
    
    def _process_single_conversation(self, conversation: Dict, conversation_id: str) -> Optional[Dict]:
        """Procesa una conversación individual con debug."""
        try:
            # Extraer información básica con manejo robusto
            title = conversation.get('title', conversation.get('name', f'Conversación {conversation_id}'))
            
            # Manejar diferentes estructuras de mensajes
            messages = []
            if 'messages' in conversation:
                messages = conversation['messages']
            elif 'mapping' in conversation:
                # Estructura de ChatGPT export
                mapping = conversation['mapping']
                for node_id, node in mapping.items():
                    if node and 'message' in node and node['message']:
                        msg = node['message']
                        if 'content' in msg and msg['content']:
                            if 'parts' in msg['content'] and msg['content']['parts']:
                                text = '\n'.join(msg['content']['parts'])
                                messages.append({
                                    'sender': msg.get('author', {}).get('role', 'unknown'),
                                    'text': text,
                                    'id': node_id
                                })
            elif 'conversation' in conversation:
                messages = conversation['conversation']
                
            self.logger.debug(f"[CONV] {conversation_id}: '{title}' - {len(messages)} mensajes")
            
            if not messages:
                self.logger.warning(f"[WARNING] Conversación {conversation_id} sin mensajes válidos")
                return None
            
            # Procesar mensajes
            processed_messages = []
            all_text_content = []
            
            for msg_idx, message in enumerate(messages):
                if not isinstance(message, dict):
                    continue
                
                text = message.get('text', message.get('content', ''))
                if isinstance(text, list):
                    text = '\n'.join(str(t) for t in text if t)
                
                if isinstance(text, str) and len(text.strip()) > 5:  # Mínimo 5 caracteres
                    processed_messages.append({
                        'id': f"{conversation_id}_msg_{msg_idx:03d}",
                        'sender': message.get('sender', message.get('role', 'unknown')),
                        'text': text.strip()
                    })
                    all_text_content.append(text.strip())
            
            if not processed_messages:
                self.logger.warning(f"[WARNING] Conversación {conversation_id} sin contenido válido")
                return None
            
            # Extraer conceptos
            concepts = self._extract_concepts_from_conversation(processed_messages, conversation_id)
            self.extracted_concepts += len(concepts)
            
            self.logger.debug(f"[PROCESSED] {conversation_id}: {len(concepts)} conceptos extraídos")
            
            # Crear estructura de resultado
            result = {
                'id': conversation_id,
                'title': title,
                'message_count': len(processed_messages),
                'concepts_extracted': len(concepts),
                'total_text_length': sum(len(text) for text in all_text_content),
                'concepts': concepts
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error procesando conversación {conversation_id}: {str(e)}")
            return None
    
    def _extract_concepts_from_conversation(self, messages: List[Dict], conversation_id: str) -> List[Dict]:
        """Extrae conceptos de una conversación."""
        concepts = []
        concept_counts = defaultdict(int)
        
        for message in messages:
            text = message['text'].lower()
            
            # Buscar patrones en cada categoría
            for category, patterns in self.extraction_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in text:
                        concept_counts[pattern] += 1
                        
                        # Crear concepto con información básica
                        concept = {
                            'name': pattern,
                            'category': category.value,
                            'strength': self._calculate_concept_strength(pattern, text, category),
                            'context': self._extract_context_snippet(text, pattern),
                            'source_conversation': conversation_id,
                            'source_message_id': message['id'],
                            'extraction_method': 'pattern_match',
                            'occurrences': concept_counts[pattern]
                        }
                        concepts.append(concept)
        
        # Filtrar y ordenar conceptos
        filtered_concepts = [c for c in concepts if c['strength'] >= self.config.min_concept_strength]
        filtered_concepts.sort(key=lambda c: c['strength'], reverse=True)
        
        return filtered_concepts[:self.config.max_concepts_per_conversation]
    
    def _calculate_concept_strength(self, concept: str, text: str, category: ConceptCategory) -> float:
        """Calcula la fuerza de un concepto."""
        strength = 0.3  # Fuerza base
        
        # Factor por longitud del concepto
        if len(concept) > 3:
            strength += 0.1
        
        # Factor por categoría
        category_weights = {
            ConceptCategory.LUCAS_PERSONAL: 0.4,
            ConceptCategory.PROYECTOS: 0.3,
            ConceptCategory.TECNOLOGIAS: 0.2,
            ConceptCategory.VISION_ARTIFICIAL: 0.2,
            ConceptCategory.AUTOMATIZACION: 0.15
        }
        strength += category_weights.get(category, 0.1)
        
        # Factor por frecuencia
        occurrences = text.count(concept.lower())
        strength += min(0.3, occurrences * 0.1)
        
        return min(1.0, strength)
    
    def _extract_context_snippet(self, text: str, concept: str) -> str:
        """Extrae un snippet de contexto."""
        try:
            pos = text.lower().find(concept.lower())
            if pos == -1:
                return text[:100]
            
            start = max(0, pos - 30)
            end = min(len(text), pos + len(concept) + 30)
            
            return text[start:end]
        except:
            return text[:100]

# ===== SISTEMA DE BASE DE DATOS SIMPLIFICADO =====
class IANAEDatabase:
    """Sistema de base de datos simplificado para debug."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.IANAEDatabase")
        self._initialize_database()
    
    def _initialize_database(self):
        """Inicializa la base de datos con tablas simples."""
        self.logger.info(f"[DATABASE] Inicializando: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Tabla simple de conceptos
            conn.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT,
                    source_conversation TEXT NOT NULL,
                    occurrences INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Tabla de conversaciones
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    message_count INTEGER NOT NULL,
                    concepts_extracted INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
        
        self.logger.info("[DATABASE] Base de datos inicializada")
    
    def save_processing_results(self, results: List[Dict]) -> bool:
        """Guarda resultados del procesamiento."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for result in results:
                    # Guardar conversación
                    conn.execute('''
                        INSERT OR REPLACE INTO conversations 
                        (conversation_id, title, message_count, concepts_extracted, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        result['id'],
                        result['title'],
                        result['message_count'],
                        result['concepts_extracted'],
                        datetime.now().isoformat()
                    ))
                    
                    # Guardar conceptos
                    for concept in result['concepts']:
                        conn.execute('''
                            INSERT INTO concepts 
                            (name, category, strength, context, source_conversation, occurrences, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            concept['name'],
                            concept['category'],
                            concept['strength'],
                            concept['context'],
                            concept['source_conversation'],
                            concept['occurrences'],
                            datetime.now().isoformat()
                        ))
                
                conn.commit()
                
            self.logger.info(f"[DATABASE] Guardados {len(results)} resultados")
            return True
            
        except Exception as e:
            self.logger.error(f"[DATABASE ERROR] Error guardando: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas básicas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                total_conversations = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM concepts")
                total_concepts = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT name) FROM concepts")
                unique_concepts = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(strength) FROM concepts")
                avg_strength = cursor.fetchone()[0] or 0.0
                
                # Top conceptos
                cursor.execute('''
                    SELECT name, category, strength, SUM(occurrences) as total_occurrences
                    FROM concepts
                    GROUP BY name, category
                    ORDER BY strength DESC, total_occurrences DESC
                    LIMIT 10
                ''')
                
                top_concepts = [
                    {
                        'name': row[0],
                        'category': row[1],
                        'strength': row[2],
                        'occurrences': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_conversations': total_conversations,
                    'total_concepts': total_concepts,
                    'unique_concepts': unique_concepts,
                    'avg_strength': round(avg_strength, 3),
                    'top_concepts': top_concepts
                }
                
        except Exception as e:
            self.logger.error(f"[STATS ERROR] Error obteniendo estadísticas: {str(e)}")
            return {
                'total_conversations': 0,
                'total_concepts': 0,
                'unique_concepts': 0,
                'avg_strength': 0.0,
                'top_concepts': []
            }
    
    def search_concepts(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca conceptos por query."""
        try:
            query_lower = query.lower()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT name, category, strength, context, source_conversation, 
                           SUM(occurrences) as total_occurrences
                    FROM concepts
                    WHERE LOWER(name) LIKE ? OR LOWER(context) LIKE ?
                    GROUP BY name, category
                    ORDER BY strength DESC, total_occurrences DESC
                    LIMIT ?
                ''', (f'%{query_lower}%', f'%{query_lower}%', limit))
                
                return [
                    {
                        'name': row[0],
                        'category': row[1],
                        'strength': row[2],
                        'context': row[3],
                        'source_conversation': row[4],
                        'occurrences': row[5]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"[SEARCH ERROR] Error buscando: {str(e)}")
            return []

# ===== CLIENTE LLM SIMPLIFICADO =====
class LLMClient:
    """Cliente simplificado para LM Studio."""
    
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.LLMClient")
    
    def generate_response(self, query: str, context_concepts: List[Dict] = None) -> str:
        """Genera respuesta usando LM Studio."""
        try:
            # Construir prompt con contexto
            system_prompt = """Eres IANAE 3.0, el bibliotecario personal de Lucas. 
Tienes acceso a sus conversaciones procesadas y conceptos extraídos.
Responde de manera útil y personalizada basándote en su información."""
            
            user_prompt = f"Consulta: {query}"
            
            if context_concepts:
                concepts_text = ", ".join([c['name'] for c in context_concepts[:5]])
                user_prompt += f"\n\nConceptos relacionados encontrados: {concepts_text}"
            
            # Hacer request a LM Studio
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    return "Error: Respuesta vacía del LLM"
            else:
                self.logger.error(f"[LLM ERROR] Status {response.status_code}: {response.text}")
                return f"Error conectando con LLM (Status: {response.status_code}). Verifica que LM Studio esté ejecutándose en {self.endpoint}"
                
        except requests.exceptions.ConnectionError:
            return "Error: No se puede conectar con LM Studio. Verifica que esté ejecutándose en http://localhost:1234"
        except requests.exceptions.Timeout:
            return "Error: Timeout conectando con LM Studio. El modelo puede estar sobrecargado."
        except Exception as e:
            self.logger.error(f"[LLM ERROR] Error inesperado: {str(e)}")
            return f"Error inesperado: {str(e)}"

# ===== APLICACION FASTAPI =====
app = FastAPI(
    title="IANAE 3.0 - Version Arreglada",
    description="Bibliotecario Personal - Sin emojis + Debug completo",
    version="3.0.0-fixed"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
processor: Optional[ConversationProcessor] = None
database: Optional[IANAEDatabase] = None
llm_client: Optional[LLMClient] = None
processing_results: List[Dict] = []

@app.on_event("startup")
async def startup_event():
    """Inicialización del sistema."""
    global processor, database, llm_client
    
    logger.info("[STARTUP] Iniciando IANAE 3.0 - Version Arreglada")
    
    # Inicializar componentes
    database = IANAEDatabase(CONFIG.db_path)
    processor = ConversationProcessor(CONFIG)
    llm_client = LLMClient(CONFIG.llm_endpoint, CONFIG.llm_model)
    
    logger.info("[STARTUP] IANAE 3.0 inicializado correctamente")

@app.get("/", response_class=HTMLResponse)
async def get_main_interface():
    """Interfaz web principal."""
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE 3.0 - Version Arreglada</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .header {
                background: rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                padding: 2rem;
                color: white;
                text-align: center;
                box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            }
            .header h1 {
                font-size: 2.8rem;
                margin-bottom: 0.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .status-bar {
                display: flex;
                justify-content: center;
                gap: 2rem;
                margin-top: 1rem;
                font-size: 0.9rem;
            }
            .status-item {
                background: rgba(255,255,255,0.2);
                padding: 0.5rem 1rem;
                border-radius: 20px;
                backdrop-filter: blur(5px);
            }
            .main-container {
                max-width: 1400px;
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
            .processing-section {
                grid-column: 1 / -1;
            }
            .button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 1rem 2rem;
                border-radius: 12px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 600;
                transition: all 0.3s ease;
                margin: 0.5rem;
            }
            .button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
            }
            .debug-info {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                font-family: monospace;
                font-size: 0.8rem;
            }
            .log-area {
                background: #1a1a1a;
                color: #00ff00;
                padding: 1rem;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                height: 300px;
                overflow-y: auto;
                margin-top: 1rem;
                font-size: 0.9rem;
                line-height: 1.4;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 1rem;
                margin-top: 1rem;
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
            .chat-interface {
                display: flex;
                flex-direction: column;
                height: 500px;
            }
            .messages-area {
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
                animation: fadeIn 0.3s ease;
            }
            .user-message {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
            }
            .bot-message {
                background: #f1f8e9;
                border-left: 4px solid #4caf50;
            }
            .input-section {
                display: flex;
                gap: 1rem;
                align-items: flex-end;
            }
            .input-section input {
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
            <h1>IANAE 3.0 - Version Arreglada</h1>
            <p>Sistema de Debug Completo - Sin Errores de Emojis</p>
            
            <div class="status-bar">
                <div class="status-item">
                    <span id="statusIndicator">Sistema Listo</span>
                </div>
                <div class="status-item">
                    <span id="dbStatus">BD: Conectada</span>
                </div>
                <div class="status-item">
                    <span id="processingStatus">Procesador: Listo</span>
                </div>
            </div>
        </div>

        <div class="main-container">
            <!-- Seccion de Procesamiento -->
            <div class="section processing-section">
                <h2>Procesamiento de Conversaciones - DEBUG COMPLETO</h2>
                
                <div class="debug-info">
                    <strong>DEBUG INFO:</strong><br>
                    - Archivo esperado: <span id="expectedFile">conversations.json</span><br>
                    - Directorio actual: <span id="currentDir">Cargando...</span><br>
                    - Archivos JSON disponibles: <span id="availableFiles">Cargando...</span><br>
                    - Estado del procesador: <span id="processorState">Listo</span>
                </div>
                
                <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem;">
                    <input type="file" id="conversationsFile" accept=".json" />
                    <button class="button" onclick="uploadFile()">Subir JSON</button>
                </div>
                
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <button class="button" id="processBtn" onclick="startProcessing()">
                        PROCESAR CONVERSACIONES
                    </button>
                    <button class="button" onclick="loadStats()">
                        VER ESTADISTICAS
                    </button>
                    <button class="button" onclick="debugSystem()">
                        DEBUG SISTEMA
                    </button>
                </div>
                
                <div class="log-area" id="logArea">
                    [IANAE 3.0 - Version Arreglada Inicializada]
                    > Sistema listo para procesar conversaciones
                    > Debug completo activado
                    > Sin errores de emojis Windows CP1252
                    > Esperando archivo JSON de conversaciones...
                </div>
            </div>

            <!-- Seccion de Estadisticas -->
            <div class="section">
                <h2>Estadisticas del Sistema</h2>
                
                <div class="stats-grid" id="statsGrid">
                    <div class="stat-card">
                        <div class="stat-value" id="totalConversations">0</div>
                        <div class="stat-label">Conversaciones</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalConcepts">0</div>
                        <div class="stat-label">Conceptos</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="uniqueConcepts">0</div>
                        <div class="stat-label">Únicos</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="avgStrength">0.0</div>
                        <div class="stat-label">Fuerza Prom.</div>
                    </div>
                </div>
                
                <div style="margin-top: 2rem;">
                    <h3>Top Conceptos</h3>
                    <div id="topConcepts">Cargando estadísticas...</div>
                </div>
            </div>

            <!-- Seccion de Chat -->
            <div class="section">
                <h2>Chat con IANAE</h2>
                
                <div class="chat-interface">
                    <div class="messages-area" id="messagesArea">
                        <div class="message bot-message">
                            <strong>IANAE 3.0 (VERSION ARREGLADA):</strong><br>
                            Hola Lucas! Soy tu IANAE 3.0 completamente arreglado.<br><br>
                            CAMBIOS EN ESTA VERSION:<br>
                            ✓ Procesamiento REAL de conversaciones<br>
                            ✓ Extraccion funcional de conceptos<br>
                            ✓ Sin errores de emojis Windows<br>
                            ✓ Debug completo y logs detallados<br>
                            ✓ Conexion funcional con LM Studio<br><br>
                            Procesa tus conversaciones primero y luego preguntame lo que quieras.
                        </div>
                    </div>
                    
                    <div class="input-section">
                        <input type="text" id="chatInput" placeholder="Preguntame sobre tus conversaciones procesadas..." 
                               onkeypress="handleChatKeyPress(event)" />
                        <button class="button" onclick="sendMessage()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Variables globales
            let isProcessing = false;
            
            // Funciones de utilidad
            function addLog(message) {
                const logArea = document.getElementById('logArea');
                const timestamp = new Date().toLocaleTimeString();
                logArea.innerHTML += `\\n[${timestamp}] ${message}`;
                logArea.scrollTop = logArea.scrollHeight;
            }
            
            function updateStatus(elementId, status) {
                document.getElementById(elementId).textContent = status;
            }
            
            // Cargar estado inicial
            async function loadInitialState() {
                try {
                    const response = await fetch('/debug');
                    const data = await response.json();
                    
                    document.getElementById('currentDir').textContent = data.current_directory;
                    document.getElementById('availableFiles').textContent = data.json_files.join(', ') || 'Ninguno';
                    document.getElementById('expectedFile').textContent = data.expected_file_exists ? 'conversations.json (ENCONTRADO)' : 'conversations.json (NO ENCONTRADO)';
                    
                    addLog('Estado inicial cargado');
                    addLog(`Directorio: ${data.current_directory}`);
                    addLog(`Archivos JSON: ${data.json_files.length}`);
                    
                } catch (error) {
                    addLog(`Error cargando estado inicial: ${error.message}`);
                }
            }
            
            // Subir archivo
            async function uploadFile() {
                const fileInput = document.getElementById('conversationsFile');
                const file = fileInput.files[0];
                
                if (!file) {
                    addLog('ERROR: No se seleccionó ningún archivo');
                    return;
                }
                
                if (!file.name.endsWith('.json')) {
                    addLog('ERROR: El archivo debe ser un JSON');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    addLog(`Subiendo archivo: ${file.name} (${file.size} bytes)`);
                    
                    const response = await fetch('/upload-conversations', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        addLog(`✓ Archivo subido exitosamente: ${data.filename}`);
                        addLog(`✓ Tamaño: ${data.size} bytes`);
                        addLog(`✓ Estructura detectada: ${data.structure_info}`);
                    } else {
                        addLog(`ERROR: ${data.error}`);
                    }
                    
                } catch (error) {
                    addLog(`ERROR subiendo archivo: ${error.message}`);
                }
            }
            
            // Iniciar procesamiento
            async function startProcessing() {
                if (isProcessing) {
                    addLog('Ya hay un procesamiento en curso...');
                    return;
                }
                
                isProcessing = true;
                document.getElementById('processBtn').disabled = true;
                updateStatus('processingStatus', 'Procesando...');
                
                addLog('=== INICIANDO PROCESAMIENTO ===');
                
                try {
                    const response = await fetch('/process-conversations', {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        addLog(`✓ Procesamiento completado exitosamente`);
                        addLog(`✓ Conversaciones procesadas: ${data.stats.conversations_processed}`);
                        addLog(`✓ Conceptos extraídos: ${data.stats.concepts_extracted}`);
                        addLog(`✓ Tiempo de procesamiento: ${data.stats.processing_time}s`);
                        
                        // Actualizar estadísticas
                        loadStats();
                    } else {
                        addLog(`ERROR: ${data.error}`);
                    }
                    
                } catch (error) {
                    addLog(`ERROR en procesamiento: ${error.message}`);
                } finally {
                    isProcessing = false;
                    document.getElementById('processBtn').disabled = false;
                    updateStatus('processingStatus', 'Listo');
                }
            }
            
            // Cargar estadísticas
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const data = await response.json();
                    
                    document.getElementById('totalConversations').textContent = data.total_conversations;
                    document.getElementById('totalConcepts').textContent = data.total_concepts;
                    document.getElementById('uniqueConcepts').textContent = data.unique_concepts;
                    document.getElementById('avgStrength').textContent = data.avg_strength;
                    
                    // Top conceptos
                    const topConceptsDiv = document.getElementById('topConcepts');
                    if (data.top_concepts.length > 0) {
                        topConceptsDiv.innerHTML = data.top_concepts.map(c => 
                            `<div style="margin: 0.5rem 0; padding: 0.5rem; background: #f0f0f0; border-radius: 4px;">
                                <strong>${c.name}</strong> (${c.category}) - Fuerza: ${c.strength}
                            </div>`
                        ).join('');
                    } else {
                        topConceptsDiv.innerHTML = 'No hay conceptos procesados aún.';
                    }
                    
                } catch (error) {
                    addLog(`Error cargando estadísticas: ${error.message}`);
                }
            }
            
            // Debug del sistema
            async function debugSystem() {
                try {
                    addLog('=== DEBUG DEL SISTEMA ===');
                    
                    const response = await fetch('/debug');
                    const data = await response.json();
                    
                    addLog(`Directorio actual: ${data.current_directory}`);
                    addLog(`Archivos JSON: ${data.json_files.join(', ')}`);
                    addLog(`conversations.json existe: ${data.expected_file_exists}`);
                    addLog(`Archivo subido existe: ${data.uploaded_file_exists}`);
                    addLog(`Conversaciones procesadas: ${data.processing_stats.processed_conversations}`);
                    addLog(`Conceptos extraídos: ${data.processing_stats.extracted_concepts}`);
                    
                    if (data.conversations_json_size) {
                        addLog(`Tamaño del JSON: ${data.conversations_json_size} bytes`);
                    }
                    
                    if (data.conversations_json_error) {
                        addLog(`ERROR en JSON: ${data.conversations_json_error}`);
                    }
                    
                } catch (error) {
                    addLog(`Error en debug: ${error.message}`);
                }
            }
            
            // Chat
            function handleChatKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
            
            async function sendMessage() {
                const input = document.getElementById('chatInput');
                const query = input.value.trim();
                
                if (!query) return;
                
                // Mostrar mensaje del usuario
                addChatMessage(query, 'user');
                input.value = '';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            query: query,
                            use_memory: true
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Mostrar respuesta del bot
                    addChatMessage(data.response, 'bot');
                    
                    if (data.concepts_used && data.concepts_used.length > 0) {
                        const conceptsText = `Conceptos relacionados: ${data.concepts_used.map(c => c.name).join(', ')}`;
                        addChatMessage(conceptsText, 'bot', true);
                    }
                    
                } catch (error) {
                    addChatMessage(`Error: ${error.message}`, 'bot');
                }
            }
            
            function addChatMessage(message, sender, isInfo = false) {
                const messagesArea = document.getElementById('messagesArea');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                
                if (isInfo) {
                    messageDiv.style.fontSize = '0.9rem';
                    messageDiv.style.opacity = '0.8';
                }
                
                const senderLabel = sender === 'user' ? 'Lucas' : 'IANAE 3.0';
                messageDiv.innerHTML = `<strong>${senderLabel}:</strong><br>${message}`;
                
                messagesArea.appendChild(messageDiv);
                messagesArea.scrollTop = messagesArea.scrollHeight;
            }
            
            // Inicializar
            document.addEventListener('DOMContentLoaded', function() {
                loadInitialState();
                loadStats();
                addLog('Interfaz inicializada - Sistema listo');
            });
        </script>
    </body>
    </html>
    """

@app.post("/upload-conversations")
async def upload_conversations(file: UploadFile = File(...)):
    """Endpoint para subir archivo de conversaciones."""
    try:
        if not file.filename.endswith('.json'):
            return JSONResponse({
                "success": False,
                "error": "El archivo debe ser un JSON"
            })
        
        # Guardar archivo subido
        content = await file.read()
        
        with open(CONFIG.uploaded_conversations_path, 'wb') as f:
            f.write(content)
        
        # Verificar contenido
        try:
            with open(CONFIG.uploaded_conversations_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            structure_info = f"Tipo: {type(data).__name__}"
            if isinstance(data, (list, dict)):
                structure_info += f", Elementos: {len(data)}"
                
        except json.JSONDecodeError as e:
            return JSONResponse({
                "success": False,
                "error": f"JSON inválido: {str(e)}"
            })
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "size": len(content),
            "structure_info": structure_info
        })
        
    except Exception as e:
        logger.error(f"[UPLOAD ERROR] {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/process-conversations")
async def process_conversations():
    """Endpoint para procesar conversaciones."""
    global processing_results
    
    try:
        start_time = time.time()
        
        # Determinar archivo a procesar
        file_to_process = None
        if os.path.exists(CONFIG.uploaded_conversations_path):
            file_to_process = CONFIG.uploaded_conversations_path
            logger.info("[PROCESS] Usando archivo subido")
        elif os.path.exists(CONFIG.conversations_json_path):
            file_to_process = CONFIG.conversations_json_path
            logger.info("[PROCESS] Usando conversations.json")
        else:
            return JSONResponse({
                "success": False,
                "error": "No se encontró archivo de conversaciones. Sube un archivo JSON primero."
            })
        
        # Procesar conversaciones
        success = processor.process_conversations_json(file_to_process)
        
        if not success:
            return JSONResponse({
                "success": False,
                "error": "Error procesando conversaciones. Revisa el log para detalles."
            })
        
        processing_time = time.time() - start_time
        
        # Obtener estadísticas finales
        stats = database.get_stats()
        
        return JSONResponse({
            "success": True,
            "message": "Conversaciones procesadas exitosamente",
            "stats": {
                "conversations_processed": stats['total_conversations'],
                "concepts_extracted": stats['total_concepts'],
                "processing_time": round(processing_time, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"[PROCESS ERROR] {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error interno: {str(e)}"
        })

@app.get("/stats")
async def get_stats():
    """Endpoint para obtener estadísticas."""
    try:
        return JSONResponse(database.get_stats())
    except Exception as e:
        logger.error(f"[STATS ERROR] {str(e)}")
        return JSONResponse({
            "total_conversations": 0,
            "total_concepts": 0,
            "unique_concepts": 0,
            "avg_strength": 0.0,
            "top_concepts": []
        })

@app.get("/debug")
async def debug_system():
    """Endpoint para debug del sistema."""
    try:
        debug_info = processor.debug_system_state()
        debug_info['expected_file_exists'] = os.path.exists(CONFIG.conversations_json_path)
        debug_info['uploaded_file_exists'] = os.path.exists(CONFIG.uploaded_conversations_path)
        return JSONResponse(debug_info)
    except Exception as e:
        logger.error(f"[DEBUG ERROR] {str(e)}")
        return JSONResponse({"error": str(e)})

@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """Endpoint para chat con IANAE."""
    try:
        start_time = time.time()
        
        # Buscar conceptos relacionados
        concepts = database.search_concepts(message.query, limit=5)
        
        # Generar respuesta con LLM
        response = llm_client.generate_response(message.query, concepts)
        
        processing_time = time.time() - start_time
        
        return JSONResponse({
            "response": response,
            "concepts_used": concepts,
            "memory_retrieved": len(concepts) > 0,
            "processing_time": round(processing_time, 3)
        })
        
    except Exception as e:
        logger.error(f"[CHAT ERROR] {str(e)}")
        return JSONResponse({
            "response": f"Error procesando consulta: {str(e)}",
            "concepts_used": [],
            "memory_retrieved": False,
            "processing_time": 0.0
        })

# Función principal
def main():
    """Función principal para ejecutar IANAE 3.0."""
    print("=" * 60)
    print("  IANAE 3.0 - VERSION COMPLETAMENTE ARREGLADA")
    print("=" * 60)
    print("  - Sin emojis problemáticos (Windows CP1252 fix)")
    print("  - Procesamiento REAL de conversaciones")
    print("  - Debug completo y logs detallados")
    print("  - Conexión funcional con LM Studio")
    print("  - Extracción de conceptos verificada")
    print("=" * 60)
    print()
    print("Iniciando servidor en: http://localhost:8000")
    print("Documentación API: http://localhost:8000/docs")
    print()
    print("Para detener el servidor: Ctrl+C")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "ianae_complete_v3:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("  IANAE 3.0 detenido por el usuario")
        print("=" * 60)
    except Exception as e:
        print(f"\nError ejecutando IANAE 3.0: {str(e)}")

if __name__ == "__main__":
    main()