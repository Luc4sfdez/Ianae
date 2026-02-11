#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IANAE 3.0 - Sistema Completo con Procesamiento de Conversaciones y Trazabilidad

Este módulo implementa el sistema completo IANAE que:
1. Procesa el JSON gordo de conversaciones
2. Extrae conceptos con trazabilidad completa
3. Crea resúmenes con valor y patrones
4. Implementa pensamiento emergente
5. Proporciona interfaz web y API REST

Autor: Sistema IANAE para Lucas
Ubicación: Novelda, Alicante, España
Versión: 3.0.0
"""

import os
import json
import sqlite3
import numpy as np
import networkx as nx
import hashlib
import pickle
import time
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ===== CONFIGURACIÓN DE LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ianae_v3.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CONFIGURACIÓN GLOBAL =====
@dataclass
class IANAEConfig:
    """
    Configuración global del sistema IANAE 3.0.
    
    Attributes:
        conversations_json_path: Ruta al JSON gordo de conversaciones
        output_conversations_path: Ruta donde guardar conversaciones individuales
        db_path: Ruta de la base de datos SQLite
        llm_endpoint: Endpoint del LLM local
        llm_model: Modelo a usar
        processing_batch_size: Tamaño de lote para procesamiento
        min_concept_strength: Fuerza mínima para considerar un concepto
        max_concepts_per_conversation: Máximo conceptos por conversación
        emergence_threshold: Umbral para detección de emergencia
        enable_traceability: Habilitar trazabilidad completa
        debug_mode: Modo debug con logging extendido
    """
    conversations_json_path: str = "conversations.json"
    output_conversations_path: str = "conversations_database/"
    db_path: str = "ianae_v3_traced.db"
    llm_endpoint: str = "http://localhost:1234/v1/chat/completions"
    llm_model: str = "local-model"
    processing_batch_size: int = 50
    min_concept_strength: float = 0.3
    max_concepts_per_conversation: int = 20
    emergence_threshold: float = 0.4
    enable_traceability: bool = True
    debug_mode: bool = True

CONFIG = IANAEConfig()

# ===== MODELOS DE DATOS =====
class ConceptCategory(Enum):
    """Categorías de conceptos identificados en el sistema."""
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
    """
    Estructura de datos para un concepto extraído.
    
    Attributes:
        name: Nombre del concepto
        category: Categoría del concepto
        strength: Fuerza/relevancia del concepto (0.0-1.0)
        context: Contexto donde apareció el concepto
        source_conversation: ID de la conversación fuente
        source_message_id: ID del mensaje específico
        extraction_method: Método usado para extraer el concepto
        confidence: Confianza en la extracción (0.0-1.0)
        occurrences: Número de veces que aparece
        created_at: Timestamp de creación
        metadata: Datos adicionales del concepto
    """
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

@dataclass
class ConversationSummary:
    """
    Resumen de una conversación procesada.
    
    Attributes:
        conversation_id: ID único de la conversación
        title: Título de la conversación
        participants: Lista de participantes
        message_count: Número de mensajes
        concepts_extracted: Número de conceptos extraídos
        key_topics: Temas principales identificados
        summary_text: Resumen textual de la conversación
        value_score: Puntuación de valor de la conversación
        patterns_detected: Patrones detectados
        processing_time: Tiempo de procesamiento
        created_at: Timestamp de procesamiento
        metadata: Metadatos adicionales
    """
    conversation_id: str
    title: str
    participants: List[str]
    message_count: int
    concepts_extracted: int
    key_topics: List[str]
    summary_text: str
    value_score: float
    patterns_detected: List[str]
    processing_time: float
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class EmergencePattern:
    """
    Patrón emergente detectado en el sistema.
    
    Attributes:
        pattern_id: ID único del patrón
        pattern_type: Tipo de patrón emergente
        concepts_involved: Conceptos involucrados en el patrón
        strength: Fuerza del patrón emergente
        discovery_method: Método de descubrimiento
        context: Contexto donde se detectó
        significance: Significancia del patrón
        created_at: Timestamp de detección
        metadata: Metadatos del patrón
    """
    pattern_id: str
    pattern_type: str
    concepts_involved: List[str]
    strength: float
    discovery_method: str
    context: str
    significance: float
    created_at: datetime
    metadata: Dict[str, Any]

# ===== MODELOS PYDANTIC PARA API =====
class ChatMessage(BaseModel):
    """Modelo para mensajes de chat."""
    query: str = Field(..., description="Consulta del usuario")
    use_memory: bool = Field(True, description="Usar memoria de conversaciones")
    use_emergence: bool = Field(False, description="Usar pensamiento emergente")
    conversation_id: str = Field("default", description="ID de conversación")

class DocumentAnalysis(BaseModel):
    """Modelo para análisis de documentos."""
    content: str = Field(..., description="Contenido del documento")
    filename: str = Field(..., description="Nombre del archivo")
    extract_concepts: bool = Field(True, description="Extraer conceptos")
    detect_patterns: bool = Field(True, description="Detectar patrones")

class ChatResponse(BaseModel):
    """Modelo para respuestas de chat."""
    response: str
    concepts_used: List[Dict[str, Any]]
    patterns_detected: List[Dict[str, Any]]
    memory_retrieved: bool
    emergence_detected: bool
    processing_time: float
    traceability: Dict[str, Any]

# ===== SISTEMA DE PROCESAMIENTO DE CONVERSACIONES =====
class ConversationProcessor:
    """
    Procesador de conversaciones con extracción de conceptos y trazabilidad.
    
    Este procesador toma el JSON gordo de conversaciones y:
    1. Extrae conversaciones individuales
    2. Analiza y extrae conceptos con trazabilidad
    3. Crea resúmenes con valor
    4. Detecta patrones emergentes
    """
    
    def __init__(self, config: IANAEConfig):
        """
        Inicializa el procesador de conversaciones.
        
        Args:
            config: Configuración del sistema IANAE
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ConversationProcessor")
        self.processed_conversations = 0
        self.extracted_concepts = 0
        self.detected_patterns = 0
        
        # Patrones de extracción específicos para Lucas
        self.extraction_patterns = self._initialize_extraction_patterns()
        
        # Estadísticas de procesamiento
        self.processing_stats = {
            'start_time': None,
            'end_time': None,
            'conversations_processed': 0,
            'concepts_extracted': 0,
            'patterns_detected': 0,
            'errors_encountered': 0,
            'processing_rate': 0.0
        }
    
    def _initialize_extraction_patterns(self) -> Dict[ConceptCategory, List[str]]:
        """
        Inicializa patrones de extracción específicos para Lucas.
        
        Returns:
            Diccionario con patrones de extracción por categoría
        """
        patterns = {
            ConceptCategory.TECNOLOGIAS: [
                # OpenCV y Visión Artificial
                r'cv2\.\w+', r'findContours', r'HSV', r'mask', r'contour',
                r'imread', r'imshow', r'waitKey', r'threshold', r'morphology',
                
                # Python
                r'import \w+', r'from \w+ import', r'def \w+\(', r'class \w+:',
                'python', 'numpy', 'pandas', 'matplotlib', 'scipy',
                
                # VBA y Excel
                r'Application\.\w+', r'Worksheet\.\w+', r'Range\([^)]+\)',
                r'Cells\([^)]+\)', 'VBA', 'Excel', 'Macro', '.xlsm', '.xlsx',
                
                # Docker y Contenedores
                'docker', 'container', 'dockerfile', 'docker-compose',
                
                # Bases de Datos
                'sqlite', 'postgresql', 'mysql', 'database', 'query',
                
                # Web y APIs
                'fastapi', 'flask', 'requests', 'api', 'endpoint', 'json'
            ],
            
            ConceptCategory.PROYECTOS: [
                # Proyecto Tacógrafos
                'tacógrafo', 'tacografos', 'tacografo', 'tachograph',
                'círculo', 'circulo', 'circle detection', 'detección circular',
                
                # Proyecto VBA2Python
                'vba2python', 'vba to python', 'migration', 'conversion',
                
                # Proyecto Hollow Earth
                'hollow earth', 'tierra hueca', 'threejs', 'three.js',
                
                # Proyecto IANAE
                'ianae', 'bibliotecario', 'memory system', 'rag system',
                
                # Otros proyectos
                'automation', 'automatización', 'optimization', 'optimización'
            ],
            
            ConceptCategory.LUCAS_PERSONAL: [
                # Información personal
                'lucas', 'novelda', 'alicante', 'valencia', 'españa',
                
                # Hardware
                'i9-10900kf', 'rtx3060', 'rtx 3060', '128gb', 'ram',
                
                # Características cognitivas
                'toc', 'tdah', 'adhd', 'ocd', 'superpoder', 'patrón',
                'pattern recognition', 'detección de patrones',
                
                # Preferencias
                'automatizar', 'optimizar', 'eficiencia', 'productividad'
            ],
            
            ConceptCategory.CONCEPTOS_IANAE: [
                'pensamiento emergente', 'emergent thinking', 'conceptos difusos',
                'auto modificación', 'self modification', 'memoria semántica',
                'semantic memory', 'rag', 'retrieval augmented generation',
                'vector embeddings', 'similarity search'
            ],
            
            ConceptCategory.HERRAMIENTAS: [
                'lm studio', 'ollama', 'hugging face', 'transformers',
                'openai', 'chatgpt', 'claude', 'gemini', 'copilot',
                'vscode', 'visual studio', 'git', 'github', 'jupyter'
            ],
            
            ConceptCategory.VISION_ARTIFICIAL: [
                'computer vision', 'visión artificial', 'image processing',
                'object detection', 'feature extraction', 'machine learning',
                'deep learning', 'neural networks', 'cnn', 'opencv'
            ],
            
            ConceptCategory.AUTOMATIZACION: [
                'script', 'automation', 'batch processing', 'scheduled tasks',
                'cron', 'task scheduler', 'workflow', 'pipeline', 'etl'
            ]
        }
        
        return patterns
    
    def process_conversations_json(self, json_path: str) -> bool:
        """
        Procesa el JSON gordo de conversaciones.
        
        Args:
            json_path: Ruta al archivo JSON de conversaciones
            
        Returns:
            True si el procesamiento fue exitoso, False en caso contrario
        """
        self.logger.info(f"🚀 Iniciando procesamiento de conversaciones desde: {json_path}")
        self.processing_stats['start_time'] = time.time()
        
        try:
            # Verificar que el archivo existe
            if not os.path.exists(json_path):
                self.logger.error(f"❌ No se encontró el archivo: {json_path}")
                return False
            
            # Cargar JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                conversations_data = json.load(f)
            
            self.logger.info(f"📁 Cargado JSON con {len(conversations_data)} conversaciones")
            
            # Crear directorio de salida
            os.makedirs(self.config.output_conversations_path, exist_ok=True)
            
            # Procesar conversaciones en lotes
            total_conversations = len(conversations_data)
            processed = 0
            
            for i in range(0, total_conversations, self.config.processing_batch_size):
                batch = conversations_data[i:i + self.config.processing_batch_size]
                batch_results = self._process_conversation_batch(batch, i)
                
                processed += len(batch)
                progress = (processed / total_conversations) * 100
                
                self.logger.info(
                    f"📊 Progreso: {processed}/{total_conversations} "
                    f"({progress:.1f}%) - Conceptos extraídos: {self.extracted_concepts}"
                )
            
            # Finalizar estadísticas
            self._finalize_processing_stats()
            
            self.logger.info("✅ Procesamiento de conversaciones completado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en procesamiento: {str(e)}")
            self.processing_stats['errors_encountered'] += 1
            return False
    
    def _process_conversation_batch(self, batch: List[Dict], batch_start_index: int) -> List[ConversationSummary]:
        """
        Procesa un lote de conversaciones.
        
        Args:
            batch: Lote de conversaciones a procesar
            batch_start_index: Índice de inicio del lote
            
        Returns:
            Lista de resúmenes de conversaciones procesadas
        """
        batch_summaries = []
        
        for idx, conversation in enumerate(batch):
            try:
                conversation_id = f"conv_{batch_start_index + idx:05d}"
                summary = self._process_single_conversation(conversation, conversation_id)
                
                if summary:
                    batch_summaries.append(summary)
                    self.processed_conversations += 1
                
            except Exception as e:
                self.logger.error(f"❌ Error procesando conversación {batch_start_index + idx}: {str(e)}")
                self.processing_stats['errors_encountered'] += 1
                continue
        
        return batch_summaries
    
    def _process_single_conversation(self, conversation: Dict, conversation_id: str) -> Optional[ConversationSummary]:
        """
        Procesa una conversación individual.
        
        Args:
            conversation: Datos de la conversación
            conversation_id: ID único de la conversación
            
        Returns:
            Resumen de la conversación procesada o None si falló
        """
        start_time = time.time()
        
        try:
            # Extraer información básica
            title = conversation.get('title', f'Conversación {conversation_id}')
            messages = conversation.get('messages', [])
            
            if not messages:
                self.logger.warning(f"⚠️ Conversación {conversation_id} sin mensajes")
                return None
            
            # Procesar mensajes
            processed_messages = []
            all_text_content = []
            participants = set()
            
            for msg_idx, message in enumerate(messages):
                if not isinstance(message, dict):
                    continue
                
                message_id = f"{conversation_id}_msg_{msg_idx:03d}"
                sender = message.get('sender', 'unknown')
                text = message.get('text', '')
                
                if isinstance(text, str) and len(text.strip()) > 0:
                    processed_messages.append({
                        'id': message_id,
                        'sender': sender,
                        'text': text.strip(),
                        'timestamp': message.get('timestamp', '')
                    })
                    
                    all_text_content.append(text.strip())
                    participants.add(sender)
            
            if not processed_messages:
                self.logger.warning(f"⚠️ Conversación {conversation_id} sin mensajes válidos")
                return None
            
            # Extraer conceptos
            concepts = self._extract_concepts_from_conversation(
                processed_messages, conversation_id
            )
            
            # Crear resumen
            summary = self._create_conversation_summary(
                conversation_id, title, list(participants), 
                processed_messages, concepts, all_text_content
            )
            
            # Guardar conversación individual
            self._save_individual_conversation(conversation_id, {
                'id': conversation_id,
                'title': title,
                'messages': processed_messages,
                'summary': asdict(summary),
                'concepts': [asdict(c) for c in concepts]
            })
            
            # Actualizar estadísticas
            self.extracted_concepts += len(concepts)
            processing_time = time.time() - start_time
            
            if self.config.debug_mode:
                self.logger.debug(
                    f"✅ Procesada {conversation_id}: {len(concepts)} conceptos "
                    f"en {processing_time:.2f}s"
                )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando conversación {conversation_id}: {str(e)}")
            return None
    
    def _extract_concepts_from_conversation(self, messages: List[Dict], conversation_id: str) -> List[ConceptData]:
        """
        Extrae conceptos de una conversación.
        
        Args:
            messages: Lista de mensajes de la conversación
            conversation_id: ID de la conversación
            
        Returns:
            Lista de conceptos extraídos
        """
        concepts = []
        concept_counts = defaultdict(int)
        
        for message in messages:
            message_id = message['id']
            text = message['text']
            
            # Extraer conceptos usando patrones
            message_concepts = self._extract_concepts_from_text(
                text, conversation_id, message_id
            )
            
            # Contar ocurrencias
            for concept in message_concepts:
                concept_counts[concept.name] += 1
                concepts.append(concept)
        
        # Filtrar conceptos por fuerza mínima
        filtered_concepts = []
        for concept in concepts:
            if concept.strength >= self.config.min_concept_strength:
                # Actualizar conteo de ocurrencias
                concept.occurrences = concept_counts[concept.name]
                filtered_concepts.append(concept)
        
        # Limitar número de conceptos por conversación
        filtered_concepts.sort(key=lambda c: c.strength, reverse=True)
        return filtered_concepts[:self.config.max_concepts_per_conversation]
    
    def _extract_concepts_from_text(self, text: str, conversation_id: str, message_id: str) -> List[ConceptData]:
        """
        Extrae conceptos de un texto específico.
        
        Args:
            text: Texto a analizar
            conversation_id: ID de la conversación
            message_id: ID del mensaje
            
        Returns:
            Lista de conceptos extraídos del texto
        """
        concepts = []
        text_lower = text.lower()
        
        for category, patterns in self.extraction_patterns.items():
            for pattern in patterns:
                try:
                    if pattern.startswith('r'):
                        # Patrón regex
                        regex_pattern = pattern[1:]  # Remover 'r' inicial
                        matches = re.finditer(regex_pattern, text, re.IGNORECASE)
                        
                        for match in matches:
                            concept_text = match.group().strip()
                            if len(concept_text) > 2:
                                concept = self._create_concept_data(
                                    concept_text, category, text, match.start(),
                                    conversation_id, message_id, "regex"
                                )
                                concepts.append(concept)
                    else:
                        # Búsqueda simple
                        if pattern.lower() in text_lower:
                            concept = self._create_concept_data(
                                pattern, category, text, text_lower.find(pattern.lower()),
                                conversation_id, message_id, "simple_match"
                            )
                            concepts.append(concept)
                            
                except Exception as e:
                    if self.config.debug_mode:
                        self.logger.debug(f"⚠️ Error con patrón {pattern}: {str(e)}")
                    continue
        
        return concepts
    
    def _create_concept_data(self, name: str, category: ConceptCategory, 
                           context: str, position: int, conversation_id: str,
                           message_id: str, method: str) -> ConceptData:
        """
        Crea un objeto ConceptData con trazabilidad completa.
        
        Args:
            name: Nombre del concepto
            category: Categoría del concepto
            context: Contexto donde apareció
            position: Posición en el texto
            conversation_id: ID de la conversación
            message_id: ID del mensaje
            method: Método de extracción
            
        Returns:
            Objeto ConceptData completo
        """
        # Calcular fuerza del concepto
        strength = self._calculate_concept_strength(name, context, category)
        
        # Calcular confianza
        confidence = self._calculate_extraction_confidence(name, method, context)
        
        # Extraer snippet de contexto
        context_snippet = self._extract_context_snippet(context, position, name)
        
        return ConceptData(
            name=name.strip(),
            category=category,
            strength=strength,
            context=context_snippet,
            source_conversation=conversation_id,
            source_message_id=message_id,
            extraction_method=method,
            confidence=confidence,
            occurrences=1,  # Se actualizará después
            created_at=datetime.now(),
            metadata={
                'position': position,
                'context_length': len(context),
                'text_length': len(name),
                'extraction_timestamp': datetime.now().isoformat()
            }
        )
    
    def _calculate_concept_strength(self, name: str, context: str, category: ConceptCategory) -> float:
        """
        Calcula la fuerza de un concepto basado en varios factores.
        
        Args:
            name: Nombre del concepto
            context: Contexto donde apareció
            category: Categoría del concepto
            
        Returns:
            Fuerza del concepto (0.0-1.0)
        """
        strength = 0.5  # Fuerza base
        
        # Factor por longitud del nombre
        if len(name) > 3:
            strength += 0.1
        
        # Factor por categoría
        category_weights = {
            ConceptCategory.LUCAS_PERSONAL: 0.3,
            ConceptCategory.PROYECTOS: 0.2,
            ConceptCategory.TECNOLOGIAS: 0.15,
            ConceptCategory.CONCEPTOS_IANAE: 0.2,
            ConceptCategory.VISION_ARTIFICIAL: 0.15,
            ConceptCategory.AUTOMATIZACION: 0.1
        }
        
        strength += category_weights.get(category, 0.05)
        
        # Factor por frecuencia en contexto
        name_lower = name.lower()
        context_lower = context.lower()
        occurrences = context_lower.count(name_lower)
        strength += min(0.2, occurrences * 0.05)
        
        # Factor por posición (conceptos al inicio son más importantes)
        position = context_lower.find(name_lower)
        if position < len(context) * 0.2:  # Primer 20% del texto
            strength += 0.1
        
        return min(1.0, strength)
    
    def _calculate_extraction_confidence(self, name: str, method: str, context: str) -> float:
        """
        Calcula la confianza en la extracción de un concepto.
        
        Args:
            name: Nombre del concepto
            method: Método de extracción
            context: Contexto
            
        Returns:
            Confianza en la extracción (0.0-1.0)
        """
        confidence = 0.5  # Confianza base
        
        # Factor por método de extracción
        method_weights = {
            'regex': 0.3,
            'simple_match': 0.2,
            'nlp_extraction': 0.4,
            'pattern_matching': 0.25
        }
        
        confidence += method_weights.get(method, 0.1)
        
        # Factor por longitud del concepto
        if len(name) >= 5:
            confidence += 0.1
        
        # Factor por contexto
        if len(context) > 50:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _extract_context_snippet(self, context: str, position: int, concept: str) -> str:
        """
        Extrae un snippet de contexto alrededor del concepto.
        
        Args:
            context: Texto completo
            position: Posición del concepto
            concept: Concepto extraído
            
        Returns:
            Snippet de contexto
        """
        try:
            context_window = 50  # Caracteres antes y después
            start = max(0, position - context_window)
            end = min(len(context), position + len(concept) + context_window)
            
            snippet = context[start:end].strip()
            
            # Marcar el concepto en el snippet
            if concept.lower() in snippet.lower():
                # Encontrar posición exacta en el snippet
                snippet_lower = snippet.lower()
                concept_lower = concept.lower()
                snippet_pos = snippet_lower.find(concept_lower)
                
                if snippet_pos != -1:
                    # Marcar el concepto
                    before = snippet[:snippet_pos]
                    marked_concept = f"**{snippet[snippet_pos:snippet_pos + len(concept)]}**"
                    after = snippet[snippet_pos + len(concept):]
                    snippet = before + marked_concept + after
            
            return snippet
            
        except Exception as e:
            self.logger.debug(f"⚠️ Error extrayendo snippet: {str(e)}")
            return context[:100] + "..." if len(context) > 100 else context
    
    def _create_conversation_summary(self, conversation_id: str, title: str, 
                                   participants: List[str], messages: List[Dict],
                                   concepts: List[ConceptData], 
                                   all_text: List[str]) -> ConversationSummary:
        """
        Crea un resumen completo de la conversación.
        
        Args:
            conversation_id: ID de la conversación
            title: Título de la conversación
            participants: Lista de participantes
            messages: Lista de mensajes
            concepts: Lista de conceptos extraídos
            all_text: Todo el texto de la conversación
            
        Returns:
            Resumen completo de la conversación
        """
        # Calcular temas principales
        key_topics = self._identify_key_topics(concepts)
        
        # Crear resumen textual
        summary_text = self._generate_text_summary(all_text, concepts)
        
        # Calcular puntuación de valor
        value_score = self._calculate_conversation_value(concepts, messages, all_text)
        
        # Detectar patrones
        patterns = self._detect_conversation_patterns(concepts, messages)
        
        return ConversationSummary(
            conversation_id=conversation_id,
            title=title,
            participants=participants,
            message_count=len(messages),
            concepts_extracted=len(concepts),
            key_topics=key_topics,
            summary_text=summary_text,
            value_score=value_score,
            patterns_detected=patterns,
            processing_time=0.0,  # Se calculará después
            created_at=datetime.now(),
            metadata={
                'total_characters': sum(len(text) for text in all_text),
                'unique_concepts': len(set(c.name for c in concepts)),
                'concept_categories': list(set(c.category.value for c in concepts)),
                'highest_strength_concept': max(concepts, key=lambda c: c.strength).name if concepts else None
            }
        )
    
    def _identify_key_topics(self, concepts: List[ConceptData]) -> List[str]:
        """
        Identifica los temas principales de una conversación.
        
        Args:
            concepts: Lista de conceptos extraídos
            
        Returns:
            Lista de temas principales
        """
        if not concepts:
            return []
        
        # Agrupar conceptos por categoría
        category_groups = defaultdict(list)
        for concept in concepts:
            category_groups[concept.category.value].append(concept)
        
        # Identificar temas principales por fuerza
        key_topics = []
        
        for category, category_concepts in category_groups.items():
            if len(category_concepts) >= 2:  # Al menos 2 conceptos de la categoría
                # Obtener el concepto más fuerte de la categoría
                strongest = max(category_concepts, key=lambda c: c.strength)
                key_topics.append(f"{category}: {strongest.name}")
        
        # Ordenar por fuerza total de la categoría
        category_strengths = {
            category: sum(c.strength for c in concepts)
            for category, concepts in category_groups.items()
        }
        
        key_topics.sort(key=lambda topic: category_strengths.get(topic.split(':')[0], 0), reverse=True)
        
        return key_topics[:5]  # Top 5 temas
    
    def _generate_text_summary(self, all_text: List[str], concepts: List[ConceptData]) -> str:
        """
        Genera un resumen textual de la conversación.
        
        Args:
            all_text: Todo el texto de la conversación
            concepts: Conceptos extraídos
            
        Returns:
            Resumen textual
        """
        if not concepts:
            return "Conversación sin conceptos técnicos identificados."
        
        # Obtener conceptos más relevantes
        top_concepts = sorted(concepts, key=lambda c: c.strength, reverse=True)[:5]
        
        # Agrupar por categoría
        categories = defaultdict(list)
        for concept in top_concepts:
            categories[concept.category.value].append(concept.name)
        
        # Construir resumen
        summary_parts = []
        
        if ConceptCategory.LUCAS_PERSONAL.value in categories:
            personal_concepts = categories[ConceptCategory.LUCAS_PERSONAL.value]
            summary_parts.append(f"Aspectos personales de Lucas: {', '.join(personal_concepts)}")
        
        if ConceptCategory.PROYECTOS.value in categories:
            project_concepts = categories[ConceptCategory.PROYECTOS.value]
            summary_parts.append(f"Proyectos discutidos: {', '.join(project_concepts)}")
        
        if ConceptCategory.TECNOLOGIAS.value in categories:
            tech_concepts = categories[ConceptCategory.TECNOLOGIAS.value]
            summary_parts.append(f"Tecnologías mencionadas: {', '.join(tech_concepts)}")
        
        if ConceptCategory.VISION_ARTIFICIAL.value in categories:
            vision_concepts = categories[ConceptCategory.VISION_ARTIFICIAL.value]
            summary_parts.append(f"Visión artificial: {', '.join(vision_concepts)}")
        
        if ConceptCategory.AUTOMATIZACION.value in categories:
            auto_concepts = categories[ConceptCategory.AUTOMATIZACION.value]
            summary_parts.append(f"Automatización: {', '.join(auto_concepts)}")
        
        # Calcular estadísticas básicas
        total_chars = sum(len(text) for text in all_text)
        avg_message_length = total_chars / len(all_text) if all_text else 0
        
        summary = f"Conversación de {len(all_text)} mensajes ({total_chars} caracteres). "
        summary += " | ".join(summary_parts)
        
        if avg_message_length > 100:
            summary += " | Mensajes detallados con contenido técnico."
        
        return summary
    
    def _calculate_conversation_value(self, concepts: List[ConceptData], 
                                    messages: List[Dict], all_text: List[str]) -> float:
        """
        Calcula una puntuación de valor para la conversación.
        
        Args:
            concepts: Conceptos extraídos
            messages: Mensajes de la conversación
            all_text: Todo el texto
            
        Returns:
            Puntuación de valor (0.0-1.0)
        """
        if not concepts:
            return 0.1
        
        value_score = 0.0
        
        # Factor por número de conceptos
        concept_factor = min(1.0, len(concepts) / 10.0)
        value_score += concept_factor * 0.3
        
        # Factor por fuerza promedio de conceptos
        avg_strength = sum(c.strength for c in concepts) / len(concepts)
        value_score += avg_strength * 0.3
        
        # Factor por diversidad de categorías
        unique_categories = len(set(c.category for c in concepts))
        category_factor = min(1.0, unique_categories / 5.0)
        value_score += category_factor * 0.2
        
        # Factor por longitud de la conversación
        total_chars = sum(len(text) for text in all_text)
        length_factor = min(1.0, total_chars / 5000.0)  # Conversaciones largas son más valiosas
        value_score += length_factor * 0.1
        
        # Factor por conceptos de alta prioridad (Lucas personal, proyectos)
        high_priority_concepts = [
            c for c in concepts 
            if c.category in [ConceptCategory.LUCAS_PERSONAL, ConceptCategory.PROYECTOS]
        ]
        priority_factor = min(1.0, len(high_priority_concepts) / 3.0)
        value_score += priority_factor * 0.1
        
        return min(1.0, value_score)
    
    def _detect_conversation_patterns(self, concepts: List[ConceptData], 
                                    messages: List[Dict]) -> List[str]:
        """
        Detecta patrones en la conversación.
        
        Args:
            concepts: Conceptos extraídos
            messages: Mensajes de la conversación
            
        Returns:
            Lista de patrones detectados
        """
        patterns = []
        
        if not concepts:
            return patterns
        
        # Patrón: Concentración de conceptos técnicos
        tech_concepts = [c for c in concepts if c.category == ConceptCategory.TECNOLOGIAS]
        if len(tech_concepts) >= 3:
            patterns.append("concentracion_tecnologica")
        
        # Patrón: Discusión de proyectos
        project_concepts = [c for c in concepts if c.category == ConceptCategory.PROYECTOS]
        if len(project_concepts) >= 2:
            patterns.append("discusion_proyectos")
        
        # Patrón: Automatización
        auto_concepts = [c for c in concepts if c.category == ConceptCategory.AUTOMATIZACION]
        if len(auto_concepts) >= 1:
            patterns.append("enfoque_automatizacion")
        
        # Patrón: Visión artificial
        vision_concepts = [c for c in concepts if c.category == ConceptCategory.VISION_ARTIFICIAL]
        if len(vision_concepts) >= 2:
            patterns.append("trabajo_vision_artificial")
        
        # Patrón: Información personal de Lucas
        personal_concepts = [c for c in concepts if c.category == ConceptCategory.LUCAS_PERSONAL]
        if len(personal_concepts) >= 1:
            patterns.append("contenido_personal")
        
        # Patrón: Conversación técnica profunda
        high_strength_concepts = [c for c in concepts if c.strength > 0.7]
        if len(high_strength_concepts) >= 3:
            patterns.append("conversacion_tecnica_profunda")
        
        # Patrón: Múltiples categorías (conversación diversa)
        unique_categories = len(set(c.category for c in concepts))
        if unique_categories >= 4:
            patterns.append("conversacion_diversa")
        
        return patterns
    
    def _save_individual_conversation(self, conversation_id: str, conversation_data: Dict) -> None:
        """
        Guarda una conversación individual en archivo JSON.
        
        Args:
            conversation_id: ID de la conversación
            conversation_data: Datos de la conversación
        """
        try:
            filename = f"{conversation_id}.json"
            filepath = os.path.join(self.config.output_conversations_path, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando conversación {conversation_id}: {str(e)}")
    
    def _finalize_processing_stats(self) -> None:
        """Finaliza las estadísticas de procesamiento."""
        self.processing_stats['end_time'] = time.time()
        self.processing_stats['conversations_processed'] = self.processed_conversations
        self.processing_stats['concepts_extracted'] = self.extracted_concepts
        
        processing_time = self.processing_stats['end_time'] - self.processing_stats['start_time']
        self.processing_stats['processing_rate'] = self.processed_conversations / processing_time if processing_time > 0 else 0
        
        self.logger.info("📊 ESTADÍSTICAS FINALES DE PROCESAMIENTO:")
        self.logger.info(f"   ⏱️ Tiempo total: {processing_time:.2f} segundos")
        self.logger.info(f"   💬 Conversaciones procesadas: {self.processed_conversations}")
        self.logger.info(f"   🧠 Conceptos extraídos: {self.extracted_concepts}")
        self.logger.info(f"   🔄 Tasa de procesamiento: {self.processing_stats['processing_rate']:.2f} conv/seg")
        self.logger.info(f"   ❌ Errores encontrados: {self.processing_stats['errors_encountered']}")

# ===== SISTEMA DE BASE DE DATOS CON TRAZABILIDAD =====
class IANAEDatabase:
    """
    Sistema de base de datos con trazabilidad completa para IANAE 3.0.
    
    Gestiona el almacenamiento y recuperación de:
    - Conceptos con trazabilidad completa
    - Conversaciones procesadas
    - Patrones emergentes
    - Relaciones entre conceptos
    """
    
    def __init__(self, db_path: str):
        """
        Inicializa la base de datos.
        
        Args:
            db_path: Ruta de la base de datos SQLite
        """
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.IANAEDatabase")
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Inicializa las tablas de la base de datos."""
        self.logger.info(f"🗄️ Inicializando base de datos: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Tabla de conceptos con trazabilidad completa
            conn.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT,
                    source_conversation TEXT NOT NULL,
                    source_message_id TEXT NOT NULL,
                    extraction_method TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurrences INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    UNIQUE(name, source_conversation, source_message_id)
                )
            ''')
            
            # Tabla de conversaciones procesadas
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    participants TEXT,
                    message_count INTEGER NOT NULL,
                    concepts_extracted INTEGER NOT NULL,
                    key_topics TEXT,
                    summary_text TEXT,
                    value_score REAL NOT NULL,
                    patterns_detected TEXT,
                    processing_time REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Tabla de relaciones entre conceptos
            conn.execute('''
                CREATE TABLE IF NOT EXISTS concept_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept_a TEXT NOT NULL,
                    concept_b TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT,
                    discovery_method TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    UNIQUE(concept_a, concept_b, relationship_type)
                )
            ''')
            
            # Tabla de patrones emergentes
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emergence_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    concepts_involved TEXT NOT NULL,
                    strength REAL NOT NULL,
                    discovery_method TEXT NOT NULL,
                    context TEXT,
                    significance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Tabla de estadísticas de procesamiento
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processing_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    conversations_processed INTEGER NOT NULL,
                    concepts_extracted INTEGER NOT NULL,
                    patterns_detected INTEGER NOT NULL,
                    processing_rate REAL,
                    errors_encountered INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Índices para optimizar consultas
            self._create_database_indexes(conn)
        
        self.logger.info("✅ Base de datos inicializada correctamente")
    
    def _create_database_indexes(self, conn: sqlite3.Connection) -> None:
        """
        Crea índices para optimizar consultas.
        
        Args:
            conn: Conexión a la base de datos
        """
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_category ON concepts(category)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_strength ON concepts(strength DESC)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_source ON concepts(source_conversation)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_id ON conversations(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_value ON conversations(value_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_concepts ON concept_relationships(concept_a, concept_b)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_strength ON concept_relationships(strength DESC)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_type ON emergence_patterns(pattern_type)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_strength ON emergence_patterns(strength DESC)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def save_concepts(self, concepts: List[ConceptData]) -> int:
        """
        Guarda conceptos en la base de datos.
        
        Args:
            concepts: Lista de conceptos a guardar
            
        Returns:
            Número de conceptos guardados exitosamente
        """
        if not concepts:
            return 0
        
        saved_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for concept in concepts:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO concepts (
                            name, category, strength, context, source_conversation,
                            source_message_id, extraction_method, confidence,
                            occurrences, created_at, updated_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        concept.name,
                        concept.category.value,
                        concept.strength,
                        concept.context,
                        concept.source_conversation,
                        concept.source_message_id,
                        concept.extraction_method,
                        concept.confidence,
                        concept.occurrences,
                        concept.created_at.isoformat(),
                        datetime.now().isoformat(),
                        json.dumps(concept.metadata)
                    ))
                    saved_count += 1
                    
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed" in str(e):
                        # Actualizar concepto existente
                        conn.execute('''
                            UPDATE concepts SET
                                strength = MAX(strength, ?),
                                occurrences = occurrences + ?,
                                updated_at = ?
                            WHERE name = ? AND source_conversation = ? AND source_message_id = ?
                        ''', (
                            concept.strength,
                            concept.occurrences,
                            datetime.now().isoformat(),
                            concept.name,
                            concept.source_conversation,
                            concept.source_message_id
                        ))
                    else:
                        self.logger.error(f"❌ Error guardando concepto {concept.name}: {str(e)}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error inesperado guardando concepto {concept.name}: {str(e)}")
        
        self.logger.info(f"💾 Guardados {saved_count} conceptos en la base de datos")
        return saved_count
    
    def save_conversations(self, conversations: List[ConversationSummary]) -> int:
        """
        Guarda resúmenes de conversaciones en la base de datos.
        
        Args:
            conversations: Lista de resúmenes de conversaciones
            
        Returns:
            Número de conversaciones guardadas exitosamente
        """
        if not conversations:
            return 0
        
        saved_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for conv in conversations:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO conversations (
                            conversation_id, title, participants, message_count,
                            concepts_extracted, key_topics, summary_text,
                            value_score, patterns_detected, processing_time,
                            created_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        conv.conversation_id,
                        conv.title,
                        json.dumps(conv.participants),
                        conv.message_count,
                        conv.concepts_extracted,
                        json.dumps(conv.key_topics),
                        conv.summary_text,
                        conv.value_score,
                        json.dumps(conv.patterns_detected),
                        conv.processing_time,
                        conv.created_at.isoformat(),
                        json.dumps(conv.metadata)
                    ))
                    saved_count += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Error guardando conversación {conv.conversation_id}: {str(e)}")
        
        self.logger.info(f"💾 Guardadas {saved_count} conversaciones en la base de datos")
        return saved_count
    
    def search_concepts(self, query: str, limit: int = 10, 
                       category_filter: Optional[str] = None,
                       min_strength: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca conceptos en la base de datos.
        
        Args:
            query: Término de búsqueda
            limit: Límite de resultados
            category_filter: Filtro opcional por categoría
            min_strength: Fuerza mínima de conceptos
            
        Returns:
            Lista de conceptos encontrados
        """
        keywords = self._extract_search_keywords(query)
        concepts = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for keyword in keywords[:3]:  # Top 3 keywords
                # Construir consulta SQL
                sql = '''
                    SELECT name, category, strength, context, source_conversation,
                           source_message_id, extraction_method, confidence,
                           occurrences, created_at, updated_at, metadata
                    FROM concepts
                    WHERE (name LIKE ? OR context LIKE ?)
                    AND strength >= ?
                '''
                params = [f'%{keyword}%', f'%{keyword}%', min_strength]
                
                if category_filter:
                    sql += ' AND category = ?'
                    params.append(category_filter)
                
                sql += ' ORDER BY strength DESC, occurrences DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(sql, params)
                
                for row in cursor.fetchall():
                    concept_dict = dict(row)
                    concept_dict['metadata'] = json.loads(concept_dict['metadata'] or '{}')
                    concepts.append(concept_dict)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_concepts = []
        for concept in concepts:
            key = (concept['name'], concept['source_conversation'])
            if key not in seen:
                seen.add(key)
                unique_concepts.append(concept)
        
        return unique_concepts[:limit]
    
    def _extract_search_keywords(self, query: str) -> List[str]:
        """
        Extrae palabras clave de una consulta de búsqueda.
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            Lista de palabras clave
        """
        # Normalizar query
        query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
        words = query_clean.split()
        
        # Filtrar palabras muy cortas y palabras comunes
        stop_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te',
            'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los',
            'las', 'como', 'mas', 'pero', 'sus', 'está', 'esta', 'todo', 'tiene',
            'hacer', 'puede', 'donde', 'cuando', 'muy', 'sin', 'sobre', 'hasta'
        }
        
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords[:5]  # Máximo 5 keywords
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de las conversaciones procesadas.
        
        Returns:
            Diccionario con estadísticas
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Estadísticas básicas
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM concepts")
            total_concepts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT name) FROM concepts")
            unique_concepts = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(value_score) FROM conversations")
            avg_value_score = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT AVG(concepts_extracted) FROM conversations")
            avg_concepts_per_conv = cursor.fetchone()[0] or 0.0
            
            # Estadísticas por categoría
            cursor.execute('''
                SELECT category, COUNT(*) as count, AVG(strength) as avg_strength
                FROM concepts
                GROUP BY category
                ORDER BY count DESC
            ''')
            category_stats = [
                {
                    'category': row[0],
                    'count': row[1],
                    'avg_strength': row[2]
                }
                for row in cursor.fetchall()
            ]
            
            # Top conceptos por fuerza
            cursor.execute('''
                SELECT name, category, strength, occurrences
                FROM concepts
                ORDER BY strength DESC
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
            
            # Conversaciones más valiosas
            cursor.execute('''
                SELECT conversation_id, title, value_score, concepts_extracted
                FROM conversations
                ORDER BY value_score DESC
                LIMIT 5
            ''')
            top_conversations = [
                {
                    'id': row[0],
                    'title': row[1],
                    'value_score': row[2],
                    'concepts_extracted': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            return {
                'total_conversations': total_conversations,
                'total_concepts': total_concepts,
                'unique_concepts': unique_concepts,
                'avg_value_score': round(avg_value_score, 3),
                'avg_concepts_per_conversation': round(avg_concepts_per_conv, 1),
                'category_stats': category_stats,
                'top_concepts': top_concepts,
                'top_conversations': top_conversations,
                'last_updated': datetime.now().isoformat()
            }

# ===== APLICACIÓN FASTAPI =====
app = FastAPI(
    title="IANAE 3.0 - Sistema Completo con Trazabilidad",
    description="Bibliotecario Personal con Procesamiento de Conversaciones y Trazabilidad Completa",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
conversation_processor: Optional[ConversationProcessor] = None
database: Optional[IANAEDatabase] = None

@app.on_event("startup")
async def startup_event():
    """Inicialización del sistema IANAE 3.0."""
    global conversation_processor, database
    
    logger.info("🚀 Iniciando IANAE 3.0 - Sistema Completo con Trazabilidad")
    
    # Inicializar base de datos
    database = IANAEDatabase(CONFIG.db_path)
    
    # Inicializar procesador de conversaciones
    conversation_processor = ConversationProcessor(CONFIG)
    
    logger.info("✅ IANAE 3.0 inicializado correctamente")

@app.get("/", response_class=HTMLResponse)
async def get_main_interface():
    """Interfaz web principal de IANAE 3.0."""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IANAE 3.0 - Sistema Completo</title>
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
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
                margin-bottom: 1rem;
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
                backdrop-filter: blur(10px);
            }
            .section h2 {
                color: #667eea;
                margin-bottom: 1.5rem;
                font-size: 1.8rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
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
            .button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            .input-group {
                margin-bottom: 1rem;
            }
            .input-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 600;
                color: #555;
            }
            .input-group input {
                width: 100%;
                padding: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s ease;
            }
            .input-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                margin: 1rem 0;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.3s ease;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            .stat-label {
                font-size: 0.9rem;
                color: #666;
                margin-top: 0.5rem;
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
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .hidden { display: none; }
            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 IANAE 3.0 ⚡</h1>
            <p>Sistema Completo con Procesamiento de Conversaciones y Trazabilidad</p>
            
            <div class="status-bar">
                <div class="status-item">
                    <span id="statusIndicator">🔴 Inicializando...</span>
                </div>
                <div class="status-item">
                    <span id="dbStatus">📊 BD: Conectando...</span>
                </div>
                <div class="status-item">
                    <span id="processingStatus">⚙️ Procesador: Listo</span>
                </div>
            </div>
        </div>

        <div class="main-container">
            <!-- Sección de Procesamiento -->
            <div class="section processing-section">
                <h2>🔄 Procesamiento de Conversaciones</h2>
                
                <div class="input-group">
                    <label for="conversationsFile">Archivo JSON de Conversaciones:</label>
                    <input type="file" id="conversationsFile" accept=".json" />
                </div>
                
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <button class="button" id="processBtn" onclick="startProcessing()">
                        🚀 Procesar Conversaciones
                    </button>
                    <button class="button" id="statsBtn" onclick="loadStats()">
                        📊 Ver Estadísticas
                    </button>
                    <button class="button" id="exportBtn" onclick="exportData()">
                        💾 Exportar Datos
                    </button>
                </div>
                
                <div class="progress-bar" id="progressContainer" style="display: none;">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                
                <div class="log-area" id="logArea">
                    [Sistema IANAE 3.0 - Listo para procesar conversaciones]
                    > Sube un archivo JSON con conversaciones para comenzar
                    > El sistema extraerá conceptos con trazabilidad completa
                    > Se crearán resúmenes y se detectarán patrones
                </div>
            </div>

            <!-- Sección de Estadísticas -->
            <div class="section">
                <h2>📊 Estadísticas del Sistema</h2>
                
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
                        <div class="stat-value" id="avgValue">0.0</div>
                        <div class="stat-label">Valor Promedio</div>
                    </div>
                </div>
                
                <div style="margin-top: 2rem;">
                    <h3>🏆 Top Conceptos</h3>
                    <div id="topConcepts">Cargando estadísticas...</div>
                </div>
            </div>

            <!-- Sección de Chat -->
            <div class="section">
                <h2>💬 Chat con IANAE</h2>
                
                <div class="chat-interface">
                    <div class="messages-area" id="messagesArea">
                        <div class="message bot-message">
                            <strong>🤖 IANAE 3.0:</strong><br>
                            ¡Hola Lucas! 🚀 Soy tu IANAE 3.0 completamente renovado.<br><br>
                            ✨ Procesamiento completo de conversaciones<br>
                            🔍 Extracción de conceptos con trazabilidad<br>
                            🧠 Detección de patrones emergentes<br>
                            📊 Análisis de valor y resúmenes automáticos<br><br>
                            Procesa tus conversaciones primero y luego pregúntame lo que quieras.
                        </div>
                    </div>
                    
                    <div class="input-section">
                        <input type="text" id="chatInput" placeholder="Pregúntame sobre tus conversaciones procesadas..." 
                               onkeypress="handleChatKeyPress(event)" />
                        <button class="button" onclick="sendChatMessage()">
                            🚀 Enviar
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Variables globales
            let processingActive = false;
            let systemStats = null;

            // Inicialización
            document.addEventListener('DOMContentLoaded', function() {
                updateStatus();
                loadStats();
            });

            // Actualizar estado del sistema
            async function updateStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    document.getElementById('statusIndicator').innerHTML = 
                        data.status === 'ready' ? '🟢 Sistema Listo' : '🟡 Inicializando...';
                    
                    document.getElementById('dbStatus').innerHTML = 
                        `📊 BD: ${data.database_status || 'Conectada'}`;
                        
                } catch (error) {
                    document.getElementById('statusIndicator').innerHTML = '🔴 Error de Conexión';
                    console.error('Error updating status:', error);
                }
            }

            // Iniciar procesamiento de conversaciones
            async function startProcessing() {
                const fileInput = document.getElementById('conversationsFile');
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('Por favor selecciona un archivo JSON de conversaciones');
                    return;
                }
                
                if (processingActive) {
                    alert('Ya hay un procesamiento en curso');
                    return;
                }
                
                processingActive = true;
                const processBtn = document.getElementById('processBtn');
                const progressContainer = document.getElementById('progressContainer');
                const logArea = document.getElementById('logArea');
                
                // UI updates
                processBtn.disabled = true;
                processBtn.innerHTML = '<div class="loading"></div> Procesando...';
                progressContainer.style.display = 'block';
                
                // Clear log
                logArea.innerHTML = '[🚀 Iniciando procesamiento de conversaciones...]\\n';
                
                try {
                    const formData = new FormData();
                    formData.append('conversations_file', file);
                    
                    const response = await fetch('/process-conversations', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    // Read the response as a stream for real-time updates
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\\n');
                        
                        for (const line of lines) {
                            if (line.trim()) {
                                try {
                                    const data = JSON.parse(line);
                                    updateProcessingProgress(data);
                                } catch (e) {
                                    // Not JSON, probably a log message
                                    appendLog(line);
                                }
                            }
                        }
                    }
                    
                    appendLog('[✅ Procesamiento completado exitosamente!]');
                    loadStats(); // Reload stats after processing
                    
                } catch (error) {
                    appendLog(`[❌ Error en procesamiento: ${error.message}]`);
                    console.error('Processing error:', error);
                } finally {
                    processingActive = false;
                    processBtn.disabled = false;
                    processBtn.innerHTML = '🚀 Procesar Conversaciones';
                    progressContainer.style.display = 'none';
                }
            }

            // Actualizar progreso de procesamiento
            function updateProcessingProgress(data) {
                const progressFill = document.getElementById('progressFill');
                const logArea = document.getElementById('logArea');
                
                if (data.progress !== undefined) {
                    progressFill.style.width = `${data.progress}%`;
                }
                
                if (data.message) {
                    appendLog(`[${new Date().toLocaleTimeString()}] ${data.message}`);
                }
                
                if (data.stats) {
                    const stats = data.stats;
                    appendLog(`📊 Procesadas: ${stats.conversations_processed} | Conceptos: ${stats.concepts_extracted}`);
                }
            }

            // Añadir línea al log
            function appendLog(message) {
                const logArea = document.getElementById('logArea');
                logArea.innerHTML += message + '\\n';
                logArea.scrollTop = logArea.scrollHeight;
            }

            // Cargar estadísticas del sistema
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const stats = await response.json();
                    systemStats = stats;
                    
                    // Actualizar UI con estadísticas
                    document.getElementById('totalConversations').textContent = stats.total_conversations || 0;
                    document.getElementById('totalConcepts').textContent = stats.total_concepts || 0;
                    document.getElementById('uniqueConcepts').textContent = stats.unique_concepts || 0;
                    document.getElementById('avgValue').textContent = (stats.avg_value_score || 0).toFixed(2);
                    
                    // Mostrar top conceptos
                    const topConceptsDiv = document.getElementById('topConcepts');
                    if (stats.top_concepts && stats.top_concepts.length > 0) {
                        topConceptsDiv.innerHTML = stats.top_concepts.slice(0, 5).map((concept, index) => 
                            `<div style="margin: 0.5rem 0; padding: 0.5rem; background: #f0f0f0; border-radius: 4px;">
                                ${index + 1}. <strong>${concept.name}</strong> (${concept.category}) - 
                                Fuerza: ${concept.strength.toFixed(3)} | Apariciones: ${concept.occurrences}
                            </div>`
                        ).join('');
                    } else {
                        topConceptsDiv.innerHTML = '<p>No hay conceptos procesados aún.</p>';
                    }
                    
                } catch (error) {
                    console.error('Error loading stats:', error);
                    document.getElementById('topConcepts').innerHTML = '<p>Error cargando estadísticas.</p>';
                }
            }

            // Enviar mensaje de chat
            async function sendChatMessage() {
                const input = document.getElementById('chatInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                const messagesArea = document.getElementById('messagesArea');
                
                // Añadir mensaje del usuario
                addChatMessage(message, 'user');
                input.value = '';
                
                // Añadir indicador de que IANAE está pensando
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'message bot-message';
                thinkingDiv.innerHTML = '<div class="loading"></div> IANAE está analizando tu consulta...';
                messagesArea.appendChild(thinkingDiv);
                messagesArea.scrollTop = messagesArea.scrollHeight;
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            query: message,
                            use_memory: true,
                            use_emergence: true
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Remover indicador de pensamiento
                    messagesArea.removeChild(thinkingDiv);
                    
                    if (response.ok) {
                        addChatMessage(data.response, 'bot');
                        
                        // Mostrar información adicional si está disponible
                        if (data.concepts_used && data.concepts_used.length > 0) {
                            const conceptsInfo = `📊 Conceptos utilizados: ${data.concepts_used.slice(0,3).map(c => c.name).join(', ')}`;
                            addChatMessage(conceptsInfo, 'bot', true);
                        }
                        
                        if (data.patterns_detected && data.patterns_detected.length > 0) {
                            const patternsInfo = `🔍 Patrones detectados: ${data.patterns_detected.length}`;
                            addChatMessage(patternsInfo, 'bot', true);
                        }
                        
                        if (data.traceability && Object.keys(data.traceability).length > 0) {
                            const traceInfo = `🔗 Trazabilidad: ${data.traceability.source_conversations || 0} conversaciones consultadas`;
                            addChatMessage(traceInfo, 'bot', true);
                        }
                    } else {
                        addChatMessage('❌ Error procesando tu consulta: ' + data.detail, 'bot');
                    }
                    
                } catch (error) {
                    messagesArea.removeChild(thinkingDiv);
                    addChatMessage('❌ Error de conexión con el servidor', 'bot');
                    console.error('Chat error:', error);
                }
            }

            // Añadir mensaje al chat
            function addChatMessage(content, sender, isInfo = false) {
                const messagesArea = document.getElementById('messagesArea');
                const div = document.createElement('div');
                div.className = `message ${sender}-message`;
                
                if (isInfo) {
                    div.style.opacity = '0.7';
                    div.style.fontSize = '0.9em';
                }
                
                const senderName = sender === 'user' ? '👤 Lucas' : '🤖 IANAE 3.0';
                div.innerHTML = `<strong>${senderName}:</strong><br>${content.replace(/\\n/g, '<br>')}`;
                
                messagesArea.appendChild(div);
                messagesArea.scrollTop = messagesArea.scrollHeight;
            }

            // Manejar Enter en el chat
            function handleChatKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendChatMessage();
                }
            }

            // Exportar datos
            async function exportData() {
                try {
                    const response = await fetch('/export-data');
                    const blob = await response.blob();
                    
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `ianae_export_${new Date().toISOString().split('T')[0]}.json`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    appendLog('[💾 Datos exportados exitosamente]');
                    
                } catch (error) {
                    appendLog(`[❌ Error exportando datos: ${error.message}]`);
                    console.error('Export error:', error);
                }
            }

            // Actualizar estado cada 30 segundos
            setInterval(updateStatus, 30000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/process-conversations")
async def process_conversations_endpoint(background_tasks: BackgroundTasks):
    """
    Endpoint para procesar conversaciones desde archivo JSON.
    
    Returns:
        Stream de actualizaciones de progreso en tiempo real
    """
    global conversation_processor, database
    
    if not conversation_processor or not database:
        raise HTTPException(status_code=500, detail="Sistema no inicializado")
    
    # TODO: Implementar carga de archivo desde request
    # Por ahora usar archivo configurado
    json_path = CONFIG.conversations_json_path
    
    logger.info(f"🔄 Iniciando procesamiento de conversaciones desde: {json_path}")
    
    try:
        # Procesar conversaciones
        success = conversation_processor.process_conversations_json(json_path)
        
        if success:
            return {"status": "success", "message": "Conversaciones procesadas exitosamente"}
        else:
            raise HTTPException(status_code=500, detail="Error procesando conversaciones")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint de procesamiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """
    Endpoint principal de chat con IANAE 3.0.
    
    Args:
        message: Mensaje de chat del usuario
        
    Returns:
        Respuesta de IANAE con trazabilidad completa
    """
    global database
    
    if not database:
        raise HTTPException(status_code=500, detail="Base de datos no inicializada")
    
    start_time = time.time()
    
    try:
        concepts_used = []
        patterns_detected = []
        memory_retrieved = False
        emergence_detected = False
        traceability = {}
        
        # Buscar conceptos relevantes si se solicita memoria
        if message.use_memory:
            concepts_used = database.search_concepts(
                message.query, 
                limit=10, 
                min_strength=CONFIG.min_concept_strength
            )
            memory_retrieved = len(concepts_used) > 0
            
            if memory_retrieved:
                # Construir información de trazabilidad
                traceability = {
                    'source_conversations': len(set(c['source_conversation'] for c in concepts_used)),
                    'source_messages': len(set(c['source_message_id'] for c in concepts_used)),
                    'extraction_methods': list(set(c['extraction_method'] for c in concepts_used)),
                    'concept_categories': list(set(c['category'] for c in concepts_used))
                }
        
        # Detectar patrones emergentes si se solicita
        if message.use_emergence and concepts_used:
            # TODO: Implementar detección de patrones emergentes
            patterns_detected = []
            emergence_detected = len(patterns_detected) > 0
        
        # Construir respuesta (aquí se integraría con LLM real)
        response = await _generate_ianae_response(
            message.query, concepts_used, patterns_detected, traceability
        )
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=response,
            concepts_used=concepts_used,
            patterns_detected=patterns_detected,
            memory_retrieved=memory_retrieved,
            emergence_detected=emergence_detected,
            processing_time=processing_time,
            traceability=traceability
        )
        
    except Exception as e:
        logger.error(f"❌ Error en chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _generate_ianae_response(query: str, concepts: List[Dict], 
                                 patterns: List[Dict], traceability: Dict) -> str:
    """
    Genera respuesta de IANAE basada en conceptos y patrones.
    
    Args:
        query: Consulta del usuario
        concepts: Conceptos encontrados
        patterns: Patrones detectados
        traceability: Información de trazabilidad
        
    Returns:
        Respuesta generada de IANAE
    """
    if not concepts:
        return f"""🤖 He analizado tu consulta "{query}" pero no encontré conceptos específicos en tu memoria procesada.

Para obtener respuestas más precisas, asegúrate de haber procesado tus conversaciones primero usando el botón "🚀 Procesar Conversaciones".

¿Hay algo específico sobre tus proyectos, tecnologías o automatización en lo que pueda ayudarte?"""
    
    # Construcción de respuesta contextual
    response_parts = [
        f"🔥 Encontré información relevante en tu memoria sobre: **{query}**",
        ""
    ]
    
    # Agrupar conceptos por categoría
    concepts_by_category = defaultdict(list)
    for concept in concepts[:8]:  # Top 8 conceptos
        concepts_by_category[concept['category']].append(concept)
    
    # Describir conceptos encontrados por categoría
    for category, category_concepts in concepts_by_category.items():
        category_name = category.replace('_', ' ').title()
        concept_names = [c['name'] for c in category_concepts[:3]]  # Top 3 por categoría
        
        response_parts.append(f"**{category_name}:** {', '.join(concept_names)}")
    
    response_parts.append("")
    
    # Información de trazabilidad
    if traceability:
        source_convs = traceability.get('source_conversations', 0)
        source_msgs = traceability.get('source_messages', 0)
        
        response_parts.append(f"📊 **Trazabilidad:** Encontrado en {source_convs} conversaciones, {source_msgs} mensajes específicos.")
    
    # Contexto específico del concepto más fuerte
    if concepts:
        strongest_concept = max(concepts, key=lambda c: c['strength'])
        context_snippet = strongest_concept.get('context', '')
        
        if context_snippet and len(context_snippet) > 10:
            # Limpiar contexto de marcadores
            clean_context = context_snippet.replace('**', '').strip()
            if len(clean_context) > 150:
                clean_context = clean_context[:150] + "..."
            
            response_parts.append(f"💡 **Contexto relevante:** {clean_context}")
    
    response_parts.append("")
    response_parts.append("¿Te gustaría que profundice en algún aspecto específico o que busque conexiones con otros proyectos tuyos?")
    
    return "\n".join(response_parts)

@app.get("/stats")
async def get_system_stats():
    """
    Obtiene estadísticas completas del sistema.
    
    Returns:
        Estadísticas detalladas de conversaciones y conceptos
    """
    global database
    
    if not database:
        raise HTTPException(status_code=500, detail="Base de datos no inicializada")
    
    try:
        stats = database.get_conversation_stats()
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_system_status():
    """
    Obtiene el estado actual del sistema.
    
    Returns:
        Estado del sistema y componentes
    """
    global conversation_processor, database
    
    status = {
        'status': 'ready' if (conversation_processor and database) else 'initializing',
        'database_status': 'connected' if database else 'disconnected',
        'processor_status': 'ready' if conversation_processor else 'not_ready',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat()
    }
    
    if database:
        try:
            # Verificar conectividad de BD
            stats = database.get_conversation_stats()
            status['database_stats'] = {
                'total_conversations': stats.get('total_conversations', 0),
                'total_concepts': stats.get('total_concepts', 0)
            }
        except Exception as e:
            status['database_status'] = f'error: {str(e)}'
    
    return status

@app.get("/export-data")
async def export_system_data():
    """
    Exporta todos los datos del sistema.
    
    Returns:
        Archivo JSON con todos los datos procesados
    """
    global database
    
    if not database:
        raise HTTPException(status_code=500, detail="Base de datos no inicializada")
    
    try:
        # Obtener estadísticas completas
        stats = database.get_conversation_stats()
        
        # Obtener muestra de conceptos
        sample_concepts = database.search_concepts("", limit=100)
        
        export_data = {
            'export_info': {
                'version': '3.0.0',
                'export_date': datetime.now().isoformat(),
                'total_conversations': stats.get('total_conversations', 0),
                'total_concepts': stats.get('total_concepts', 0)
            },
            'system_stats': stats,
            'sample_concepts': sample_concepts,
            'config': {
                'db_path': CONFIG.db_path,
                'min_concept_strength': CONFIG.min_concept_strength,
                'max_concepts_per_conversation': CONFIG.max_concepts_per_conversation
            }
        }
        
        return JSONResponse(
            content=export_data,
            headers={
                'Content-Disposition': f'attachment; filename=ianae_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error exportando datos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-document", response_model=Dict[str, Any])
async def analyze_document_endpoint(doc: DocumentAnalysis):
    """
    Analiza un documento y extrae conceptos con trazabilidad.
    
    Args:
        doc: Documento a analizar
        
    Returns:
        Análisis completo del documento con conceptos extraídos
    """
    global conversation_processor, database
    
    if not conversation_processor:
        raise HTTPException(status_code=500, detail="Procesador no inicializado")
    
    try:
        # Extraer conceptos del documento
        concepts = conversation_processor._extract_concepts_from_text(
            doc.content, 
            f"doc_{int(time.time())}", 
            f"doc_msg_{int(time.time())}"
        )
        
        # Buscar conceptos similares existentes
        existing_concepts = []
        if database:
            existing_concepts = database.search_concepts(
                doc.content[:500],  # Primeros 500 caracteres para búsqueda
                limit=10
            )
        
        # Calcular estadísticas
        category_stats = defaultdict(int)
        strength_distribution = defaultdict(int)
        
        for concept in concepts:
            category_stats[concept.category.value] += 1
            strength_bucket = f"{int(concept.strength * 10) / 10:.1f}"
            strength_distribution[strength_bucket] += 1
        
        return {
            'status': 'success',
            'filename': doc.filename,
            'analysis': {
                'total_concepts': len(concepts),
                'unique_concepts': len(set(c.name for c in concepts)),
                'avg_strength': sum(c.strength for c in concepts) / len(concepts) if concepts else 0,
                'category_distribution': dict(category_stats),
                'strength_distribution': dict(strength_distribution)
            },
            'concepts_extracted': [
                {
                    'name': c.name,
                    'category': c.category.value,
                    'strength': c.strength,
                    'confidence': c.confidence,
                    'context': c.context[:100] + "..." if len(c.context) > 100 else c.context,
                    'extraction_method': c.extraction_method
                }
                for c in sorted(concepts, key=lambda x: x.strength, reverse=True)[:20]
            ],
            'existing_matches': [
                {
                    'name': ec['name'],
                    'category': ec['category'],
                    'strength': ec['strength'],
                    'source_conversation': ec.get('source_conversation', 'unknown')
                }
                for ec in existing_concepts[:10]
            ],
            'patterns_detected': doc.detect_patterns if hasattr(doc, 'detect_patterns') and doc.detect_patterns else [],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error analizando documento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"""
🔥 IANAE 3.0 - SISTEMA COMPLETO CON TRAZABILIDAD
===============================================

✅ Procesamiento completo de conversaciones JSON
✅ Extracción de conceptos con trazabilidad total
✅ Creación de resúmenes con valor y patrones
✅ Base de datos SQLite con índices optimizados
✅ Sistema de pensamiento emergente
✅ Interfaz web completa con tiempo real
✅ API REST documentada
✅ Exportación de datos completa

📊 Configuración:
   • Base de datos: {CONFIG.db_path}
   • Conversaciones: {CONFIG.conversations_json_path}
   • Salida: {CONFIG.output_conversations_path}
   • Fuerza mínima conceptos: {CONFIG.min_concept_strength}
   • Conceptos por conversación: {CONFIG.max_concepts_per_conversation}

🚀 Iniciando en http://localhost:8000
📚 Documentación: http://localhost:8000/docs
""")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=False  # Deshabilitado para producción
    )