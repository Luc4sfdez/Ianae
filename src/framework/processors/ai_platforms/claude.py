# Claude processor 
#!/usr/bin/env python3
"""
processors/claude.py - Procesador para archivos de Claude
Actualizado para heredar de BaseProcessor y seguir estándares IANAE
"""

import json
import time
from typing import List, Dict, Any, Optional
from .base import BaseProcessor, ProcessingError, load_json_safely, get_file_preview
import logging

logger = logging.getLogger(__name__)

class ClaudeProcessor(BaseProcessor):
    """
    Procesador especializado para archivos JSON de Claude.
    Maneja exportaciones de conversaciones de Claude con estructura específica.
    """
    
    def __init__(self):
        super().__init__('claude')
        self.supported_formats = ['.json']
        
        # Patrones específicos de Claude
        self.claude_indicators = [
            'conversation_id',
            'chat_messages',
            'sender',
            'uuid',
            'created_at',
            'updated_at',
            'name',
            'summary'
        ]
    
    def can_process(self, file_path: str, content_preview: str = None) -> bool:
        """
        Determina si este archivo es de Claude analizando su estructura.
        
        Args:
            file_path: Ruta del archivo
            content_preview: Preview del contenido (opcional)
            
        Returns:
            True si puede procesar el archivo
        """
        try:
            # Verificar extensión
            if not file_path.lower().endswith('.json'):
                return False
            
            # Obtener preview si no se proporcionó
            if content_preview is None:
                content_preview = get_file_preview(file_path, 3000)
            
            if not content_preview:
                return False
            
            # Verificar que es JSON válido
            try:
                preview_data = json.loads(content_preview[:2000])
            except json.JSONDecodeError:
                return False
            
            # Detectar patrones específicos de Claude
            confidence_score = 0
            
            # Patrón 1: Lista de conversaciones de Claude
            if isinstance(preview_data, list) and len(preview_data) > 0:
                first_item = preview_data[0]
                if isinstance(first_item, dict):
                    # Indicadores fuertes de Claude
                    if 'conversation_id' in first_item:
                        confidence_score += 30
                    if 'chat_messages' in first_item:
                        confidence_score += 25
                    if 'name' in first_item:
                        confidence_score += 15
                    if 'created_at' in first_item:
                        confidence_score += 10
                    
                    # Verificar estructura de mensajes
                    chat_messages = first_item.get('chat_messages', [])
                    if isinstance(chat_messages, list) and len(chat_messages) > 0:
                        first_msg = chat_messages[0]
                        if isinstance(first_msg, dict):
                            if 'sender' in first_msg:
                                confidence_score += 15
                            if 'uuid' in first_msg:
                                confidence_score += 10
                            if 'text' in first_msg:
                                confidence_score += 5
            
            # Patrón 2: Conversación individual de Claude
            elif isinstance(preview_data, dict):
                if 'conversation_id' in preview_data and 'chat_messages' in preview_data:
                    confidence_score += 50
                    if 'name' in preview_data:
                        confidence_score += 20
                    if 'created_at' in preview_data:
                        confidence_score += 10
            
            # Verificar indicadores en el texto
            content_lower = content_preview.lower()
            for indicator in self.claude_indicators:
                if indicator in content_lower:
                    confidence_score += 3
            
            # Verificar ausencia de patrones de ChatGPT (diferenciación)
            if 'mapping' in content_lower:
                confidence_score -= 20
            
            # Umbral de confianza para Claude
            return confidence_score >= 50
            
        except Exception as e:
            logger.error(f"Error detectando Claude en {file_path}: {e}")
            return False
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Procesa un archivo JSON de Claude completo.
        
        Args:
            file_path: Ruta del archivo a procesar
            
        Returns:
            Lista de conversaciones en formato estándar IANAE
            
        Raises:
            ProcessingError: Si hay errores durante el procesamiento
        """
        start_time = time.time()
        
        try:
            logger.info(f"Procesando archivo Claude: {file_path}")
            
            # Cargar datos JSON
            data = load_json_safely(file_path)
            if data is None:
                raise ProcessingError(f"No se pudo cargar JSON desde {file_path}", 
                                    self.name, file_path)
            
            # Procesar según estructura
            conversaciones_raw = []
            
            if isinstance(data, list):
                logger.info(f"Procesando {len(data)} conversaciones de Claude...")
                conversaciones_raw = self._process_conversation_list(data)
                
            elif isinstance(data, dict) and 'conversation_id' in data:
                logger.info("Procesando conversación individual de Claude...")
                conv = self._process_single_conversation(data, 0)
                if conv:
                    conversaciones_raw = [conv]
            else:
                raise ProcessingError(f"Estructura JSON no reconocida en {file_path}", 
                                    self.name, file_path)
            
            # Normalizar conversaciones al formato IANAE
            conversaciones_normalizadas = []
            errors = 0
            
            for conv_raw in conversaciones_raw:
                try:
                    # Agregar metadatos de procesamiento
                    conv_raw['original_format'] = 'claude_json'
                    
                    # Normalizar usando BaseProcessor
                    conv_normalizada = self.normalize_conversation(conv_raw)
                    
                    # Validar usando BaseProcessor
                    if self.validate_conversation(conv_normalizada):
                        conversaciones_normalizadas.append(conv_normalizada)
                    else:
                        logger.warning(f"Conversación inválida descartada: {conv_raw.get('id', 'unknown')}")
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Error normalizando conversación {conv_raw.get('id', 'unknown')}: {e}")
                    errors += 1
                    continue
            
            # Actualizar estadísticas
            processing_time = time.time() - start_time
            total_messages = sum(len(conv['mensajes']) for conv in conversaciones_normalizadas)
            
            self.update_stats(
                conversations_processed=len(conversaciones_normalizadas),
                messages_processed=total_messages,
                processing_time=processing_time,
                errors=errors
            )
            
            logger.info(f"Claude procesado: {len(conversaciones_normalizadas)} conversaciones, "
                       f"{total_messages} mensajes en {processing_time:.2f}s")
            
            return conversaciones_normalizadas
            
        except ProcessingError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(0, 0, processing_time, 1)
            raise ProcessingError(f"Error inesperado procesando Claude: {e}", 
                                self.name, file_path)
    
    def _process_conversation_list(self, conversations_data: List[Dict]) -> List[Dict]:
        """
        Procesa una lista de conversaciones de Claude.
        
        Args:
            conversations_data: Lista de datos de conversaciones
            
        Returns:
            Lista de conversaciones procesadas
        """
        conversaciones = []
        
        for i, conv_data in enumerate(conversations_data):
            try:
                conversacion = self._process_single_conversation(conv_data, i)
                if conversacion and conversacion.get('mensajes'):
                    conversaciones.append(conversacion)
                    
                # Log progreso cada 50 conversaciones
                if i % 50 == 0 and i > 0:
                    logger.info(f"Procesadas {i}/{len(conversations_data)} conversaciones Claude...")
                    
            except Exception as e:
                logger.warning(f"Error procesando conversación Claude {i}: {e}")
                continue
        
        return conversaciones
    
    def _process_single_conversation(self, conv_data: Dict, index: int) -> Optional[Dict]:
        """
        Procesa una conversación individual de Claude.
        
        Args:
            conv_data: Datos de la conversación
            index: Índice de la conversación
            
        Returns:
            Conversación procesada o None si hay error
        """
        try:
            # Extraer metadatos básicos
            conv_id = conv_data.get('conversation_id', f'claude_conv_{index}')
            titulo = conv_data.get('name', f'Conversación Claude {index + 1}')
            
            # Timestamps
            created_at = conv_data.get('created_at')
            updated_at = conv_data.get('updated_at')
            
            # Procesar mensajes de chat
            chat_messages = conv_data.get('chat_messages', [])
            if not chat_messages:
                logger.warning(f"Conversación {conv_id} sin mensajes")
                return None
            
            mensajes = self._extract_messages_from_chat(chat_messages)
            
            # Solo retornar si hay mensajes válidos
            if not mensajes:
                logger.warning(f"Conversación {conv_id} sin mensajes válidos")
                return None
            
            return {
                'id': conv_id,
                'titulo': titulo,
                'plataforma': 'claude',
                'timestamp': created_at,
                'mensajes': mensajes,
                'metadata': {
                    'conversation_index': index,
                    'original_id': conv_data.get('conversation_id'),
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'summary': conv_data.get('summary'),
                    'total_chat_messages': len(chat_messages)
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando conversación Claude {index}: {e}")
            return None
    
    def _extract_messages_from_chat(self, chat_messages: List[Dict]) -> List[Dict]:
        """
        Extrae mensajes del array chat_messages de Claude.
        
        Args:
            chat_messages: Lista de mensajes de chat
            
        Returns:
            Lista de mensajes extraídos
        """
        mensajes = []
        
        for i, message_data in enumerate(chat_messages):
            try:
                # Verificar que tenga texto
                text_content = message_data.get('text', '').strip()
                if not text_content:
                    continue
                
                # Extraer información básica
                sender = message_data.get('sender', 'unknown')
                uuid = message_data.get('uuid', f'claude_msg_{i}')
                created_at = message_data.get('created_at')
                
                # Mapear sender a role estándar
                role_mapping = {
                    'human': 'user',
                    'assistant': 'assistant',
                    'user': 'user'
                }
                role = role_mapping.get(sender, sender)
                
                # Crear mensaje normalizado
                mensaje = {
                    'id': uuid,
                    'role': role,
                    'content': text_content,
                    'timestamp': created_at,
                    'metadata': {
                        'original_sender': sender,
                        'uuid': uuid,
                        'message_index': i,
                        'content_length': len(text_content),
                        'has_attachments': bool(message_data.get('attachments')),
                        'files': message_data.get('files', [])
                    }
                }
                
                # Agregar metadatos adicionales si están disponibles
                if 'updated_at' in message_data:
                    mensaje['metadata']['updated_at'] = message_data['updated_at']
                
                if 'attachments' in message_data:
                    mensaje['metadata']['attachments'] = message_data['attachments']
                
                mensajes.append(mensaje)
                
            except Exception as e:
                logger.warning(f"Error extrayendo mensaje Claude {i}: {e}")
                continue
        
        # Ordenar mensajes por created_at si está disponible
        mensajes_con_timestamp = [m for m in mensajes if m.get('timestamp')]
        if mensajes_con_timestamp:
            mensajes.sort(key=lambda x: x.get('timestamp', ''))
        
        return mensajes
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Información específica del procesador Claude.
        
        Returns:
            Diccionario con información detallada
        """
        base_info = self.get_info()
        
        # Agregar información específica de Claude
        base_info.update({
            'claude_specifics': {
                'handles_chat_messages': True,
                'supports_attachments': True,
                'extracts_uuid': True,
                'preserves_timestamps': True,
                'confidence_threshold': 50
            },
            'detection_patterns': self.claude_indicators,
            'processing_features': {
                'batch_processing': True,
                'conversation_metadata': True,
                'file_attachments': True,
                'sender_mapping': True
            },
            'supported_senders': ['human', 'assistant', 'user'],
            'timestamp_formats': ['ISO8601', 'RFC3339']
        })
        
        return base_info


