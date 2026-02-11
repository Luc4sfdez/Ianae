# Base processor 
#!/usr/bin/env python3
"""
processors/base.py - Clase base abstracta para todos los procesadores IANAE
Establece la interfaz común que deben implementar todos los procesadores
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import json
import os
from datetime import datetime
import hashlib
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """
    Clase base abstracta para todos los procesadores de conversaciones IANAE.
    Define la interfaz común que deben implementar ChatGPT, Claude, Cline, etc.
    """
    
    def __init__(self, name: str):
        """
        Inicializa el procesador base
        
        Args:
            name: Nombre del procesador (e.g., 'chatgpt', 'claude', 'cline')
        """
        self.name = name
        self.supported_formats = []  # Debe ser definido por subclases
        self.stats = {
            'files_processed': 0,
            'conversations_extracted': 0,
            'messages_extracted': 0,
            'errors_encountered': 0,
            'processing_time_total': 0.0
        }
        
        logger.info(f"Inicializado procesador: {self.name}")
    
    @abstractmethod
    def can_process(self, file_path: str, content_preview: str = None) -> bool:
        """
        Determina si este procesador puede manejar el archivo dado.
        
        Args:
            file_path: Ruta del archivo a procesar
            content_preview: Primeros caracteres del archivo (opcional)
            
        Returns:
            True si puede procesar el archivo, False en caso contrario
        """
        pass
    
    @abstractmethod
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Procesa un archivo y extrae las conversaciones.
        
        Args:
            file_path: Ruta del archivo a procesar
            
        Returns:
            Lista de conversaciones extraídas en formato estándar
            
        Raises:
            ProcessingError: Si hay errores durante el procesamiento
        """
        pass
    
    def validate_conversation(self, conversation: Dict[str, Any]) -> bool:
        """
        Valida que una conversación tenga la estructura mínima requerida.
        
        Args:
            conversation: Diccionario con datos de conversación
            
        Returns:
            True si la conversación es válida
        """
        required_fields = ['id', 'titulo', 'plataforma', 'mensajes']
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in conversation:
                logger.warning(f"Conversación inválida: falta campo '{field}'")
                return False
        
        # Verificar que tenga al menos un mensaje
        if not conversation['mensajes'] or len(conversation['mensajes']) == 0:
            logger.warning("Conversación inválida: sin mensajes")
            return False
        
        # Verificar estructura de mensajes
        for i, mensaje in enumerate(conversation['mensajes']):
            if not self.validate_message(mensaje):
                logger.warning(f"Mensaje {i} inválido en conversación {conversation['id']}")
                return False
        
        return True
    
    def validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Valida que un mensaje tenga la estructura mínima requerida.
        
        Args:
            message: Diccionario con datos del mensaje
            
        Returns:
            True si el mensaje es válido
        """
        required_fields = ['role', 'content']
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in message:
                return False
        
        # Verificar que el role sea válido
        valid_roles = ['user', 'assistant', 'human', 'system']
        if message['role'] not in valid_roles:
            return False
        
        # Verificar que el contenido no esté vacío
        if not message['content'] or not message['content'].strip():
            return False
        
        return True
    
    def normalize_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza una conversación al formato estándar IANAE.
        
        Args:
            conversation: Conversación en formato específico del procesador
            
        Returns:
            Conversación en formato estándar
        """
        # Formato estándar IANAE
        normalized = {
            'id': str(conversation.get('id', '')),
            'titulo': conversation.get('titulo', conversation.get('title', 'Sin título')),
            'plataforma': self.name,
            'timestamp': conversation.get('timestamp'),
            'mensajes': [],
            'metadata': {
                'processor': self.name,
                'original_format': conversation.get('original_format', 'unknown'),
                'processed_at': datetime.now().isoformat(),
                'total_messages': len(conversation.get('mensajes', [])),
                'conversation_hash': self.calculate_conversation_hash(conversation)
            }
        }
        
        # Normalizar mensajes
        for mensaje in conversation.get('mensajes', []):
            normalized_message = self.normalize_message(mensaje)
            if normalized_message:
                normalized['mensajes'].append(normalized_message)
        
        # Actualizar contador real de mensajes
        normalized['metadata']['total_messages'] = len(normalized['mensajes'])
        
        return normalized
    
    def normalize_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normaliza un mensaje al formato estándar IANAE.
        
        Args:
            message: Mensaje en formato específico del procesador
            
        Returns:
            Mensaje en formato estándar o None si inválido
        """
        if not self.validate_message(message):
            return None
        
        # Normalizar role
        role_mapping = {
            'human': 'user',
            'user': 'user',
            'assistant': 'assistant',
            'system': 'system'
        }
        
        normalized_role = role_mapping.get(message['role'], message['role'])
        
        return {
            'id': message.get('id', ''),
            'role': normalized_role,
            'content': message['content'].strip(),
            'timestamp': message.get('timestamp'),
            'metadata': {
                'original_role': message['role'],
                'content_length': len(message['content']),
                'content_hash': self.calculate_content_hash(message['content'])
            }
        }
    
    def calculate_conversation_hash(self, conversation: Dict[str, Any]) -> str:
        """
        Calcula hash único para una conversación basado en su contenido.
        
        Args:
            conversation: Datos de la conversación
            
        Returns:
            Hash MD5 de la conversación
        """
        # Crear string representativo de la conversación
        content_parts = [
            conversation.get('titulo', ''),
            str(conversation.get('timestamp', '')),
            str(len(conversation.get('mensajes', [])))
        ]
        
        # Agregar contenido de primeros y últimos mensajes
        mensajes = conversation.get('mensajes', [])
        if mensajes:
            content_parts.append(mensajes[0].get('content', ''))
            if len(mensajes) > 1:
                content_parts.append(mensajes[-1].get('content', ''))
        
        content_string = '|'.join(content_parts)
        return hashlib.md5(content_string.encode('utf-8')).hexdigest()
    
    def calculate_content_hash(self, content: str) -> str:
        """
        Calcula hash del contenido de un mensaje.
        
        Args:
            content: Contenido del mensaje
            
        Returns:
            Hash MD5 del contenido
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def update_stats(self, conversations_processed: int, messages_processed: int, 
                    processing_time: float, errors: int = 0):
        """
        Actualiza estadísticas del procesador.
        
        Args:
            conversations_processed: Número de conversaciones procesadas
            messages_processed: Número de mensajes procesados
            processing_time: Tiempo de procesamiento en segundos
            errors: Número de errores encontrados
        """
        self.stats['files_processed'] += 1
        self.stats['conversations_extracted'] += conversations_processed
        self.stats['messages_extracted'] += messages_processed
        self.stats['errors_encountered'] += errors
        self.stats['processing_time_total'] += processing_time
        
        logger.info(f"Stats actualizadas para {self.name}: "
                   f"{conversations_processed} conv, {messages_processed} msg, "
                   f"{processing_time:.2f}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesador.
        
        Returns:
            Diccionario con estadísticas completas
        """
        stats = self.stats.copy()
        
        # Calcular estadísticas derivadas
        if stats['files_processed'] > 0:
            stats['avg_conversations_per_file'] = stats['conversations_extracted'] / stats['files_processed']
            stats['avg_processing_time_per_file'] = stats['processing_time_total'] / stats['files_processed']
        else:
            stats['avg_conversations_per_file'] = 0
            stats['avg_processing_time_per_file'] = 0
        
        if stats['conversations_extracted'] > 0:
            stats['avg_messages_per_conversation'] = stats['messages_extracted'] / stats['conversations_extracted']
        else:
            stats['avg_messages_per_conversation'] = 0
        
        stats['error_rate'] = stats['errors_encountered'] / max(1, stats['files_processed'])
        
        return stats
    
    def reset_stats(self):
        """Reinicia las estadísticas del procesador."""
        self.stats = {
            'files_processed': 0,
            'conversations_extracted': 0,
            'messages_extracted': 0,
            'errors_encountered': 0,
            'processing_time_total': 0.0
        }
        logger.info(f"Estadísticas reiniciadas para {self.name}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Obtiene información completa del procesador.
        
        Returns:
            Diccionario con información del procesador
        """
        return {
            'name': self.name,
            'supported_formats': self.supported_formats,
            'stats': self.get_stats(),
            'capabilities': {
                'can_detect_format': True,
                'supports_incremental': True,
                'handles_metadata': True,
                'supports_deduplication': True
            },
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat()
        }
    
    def __str__(self) -> str:
        """Representación string del procesador."""
        return f"<{self.__class__.__name__}(name='{self.name}', files={self.stats['files_processed']})>"
    
    def __repr__(self) -> str:
        """Representación detallada del procesador."""
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"formats={self.supported_formats}, "
                f"stats={self.get_stats()})")


