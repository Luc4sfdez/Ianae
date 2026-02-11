# ChatGPT processor 
#!/usr/bin/env python3
"""
processors/chatgpt.py - Procesador para archivos de ChatGPT
Actualizado para heredar de BaseProcessor y seguir estándares IANAE
"""

import json
import time
from typing import List, Dict, Any, Optional
from .base import BaseProcessor, ProcessingError, load_json_safely, get_file_preview
import logging

logger = logging.getLogger(__name__)

class ChatGPTProcessor(BaseProcessor):
    """
    Procesador especializado para archivos JSON de ChatGPT.
    Maneja tanto conversaciones individuales como archivos con múltiples conversaciones.
    """
    
    def __init__(self):
        super().__init__('chatgpt')
        self.supported_formats = ['.json']
        
        # Patrones específicos de ChatGPT
        self.chatgpt_indicators = [
            'mapping',
            'conversation_id',
            'create_time',
            'update_time',
            'title',
            'author',
            'role',
            'parts'
        ]
    
    def can_process(self, file_path: str, content_preview: str = None) -> bool:
        """
        Determina si este archivo es de ChatGPT analizando su estructura.
        
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
            
            # Detectar patrones específicos de ChatGPT
            confidence_score = 0
            
            # Patrón 1: Lista de conversaciones
            if isinstance(preview_data, list) and len(preview_data) > 0:
                first_item = preview_data[0]
                if isinstance(first_item, dict) and 'mapping' in first_item:
                    confidence_score += 30
                    
                    # Verificar estructura típica de ChatGPT
                    if 'title' in first_item:
                        confidence_score += 20
                    if 'create_time' in first_item:
                        confidence_score += 15
                    if 'conversation_id' in first_item or 'id' in first_item:
                        confidence_score += 15
            
            # Patrón 2: Conversación individual
            elif isinstance(preview_data, dict) and 'mapping' in preview_data:
                confidence_score += 40
                if 'title' in preview_data:
                    confidence_score += 20
                if 'create_time' in preview_data:
                    confidence_score += 15
            
            # Verificar indicadores en el texto
            content_lower = content_preview.lower()
            for indicator in self.chatgpt_indicators:
                if indicator in content_lower:
                    confidence_score += 5
            
            # Umbral de confianza para ChatGPT
            return confidence_score >= 60
            
        except Exception as e:
            logger.error(f"Error detectando ChatGPT en {file_path}: {e}")
            return False
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Procesa un archivo JSON de ChatGPT completo.
        
        Args:
            file_path: Ruta del archivo a procesar
            
        Returns:
            Lista de conversaciones en formato estándar IANAE
            
        Raises:
            ProcessingError: Si hay errores durante el procesamiento
        """
        start_time = time.time()
        
        try:
            logger.info(f"Procesando archivo ChatGPT: {file_path}")
            
            # Cargar datos JSON
            data = load_json_safely(file_path)
            if data is None:
                raise ProcessingError(f"No se pudo cargar JSON desde {file_path}", 
                                    self.name, file_path)
            
            # Procesar según estructura
            conversaciones_raw = []
            
            if isinstance(data, list):
                logger.info(f"Procesando {len(data)} conversaciones de ChatGPT...")
                conversaciones_raw = self._process_conversation_list(data)
                
            elif isinstance(data, dict) and 'mapping' in data:
                logger.info("Procesando conversación individual de ChatGPT...")
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
                    conv_raw['original_format'] = 'chatgpt_json'
                    
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
            
            logger.info(f"ChatGPT procesado: {len(conversaciones_normalizadas)} conversaciones, "
                       f"{total_messages} mensajes en {processing_time:.2f}s")
            
            return conversaciones_normalizadas
            
        except ProcessingError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(0, 0, processing_time, 1)
            raise ProcessingError(f"Error inesperado procesando ChatGPT: {e}", 
                                self.name, file_path)
    
    def _process_conversation_list(self, conversations_data: List[Dict]) -> List[Dict]:
        """
        Procesa una lista de conversaciones de ChatGPT.
        
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
                    
                # Log progreso cada 100 conversaciones
                if i % 100 == 0 and i > 0:
                    logger.info(f"Procesadas {i}/{len(conversations_data)} conversaciones...")
                    
            except Exception as e:
                logger.warning(f"Error procesando conversación {i}: {e}")
                continue
        
        return conversaciones
    
    def _process_single_conversation(self, conv_data: Dict, index: int) -> Optional[Dict]:
        """
        Procesa una conversación individual de ChatGPT.
        
        Args:
            conv_data: Datos de la conversación
            index: Índice de la conversación
            
        Returns:
            Conversación procesada o None si hay error
        """
        try:
            # Extraer metadatos básicos
            conv_id = conv_data.get('id', f'chatgpt_conv_{index}')
            titulo = conv_data.get('title', f'Conversación ChatGPT {index + 1}')
            
            # Timestamp de creación
            create_time = conv_data.get('create_time')
            if create_time is None:
                create_time = conv_data.get('timestamp')
            
            # Procesar mapping de mensajes (estructura típica de ChatGPT)
            mapping = conv_data.get('mapping', {})
            if not mapping:
                logger.warning(f"Conversación {conv_id} sin mapping válido")
                return None
            
            mensajes = self._extract_messages_from_mapping(mapping, create_time)
            
            # Solo retornar si hay mensajes válidos
            if not mensajes:
                logger.warning(f"Conversación {conv_id} sin mensajes válidos")
                return None
            
            return {
                'id': conv_id,
                'titulo': titulo,
                'plataforma': 'chatgpt',
                'timestamp': create_time,
                'mensajes': mensajes,
                'metadata': {
                    'total_nodes': len(mapping),
                    'conversation_index': index,
                    'original_id': conv_data.get('id'),
                    'update_time': conv_data.get('update_time')
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando conversación ChatGPT {index}: {e}")
            return None
    
    def _extract_messages_from_mapping(self, mapping: Dict, default_timestamp=None) -> List[Dict]:
        """
        Extrae mensajes del mapping de ChatGPT.
        
        Args:
            mapping: Mapping de nodos de la conversación
            default_timestamp: Timestamp por defecto si no está disponible
            
        Returns:
            Lista de mensajes extraídos
        """
        mensajes = []
        
        for node_id, node_data in mapping.items():
            try:
                message_data = node_data.get('message')
                if not message_data:
                    continue
                
                # Extraer información del autor
                author = message_data.get('author', {})
                role = author.get('role', 'unknown')
                
                # Solo procesar mensajes de usuario y asistente
                if role not in ['user', 'assistant']:
                    continue
                
                # Extraer contenido
                content = message_data.get('content', {})
                parts = content.get('parts', [])
                
                # Unir todas las partes del mensaje
                texto_completo = ""
                for part in parts:
                    if isinstance(part, str):
                        texto_completo += part + " "
                
                texto_completo = texto_completo.strip()
                if not texto_completo:
                    continue
                
                # Crear mensaje normalizado
                mensaje = {
                    'id': message_data.get('id', node_id),
                    'role': role,
                    'content': texto_completo,
                    'timestamp': message_data.get('create_time', default_timestamp),
                    'metadata': {
                        'node_id': node_id,
                        'parent_id': node_data.get('parent'),
                        'children': node_data.get('children', []),
                        'author_name': author.get('name'),
                        'content_type': content.get('content_type', 'text'),
                        'parts_count': len(parts)
                    }
                }
                
                mensajes.append(mensaje)
                
            except Exception as e:
                logger.warning(f"Error extrayendo mensaje de nodo {node_id}: {e}")
                continue
        
        # Ordenar mensajes por timestamp si está disponible
        mensajes_con_timestamp = [m for m in mensajes if m.get('timestamp')]
        if mensajes_con_timestamp:
            mensajes.sort(key=lambda x: x.get('timestamp', 0))
        
        return mensajes
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Información específica del procesador ChatGPT.
        
        Returns:
            Diccionario con información detallada
        """
        base_info = self.get_info()
        
        # Agregar información específica de ChatGPT
        base_info.update({
            'chatgpt_specifics': {
                'handles_mapping_structure': True,
                'supports_conversation_trees': True,
                'extracts_metadata': True,
                'supported_content_types': ['text', 'code'],
                'confidence_threshold': 60
            },
            'detection_patterns': self.chatgpt_indicators,
            'processing_features': {
                'batch_processing': True,
                'incremental_progress': True,
                'error_recovery': True,
                'message_validation': True
            }
        })
        
        return base_info


# Función de utilidad para testing rápido
def test_chatgpt_processor():
    """Función de prueba rápida para el procesador ChatGPT"""
    processor = ChatGPTProcessor()
    
    print("🧪 TESTING ChatGPTProcessor")
    print("=" * 40)
    
    # Test básico de detección
    print(f"Procesador: {processor.name}")
    print(f"Formatos soportados: {processor.supported_formats}")
    print(f"Estadísticas iniciales: {processor.get_stats()}")
    
    # Simular detección con contenido de ejemplo
    sample_content = '''
    {
        "title": "Test Conversation",
        "create_time": 1234567890,
        "mapping": {
            "node1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Hello"]}
                }
            }
        }
    }
    '''
    
    can_process = processor.can_process("test.json", sample_content)
    print(f"¿Puede procesar contenido de ejemplo? {can_process}")
    
    return processor

if __name__ == "__main__":
    test_chatgpt_processor()