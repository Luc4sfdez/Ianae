# Cline processor 
#!/usr/bin/env python3
"""
processors/cline.py - Procesador para archivos de Cline/Continue
Actualizado para heredar de BaseProcessor y seguir estándares IANAE
"""

import time
from typing import List, Dict, Any, Optional
from .base import BaseProcessor, ProcessingError, load_file_safely, get_file_preview
import logging
import re

logger = logging.getLogger(__name__)

class ClineProcessor(BaseProcessor):
    """
    Procesador especializado para archivos Markdown de Cline/Continue.
    Maneja conversaciones en formato Markdown con estructura específica.
    """
    
    def __init__(self):
        super().__init__('cline')
        self.supported_formats = ['.md', '.txt']
        
        # Patrones específicos de Cline
        self.cline_indicators = [
            'cline task',
            '## human:',
            '## assistant:',
            'continue dev',
            'cline conversation',
            '### user',
            '### assistant'
        ]
        
        # Patrones de regex para detección
        self.cline_patterns = [
            r'#\s*cline\s+task',
            r'##\s*human\s*:',
            r'##\s*assistant\s*:',
            r'###\s*user',
            r'###\s*assistant',
            r'continue\s+dev',
            r'cline\s+conversation'
        ]
    
    def can_process(self, file_path: str, content_preview: str = None) -> bool:
        """
        Determina si este archivo es de Cline analizando su estructura.
        
        Args:
            file_path: Ruta del archivo
            content_preview: Preview del contenido (opcional)
            
        Returns:
            True si puede procesar el archivo
        """
        try:
            # Verificar extensión
            if not any(file_path.lower().endswith(ext) for ext in self.supported_formats):
                return False
            
            # Obtener preview si no se proporcionó
            if content_preview is None:
                content_preview = get_file_preview(file_path, 3000)
            
            if not content_preview:
                return False
            
            # Detectar patrones específicos de Cline
            confidence_score = 0
            content_lower = content_preview.lower()
            
            # Verificar indicadores textuales
            for indicator in self.cline_indicators:
                if indicator in content_lower:
                    confidence_score += 15
            
            # Verificar patrones con regex
            for pattern in self.cline_patterns:
                if re.search(pattern, content_preview, re.IGNORECASE):
                    confidence_score += 20
            
            # Patrones estructurales de markdown
            lines = content_preview.split('\n')
            header_count = 0
            conversation_markers = 0
            
            for line in lines[:50]:  # Revisar primeras 50 líneas
                line_lower = line.lower().strip()
                
                # Contar headers típicos
                if line.startswith('#'):
                    header_count += 1
                    if 'cline' in line_lower or 'task' in line_lower:
                        confidence_score += 10
                
                # Contar marcadores de conversación
                if line_lower.startswith('## human') or line_lower.startswith('## assistant'):
                    conversation_markers += 1
                    confidence_score += 15
                
                if line_lower.startswith('### user') or line_lower.startswith('### assistant'):
                    conversation_markers += 1
                    confidence_score += 10
            
            # Bonus por estructura coherente
            if header_count > 0 and conversation_markers > 1:
                confidence_score += 20
            
            # Penalizar si parece JSON o tiene estructura de otras plataformas
            if '{' in content_preview and '}' in content_preview:
                confidence_score -= 30
            
            if 'mapping' in content_lower or 'conversation_id' in content_lower:
                confidence_score -= 40
            
            # Umbral de confianza para Cline
            return confidence_score >= 40
            
        except Exception as e:
            logger.error(f"Error detectando Cline en {file_path}: {e}")
            return False
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Procesa un archivo Markdown de Cline completo.
        
        Args:
            file_path: Ruta del archivo a procesar
            
        Returns:
            Lista de conversaciones en formato estándar IANAE
            
        Raises:
            ProcessingError: Si hay errores durante el procesamiento
        """
        start_time = time.time()
        
        try:
            logger.info(f"Procesando archivo Cline: {file_path}")
            
            # Cargar contenido del archivo
            content = load_file_safely(file_path)
            if content is None:
                raise ProcessingError(f"No se pudo cargar archivo {file_path}", 
                                    self.name, file_path)
            
            # Procesar conversaciones desde el contenido
            conversaciones_raw = self._parse_markdown_conversations(content, file_path)
            
            if not conversaciones_raw:
                logger.warning(f"No se encontraron conversaciones válidas en {file_path}")
                return []
            
            # Normalizar conversaciones al formato IANAE
            conversaciones_normalizadas = []
            errors = 0
            
            for conv_raw in conversaciones_raw:
                try:
                    # Agregar metadatos de procesamiento
                    conv_raw['original_format'] = 'cline_markdown'
                    
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
            
            logger.info(f"Cline procesado: {len(conversaciones_normalizadas)} conversaciones, "
                       f"{total_messages} mensajes en {processing_time:.2f}s")
            
            return conversaciones_normalizadas
            
        except ProcessingError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(0, 0, processing_time, 1)
            raise ProcessingError(f"Error inesperado procesando Cline: {e}", 
                                self.name, file_path)
    
    def _parse_markdown_conversations(self, content: str, file_path: str) -> List[Dict]:
        """
        Parsea conversaciones desde contenido Markdown de Cline.
        
        Args:
            content: Contenido completo del archivo
            file_path: Ruta del archivo (para generar IDs)
            
        Returns:
            Lista de conversaciones parseadas
        """
        conversaciones = []
        
        # Detectar si es una conversación única o múltiples
        if self._is_single_task_conversation(content):
            conv = self._parse_single_conversation(content, file_path)
            if conv:
                conversaciones.append(conv)
        else:
            # Intentar parsear múltiples conversaciones
            convs = self._parse_multiple_conversations(content, file_path)
            conversaciones.extend(convs)
        
        return conversaciones
    
    def _is_single_task_conversation(self, content: str) -> bool:
        """
        Determina si el archivo contiene una sola conversación o múltiples.
        
        Args:
            content: Contenido del archivo
            
        Returns:
            True si es una sola conversación
        """
        # Buscar indicadores de tarea única
        single_task_patterns = [
            r'#\s*cline\s+task',
            r'#\s*task\s*:',
            r'##\s*human\s*:',
            r'##\s*assistant\s*:'
        ]
        
        task_headers = 0
        for pattern in single_task_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if pattern.startswith('#\\s*cline') or pattern.startswith('#\\s*task'):
                task_headers += len(matches)
        
        # Si hay un solo header de tarea, probablemente es conversación única
        return task_headers <= 1
    
    def _parse_single_conversation(self, content: str, file_path: str) -> Optional[Dict]:
        """
        Parsea una conversación única desde Markdown.
        
        Args:
            content: Contenido del archivo
            file_path: Ruta del archivo
            
        Returns:
            Conversación parseada o None
        """
        try:
            # Extraer título de la tarea
            titulo = self._extract_title_from_content(content)
            if not titulo:
                titulo = f"Cline Task - {file_path.split('/')[-1]}"
            
            # Parsear mensajes
            mensajes = self._extract_messages_from_markdown(content)
            
            if not mensajes:
                logger.warning(f"No se encontraron mensajes en {file_path}")
                return None
            
            # Generar ID único
            import hashlib
            conv_id = hashlib.md5(f"cline_{file_path}_{titulo}".encode()).hexdigest()[:16]
            
            return {
                'id': f"cline_{conv_id}",
                'titulo': titulo,
                'plataforma': 'cline',
                'timestamp': None,  # Cline no suele incluir timestamps
                'mensajes': mensajes,
                'metadata': {
                    'source_file': file_path,
                    'conversation_type': 'single_task',
                    'total_lines': len(content.split('\n')),
                    'file_size': len(content)
                }
            }
            
        except Exception as e:
            logger.error(f"Error parseando conversación única de Cline: {e}")
            return None
    
    def _parse_multiple_conversations(self, content: str, file_path: str) -> List[Dict]:
        """
        Parsea múltiples conversaciones desde Markdown.
        
        Args:
            content: Contenido del archivo
            file_path: Ruta del archivo
            
        Returns:
            Lista de conversaciones parseadas
        """
        conversaciones = []
        
        # Dividir por headers de nivel 1 o patrones de nueva conversación
        sections = re.split(r'\n(?=#\s)', content)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
                
            try:
                titulo = self._extract_title_from_content(section)
                if not titulo:
                    titulo = f"Conversación Cline {i + 1}"
                
                mensajes = self._extract_messages_from_markdown(section)
                
                if mensajes:
                    import hashlib
                    conv_id = hashlib.md5(f"cline_{file_path}_{i}_{titulo}".encode()).hexdigest()[:16]
                    
                    conversaciones.append({
                        'id': f"cline_{conv_id}",
                        'titulo': titulo,
                        'plataforma': 'cline',
                        'timestamp': None,
                        'mensajes': mensajes,
                        'metadata': {
                            'source_file': file_path,
                            'conversation_type': 'multi_section',
                            'section_index': i,
                            'section_lines': len(section.split('\n'))
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"Error parseando sección {i} de Cline: {e}")
                continue
        
        return conversaciones
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """
        Extrae el título de la conversación desde el contenido.
        
        Args:
            content: Contenido a analizar
            
        Returns:
            Título extraído o None
        """
        lines = content.split('\n')
        
        for line in lines[:10]:  # Revisar primeras 10 líneas
            line = line.strip()
            
            # Header de nivel 1
            if line.startswith('# '):
                return line[2:].strip()
            
            # Patrones específicos de Cline
            cline_title_patterns = [
                r'#\s*cline\s+task\s*:?\s*(.+)',
                r'#\s*task\s*:?\s*(.+)',
                r'##\s*(.+?)(?:\s*-\s*cline)?$'
            ]
            
            for pattern in cline_title_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if title and len(title) > 3:
                        return title
        
        return None
    
    def _extract_messages_from_markdown(self, content: str) -> List[Dict]:
        """
        Extrae mensajes desde el contenido Markdown.
        
        Args:
            content: Contenido Markdown
            
        Returns:
            Lista de mensajes extraídos
        """
        mensajes = []
        lines = content.split('\n')
        
        current_message = {'role': None, 'content_lines': []}
        message_counter = 0
        
        for line_num, line in enumerate(lines):
            line_original = line
            line_stripped = line.strip()
            
            # Detectar inicio de mensaje
            role_detected = None
            
            # Patrones de role con diferentes formatos
            role_patterns = [
                (r'^##\s*human\s*:?\s*', 'user'),
                (r'^##\s*assistant\s*:?\s*', 'assistant'),
                (r'^###\s*user\s*:?\s*', 'user'),
                (r'^###\s*assistant\s*:?\s*', 'assistant'),
                (r'^>\s*human\s*:?\s*', 'user'),
                (r'^>\s*assistant\s*:?\s*', 'assistant')
            ]
            
            for pattern, role in role_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    role_detected = role
                    # Remover el marcador del contenido
                    line_content = re.sub(pattern, '', line_stripped, flags=re.IGNORECASE).strip()
                    break
            
            if role_detected:
                # Guardar mensaje anterior si existe
                if current_message['role'] and current_message['content_lines']:
                    mensaje = self._create_message_from_lines(
                        current_message, message_counter
                    )
                    if mensaje:
                        mensajes.append(mensaje)
                        message_counter += 1
                
                # Iniciar nuevo mensaje
                current_message = {
                    'role': role_detected,
                    'content_lines': [line_content] if line_content else [],
                    'start_line': line_num
                }
            else:
                # Continuar mensaje actual
                if current_message['role']:
                    # Agregar línea al mensaje actual
                    current_message['content_lines'].append(line_original)
        
        # Guardar último mensaje
        if current_message['role'] and current_message['content_lines']:
            mensaje = self._create_message_from_lines(current_message, message_counter)
            if mensaje:
                mensajes.append(mensaje)
        
        return mensajes
    
    def _create_message_from_lines(self, message_data: Dict, index: int) -> Optional[Dict]:
        """
        Crea un mensaje desde las líneas recolectadas.
        
        Args:
            message_data: Datos del mensaje con líneas
            index: Índice del mensaje
            
        Returns:
            Mensaje formateado o None
        """
        try:
            # Unir líneas y limpiar
            content = '\n'.join(message_data['content_lines']).strip()
            
            # Remover líneas vacías excesivas
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            if not content:
                return None
            
            return {
                'id': f"cline_msg_{index}",
                'role': message_data['role'],
                'content': content,
                'timestamp': None,
                'metadata': {
                    'message_index': index,
                    'start_line': message_data.get('start_line', 0),
                    'content_length': len(content),
                    'line_count': len(message_data['content_lines'])
                }
            }
            
        except Exception as e:
            logger.warning(f"Error creando mensaje {index}: {e}")
            return None
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Información específica del procesador Cline.
        
        Returns:
            Diccionario con información detallada
        """
        base_info = self.get_info()
        
        # Agregar información específica de Cline
        base_info.update({
            'cline_specifics': {
                'handles_markdown': True,
                'supports_multiple_formats': True,
                'extracts_task_titles': True,
                'preserves_formatting': True,
                'confidence_threshold': 40
            },
            'detection_patterns': self.cline_indicators,
            'regex_patterns': self.cline_patterns,
            'processing_features': {
                'single_task_parsing': True,
                'multi_section_parsing': True,
                'title_extraction': True,
                'role_detection': True
            },
            'supported_roles': ['user', 'assistant', 'human'],
            'markdown_features': ['headers', 'code_blocks', 'lists', 'emphasis']
        })
        
        return base_info