class ProcessingError(Exception):
    """Excepción específica para errores de procesamiento."""
    
    def __init__(self, message: str, processor_name: str = None, file_path: str = None):
        self.processor_name = processor_name
        self.file_path = file_path
        super().__init__(message)
    
    def __str__(self):
        base_msg = super().__str__()
        if self.processor_name and self.file_path:
            return f"[{self.processor_name}] Error procesando {self.file_path}: {base_msg}"
        elif self.processor_name:
            return f"[{self.processor_name}] {base_msg}"
        else:
            return base_msg


# Funciones de utilidad para los procesadores

def load_file_safely(file_path: str, encoding: str = 'utf-8') -> Union[str, None]:
    """
    Carga un archivo de forma segura.
    
    Args:
        file_path: Ruta del archivo
        encoding: Codificación del archivo
        
    Returns:
        Contenido del archivo o None si hay error
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error cargando archivo {file_path}: {e}")
        return None

def load_json_safely(file_path: str) -> Union[Dict, List, None]:
    """
    Carga un archivo JSON de forma segura.
    
    Args:
        file_path: Ruta del archivo JSON
        
    Returns:
        Datos JSON o None si hay error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error JSON en {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error cargando JSON {file_path}: {e}")
        return None

def get_file_preview(file_path: str, max_chars: int = 2000) -> str:
    """
    Obtiene preview del inicio de un archivo.
    
    Args:
        file_path: Ruta del archivo
        max_chars: Máximo número de caracteres a leer
        
    Returns:
        Preview del archivo
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(max_chars)
    except Exception as e:
        logger.error(f"Error obteniendo preview de {file_path}: {e}")
        return ""

def validate_file_path(file_path: str) -> bool:
    """
    Valida que un archivo existe y es legible.
    
    Args:
        file_path: Ruta del archivo
        
    Returns:
        True si el archivo es válido
    """
    if not file_path:
        return False
    
    if not os.path.exists(file_path):
        logger.error(f"Archivo no existe: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        logger.error(f"La ruta no es un archivo: {file_path}")
        return False
    
    if not os.access(file_path, os.R_OK):
        logger.error(f"Archivo no legible: {file_path}")
        return False
    
    return True