# Función de utilidad para testing rápido
def test_claude_processor():
    """Función de prueba rápida para el procesador Claude"""
    processor = ClaudeProcessor()
    
    print("🧪 TESTING ClaudeProcessor")
    print("=" * 40)
    
    # Test básico de detección
    print(f"Procesador: {processor.name}")
    print(f"Formatos soportados: {processor.supported_formats}")
    print(f"Estadísticas iniciales: {processor.get_stats()}")
    
    # Simular detección con contenido de ejemplo
    sample_content = '''
    [
        {
            "conversation_id": "test-conversation-1",
            "name": "Test Claude Conversation",
            "created_at": "2024-01-01T10:00:00Z",
            "chat_messages": [
                {
                    "uuid": "msg-1",
                    "sender": "human",
                    "text": "Hello Claude",
                    "created_at": "2024-01-01T10:00:00Z"
                },
                {
                    "uuid": "msg-2", 
                    "sender": "assistant",
                    "text": "Hello! How can I help you?",
                    "created_at": "2024-01-01T10:01:00Z"
                }
            ]
        }
    ]
    '''
    
    can_process = processor.can_process("test.json", sample_content)
    print(f"¿Puede procesar contenido de ejemplo? {can_process}")
    
    return processor

if __name__ == "__main__":
    test_claude_processor()