# Función de utilidad para testing rápido
def test_cline_processor():
    """Función de prueba rápida para el procesador Cline"""
    processor = ClineProcessor()
    
    print("🧪 TESTING ClineProcessor")
    print("=" * 40)
    
    # Test básico de detección
    print(f"Procesador: {processor.name}")
    print(f"Formatos soportados: {processor.supported_formats}")
    print(f"Estadísticas iniciales: {processor.get_stats()}")
    
    # Simular detección con contenido de ejemplo
    sample_content = '''
    # Cline Task: Test Conversation
    
    ## Human:
    Hello, I need help with Python code.
    
    ## Assistant:
    I'd be happy to help you with Python! What specific task are you working on?
    
    ## Human:
    I want to create a simple calculator function.
    
    ## Assistant:
    Here's a simple calculator function:
    
    ```python
    def calculator(a, b, operation):
        if operation == '+':
            return a + b
        elif operation == '-':
            return a - b
        elif operation == '*':
            return a * b
        elif operation == '/':
            return a / b if b != 0 else "Error: Division by zero"
        else:
            return "Error: Invalid operation"
    ```
    '''
    
    can_process = processor.can_process("test.md", sample_content)
    print(f"¿Puede procesar contenido de ejemplo? {can_process}")
    
    return processor

if __name__ == "__main__":
    test_cline_processor()