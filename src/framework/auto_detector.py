#auto_detector.py
#!/usr/bin/env python3
"""
auto_detector.py - Sistema completo de detección automática de tipos de archivo
Integrado con todos los procesadores IANAE
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Tuple
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoDetector:
    """
    Sistema inteligente de detección automática de tipos de archivo.
    Determina qué procesador usar basándose en el contenido y estructura del archivo.
    """
    
    def __init__(self):
        """Inicializa el auto-detector con todos los patrones de detección"""
        
        # Estadísticas de detección
        self.detection_stats = {
            'files_analyzed': 0,
            'successful_detections': 0,
            'failed_detections': 0,
            'detections_by_type': {},
            'avg_confidence': 0.0,
            'total_confidence': 0.0
        }
        
        # Patrones de detección para cada tipo
        self.detection_patterns = {
            'chatgpt': {
                'file_extensions': ['.json'],
                'required_patterns': ['mapping'],
                'strong_indicators': [
                    'conversation_id', 'create_time', 'update_time', 'title',
                    'author', 'role', 'parts', 'node_id'
                ],
                'structure_checks': ['mapping_structure', 'message_parts'],
                'confidence_threshold': 60,
                'exclusion_patterns': ['chat_messages', 'sender']
            },
            'claude': {
                'file_extensions': ['.json'],
                'required_patterns': ['conversation_id'],
                'strong_indicators': [
                    'chat_messages', 'sender', 'uuid', 'created_at', 'updated_at',
                    'name', 'summary', 'text'
                ],
                'structure_checks': ['chat_messages_array', 'sender_field'],
                'confidence_threshold': 50,
                'exclusion_patterns': ['mapping', 'parts']
            },
            'cline': {
                'file_extensions': ['.md', '.txt'],
                'required_patterns': [],
                'strong_indicators': [
                    'cline task', '## human:', '## assistant:', 'continue dev',
                    'cline conversation', '### user', '### assistant'
                ],
                'structure_checks': ['markdown_headers', 'conversation_markers'],
                'confidence_threshold': 40,
                'exclusion_patterns': ['{', '}', 'conversation_id', 'mapping']
            }
        }
        
        logger.info("AutoDetector inicializado con patrones para ChatGPT, Claude y Cline")
    
    def detect_file_type(self, file_path: str) -> Dict[str, Any]:
        """
        Detecta automáticamente el tipo de archivo y procesador recomendado.
        
        Args:
            file_path: Ruta del archivo a analizar
            
        Returns:
            Diccionario con resultado de detección
        """
        start_time = time.time()
        
        result = {
            'success': False,
            'file_path': file_path,
            'processor': None,
            'confidence': 0.0,
            'file_type': None,
            'file_size': 0,
            'analysis_time': 0.0,
            'details': {},
            'error': None
        }
        
        try:
            # Verificar que el archivo existe
            if not os.path.exists(file_path):
                result['error'] = f"Archivo no encontrado: {file_path}"
                return result
            
            # Información básica del archivo
            file_stat = os.stat(file_path)
            result['file_size'] = file_stat.st_size
            
            # Obtener preview del contenido
            content_preview = self._get_file_preview(file_path, 3000)
            if not content_preview:
                result['error'] = "No se pudo leer el contenido del archivo"
                return result
            
            # Análisis por cada tipo
            detections = {}
            
            for processor_type, patterns in self.detection_patterns.items():
                confidence = self._analyze_file_for_type(
                    file_path, content_preview, processor_type, patterns
                )
                detections[processor_type] = confidence
            
            # Determinar mejor match
            best_match = max(detections.items(), key=lambda x: x[1])
            best_type, best_confidence = best_match
            
            if best_confidence >= self.detection_patterns[best_type]['confidence_threshold']:
                result.update({
                    'success': True,
                    'processor': best_type,
                    'confidence': best_confidence,
                    'file_type': self._determine_file_type(file_path),
                    'details': {
                        'all_confidences': detections,
                        'threshold_met': True,
                        'file_extension': os.path.splitext(file_path)[1].lower()
                    }
                })
                
                self._update_stats(True, best_type, best_confidence)
                logger.debug(f"Detectado {best_type} con confianza {best_confidence:.1f} para {os.path.basename(file_path)}")
                
            else:
                result.update({
                    'success': False,
                    'error': f"Confianza insuficiente (máx: {best_confidence:.1f}, req: {self.detection_patterns[best_type]['confidence_threshold']})",
                    'details': {
                        'all_confidences': detections,
                        'threshold_met': False,
                        'best_guess': best_type
                    }
                })
                
                self._update_stats(False, None, best_confidence)
                logger.warning(f"Detección fallida para {os.path.basename(file_path)}: confianza insuficiente")
            
        except Exception as e:
            result['error'] = f"Error durante detección: {str(e)}"
            self._update_stats(False, None, 0.0)
            logger.error(f"Error detectando tipo de {file_path}: {e}")
        
        result['analysis_time'] = time.time() - start_time
        return result
    
    def _analyze_file_for_type(self, file_path: str, content: str, 
                              processor_type: str, patterns: Dict) -> float:
        """
        Analiza un archivo para un tipo específico de procesador.
        
        Args:
            file_path: Ruta del archivo
            content: Contenido del archivo
            processor_type: Tipo de procesador a evaluar
            patterns: Patrones de detección para este tipo
            
        Returns:
            Puntuación de confianza (0-100)
        """
        confidence_score = 0.0
        content_lower = content.lower()
        
        # 1. Verificar extensión de archivo
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in patterns['file_extensions']:
            confidence_score += 20
        elif file_ext not in ['.json', '.md', '.txt']:
            # Penalizar extensiones no soportadas
            confidence_score -= 30
        
        # 2. Verificar patrones requeridos
        for required_pattern in patterns['required_patterns']:
            if required_pattern.lower() in content_lower:
                confidence_score += 25
            else:
                # Si falta un patrón requerido, penalizar fuertemente
                confidence_score -= 20
        
        # 3. Verificar indicadores fuertes
        strong_matches = 0
        for indicator in patterns['strong_indicators']:
            if indicator.lower() in content_lower:
                strong_matches += 1
                confidence_score += 8
        
        # Bonus por múltiples indicadores fuertes
        if strong_matches >= 3:
            confidence_score += 15
        elif strong_matches >= 5:
            confidence_score += 25
        
        # 4. Verificaciones de estructura específicas
        structure_bonus = self._check_structure(content, processor_type, patterns)
        confidence_score += structure_bonus
        
        # 5. Penalizar patrones de exclusión
        for exclusion_pattern in patterns['exclusion_patterns']:
            if exclusion_pattern.lower() in content_lower:
                confidence_score -= 15
        
        # 6. Análisis específico por tipo
        if processor_type == 'chatgpt':
            confidence_score += self._analyze_chatgpt_specific(content)
        elif processor_type == 'claude':
            confidence_score += self._analyze_claude_specific(content)
        elif processor_type == 'cline':
            confidence_score += self._analyze_cline_specific(content)
        
        return max(0.0, min(100.0, confidence_score))
    
    def _check_structure(self, content: str, processor_type: str, patterns: Dict) -> float:
        """
        Verifica estructura específica del contenido.
        
        Args:
            content: Contenido del archivo
            processor_type: Tipo de procesador
            patterns: Patrones de detección
            
        Returns:
            Bonus de confianza por estructura
        """
        structure_bonus = 0.0
        
        if processor_type == 'chatgpt' and 'mapping_structure' in patterns['structure_checks']:
            # Verificar estructura de mapping de ChatGPT
            try:
                preview_data = json.loads(content[:2000])
                if isinstance(preview_data, (list, dict)):
                    if isinstance(preview_data, list) and len(preview_data) > 0:
                        first_item = preview_data[0]
                    else:
                        first_item = preview_data
                    
                    if isinstance(first_item, dict) and 'mapping' in first_item:
                        mapping = first_item['mapping']
                        if isinstance(mapping, dict) and len(mapping) > 0:
                            # Verificar estructura típica de nodos de ChatGPT
                            first_node = list(mapping.values())[0]
                            if isinstance(first_node, dict) and 'message' in first_node:
                                structure_bonus += 20
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        elif processor_type == 'claude' and 'chat_messages_array' in patterns['structure_checks']:
            # Verificar estructura de chat_messages de Claude
            try:
                preview_data = json.loads(content[:2000])
                if isinstance(preview_data, list) and len(preview_data) > 0:
                    first_item = preview_data[0]
                    if isinstance(first_item, dict) and 'chat_messages' in first_item:
                        chat_messages = first_item['chat_messages']
                        if isinstance(chat_messages, list) and len(chat_messages) > 0:
                            first_msg = chat_messages[0]
                            if isinstance(first_msg, dict) and 'sender' in first_msg and 'text' in first_msg:
                                structure_bonus += 20
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        elif processor_type == 'cline' and 'markdown_headers' in patterns['structure_checks']:
            # Verificar estructura de Markdown de Cline
            lines = content.split('\n')
            header_count = 0
            conversation_markers = 0
            
            for line in lines[:50]:  # Revisar primeras 50 líneas
                line_lower = line.strip().lower()
                
                if line.startswith('#'):
                    header_count += 1
                    if 'cline' in line_lower or 'task' in line_lower:
                        structure_bonus += 5
                
                if (line_lower.startswith('## human') or 
                    line_lower.startswith('## assistant') or
                    line_lower.startswith('### user') or 
                    line_lower.startswith('### assistant')):
                    conversation_markers += 1
                    structure_bonus += 8
            
            # Bonus por estructura coherente
            if header_count > 0 and conversation_markers > 1:
                structure_bonus += 15
        
        return structure_bonus
    
    def _analyze_chatgpt_specific(self, content: str) -> float:
        """Análisis específico para ChatGPT"""
        bonus = 0.0
        content_lower = content.lower()
        
        # Patrones muy específicos de ChatGPT
        chatgpt_specific = [
            'create_time', 'update_time', 'conversation_id',
            'author": {"role"', 'content": {"parts"',
            'parent": null', 'children": []'
        ]
        
        for pattern in chatgpt_specific:
            if pattern in content_lower:
                bonus += 5
        
        # Verificar estructura típica de árbol de conversación
        if 'parent' in content_lower and 'children' in content_lower:
            bonus += 10
        
        # Verificar formato de timestamp típico de ChatGPT
        timestamp_pattern = r'\d{10}\.\d+'  # Formato timestamp de ChatGPT
        if re.search(timestamp_pattern, content):
            bonus += 8
        
        return bonus
    
    def _analyze_claude_specific(self, content: str) -> float:
        """Análisis específico para Claude"""
        bonus = 0.0
        content_lower = content.lower()
        
        # Patrones muy específicos de Claude
        claude_specific = [
            'conversation_id', 'chat_messages', 'sender": "human"',
            'sender": "assistant"', 'uuid', 'created_at', 'updated_at'
        ]
        
        for pattern in claude_specific:
            if pattern in content_lower:
                bonus += 6
        
        # Verificar formato de UUID típico de Claude
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        if re.search(uuid_pattern, content, re.IGNORECASE):
            bonus += 10
        
        # Verificar estructura sender/text típica de Claude
        if '"sender"' in content_lower and '"text"' in content_lower:
            bonus += 8
        
        return bonus
    
    def _analyze_cline_specific(self, content: str) -> float:
        """Análisis específico para Cline"""
        bonus = 0.0
        content_lower = content.lower()
        
        # Patrones muy específicos de Cline
        cline_specific = [
            '# cline task', 'continue dev', 'cline conversation',
            '## human:', '## assistant:', '### user', '### assistant'
        ]
        
        for pattern in cline_specific:
            if pattern in content_lower:
                bonus += 10
        
        # Verificar que no tiene estructura JSON
        if not ('{' in content and '}' in content):
            bonus += 5
        
        # Verificar líneas típicas de conversación Markdown
        lines = content.split('\n')
        conversation_lines = 0
        
        for line in lines:
            line_lower = line.strip().lower()
            if (line_lower.startswith('##') and 
                ('human' in line_lower or 'assistant' in line_lower)):
                conversation_lines += 1
        
        if conversation_lines >= 2:
            bonus += 15
        
        return bonus
    
    def _get_file_preview(self, file_path: str, max_chars: int = 3000) -> str:
        """
        Obtiene preview del archivo para análisis.
        
        Args:
            file_path: Ruta del archivo
            max_chars: Máximo de caracteres a leer
            
        Returns:
            Preview del contenido o string vacío
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read(max_chars)
        except UnicodeDecodeError:
            # Intentar con diferentes encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read(max_chars)
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Error leyendo archivo {file_path}: {e}")
        
        return ""
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determina el tipo básico del archivo por extensión"""
        ext = os.path.splitext(file_path)[1].lower()
        
        type_mapping = {
            '.json': 'JSON',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.csv': 'CSV'
        }
        
        return type_mapping.get(ext, 'Unknown')
    
    def _update_stats(self, success: bool, processor_type: Optional[str], confidence: float):
        """Actualiza estadísticas de detección"""
        self.detection_stats['files_analyzed'] += 1
        
        if success:
            self.detection_stats['successful_detections'] += 1
            if processor_type:
                if processor_type not in self.detection_stats['detections_by_type']:
                    self.detection_stats['detections_by_type'][processor_type] = 0
                self.detection_stats['detections_by_type'][processor_type] += 1
        else:
            self.detection_stats['failed_detections'] += 1
        
        self.detection_stats['total_confidence'] += confidence
        if self.detection_stats['files_analyzed'] > 0:
            self.detection_stats['avg_confidence'] = (
                self.detection_stats['total_confidence'] / 
                self.detection_stats['files_analyzed']
            )
    
    def batch_detect(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Detecta tipos de múltiples archivos de forma eficiente.
        
        Args:
            file_paths: Lista de rutas de archivos
            
        Returns:
            Lista de resultados de detección
        """
        results = []
        start_time = time.time()
        
        logger.info(f"Iniciando detección por lotes de {len(file_paths)} archivos...")
        
        for i, file_path in enumerate(file_paths):
            try:
                result = self.detect_file_type(file_path)
                results.append(result)
                
                # Log progreso cada 50 archivos
                if (i + 1) % 50 == 0:
                    logger.info(f"Detectados {i+1}/{len(file_paths)} archivos...")
                    
            except Exception as e:
                logger.error(f"Error detectando {file_path}: {e}")
                results.append({
                    'success': False,
                    'file_path': file_path,
                    'error': str(e)
                })
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r['success'])
        
        logger.info(f"Detección por lotes completada: {successful}/{len(file_paths)} exitosos "
                   f"en {total_time:.2f}s")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del auto-detector.
        
        Returns:
            Diccionario con estadísticas detalladas
        """
        stats = self.detection_stats.copy()
        
        # Calcular estadísticas adicionales
        if stats['files_analyzed'] > 0:
            stats['success_rate'] = (stats['successful_detections'] / stats['files_analyzed']) * 100
        else:
            stats['success_rate'] = 0.0
        
        # Información sobre patrones
        stats['supported_processors'] = list(self.detection_patterns.keys())
        stats['supported_extensions'] = []
        
        for patterns in self.detection_patterns.values():
            stats['supported_extensions'].extend(patterns['file_extensions'])
        
        stats['supported_extensions'] = list(set(stats['supported_extensions']))
        
        return stats
    
    def reset_statistics(self):
        """Reinicia las estadísticas del detector"""
        self.detection_stats = {
            'files_analyzed': 0,
            'successful_detections': 0,
            'failed_detections': 0,
            'detections_by_type': {},
            'avg_confidence': 0.0,
            'total_confidence': 0.0
        }
        logger.info("Estadísticas del auto-detector reiniciadas")
    
    def get_processor_recommendations(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Obtiene recomendaciones de procesadores para un archivo.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Lista de recomendaciones ordenadas por confianza
        """
        if not os.path.exists(file_path):
            return []
        
        content_preview = self._get_file_preview(file_path, 3000)
        if not content_preview:
            return []
        
        recommendations = []
        
        for processor_type, patterns in self.detection_patterns.items():
            confidence = self._analyze_file_for_type(
                file_path, content_preview, processor_type, patterns
            )
            
            recommendations.append({
                'processor': processor_type,
                'confidence': confidence,
                'threshold': patterns['confidence_threshold'],
                'recommended': confidence >= patterns['confidence_threshold'],
                'file_extensions': patterns['file_extensions']
            })
        
        # Ordenar por confianza descendente
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return recommendations


# Función de utilidad para testing rápido
def test_auto_detector():
    """Función de prueba rápida para el auto-detector"""
    print("🧪 TESTING AutoDetector")
    print("=" * 40)
    
    detector = AutoDetector()
    
    # Crear archivos de prueba
    test_files = {
        "test_chatgpt.json": '''
        [
            {
                "title": "Test Conversation",
                "create_time": 1234567890.123,
                "conversation_id": "test-conv-1",
                "mapping": {
                    "node1": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Hello"]},
                            "create_time": 1234567890.123
                        },
                        "parent": null,
                        "children": ["node2"]
                    }
                }
            }
        ]
        ''',
        
        "test_claude.json": '''
        [
            {
                "conversation_id": "conv-abc-123",
                "name": "Test Claude Chat",
                "created_at": "2024-01-01T10:00:00Z",
                "chat_messages": [
                    {
                        "uuid": "msg-abc-123",
                        "sender": "human",
                        "text": "Hello Claude",
                        "created_at": "2024-01-01T10:00:00Z"
                    },
                    {
                        "uuid": "msg-def-456", 
                        "sender": "assistant",
                        "text": "Hello! How can I help?",
                        "created_at": "2024-01-01T10:01:00Z"
                    }
                ]
            }
        ]
        ''',
        
        "test_cline.md": '''
        # Cline Task: Test Conversation
        
        ## Human:
        Hello, I need help with Python.
        
        ## Assistant:
        I'd be happy to help you with Python! What specific question do you have?
        
        ## Human:
        How do I create a list?
        
        ## Assistant:
        You can create a list in Python using square brackets:
        
        ```python
        my_list = [1, 2, 3, 4, 5]
        empty_list = []
        ```
        '''
    }
    
    # Crear archivos temporales y probar detección
    for filename, content in test_files.items():
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Detectar tipo
        result = detector.detect_file_type(filename)
        
        print(f"\n📁 {filename}:")
        print(f"   Éxito: {result['success']}")
        print(f"   Procesador: {result.get('processor', 'N/A')}")
        print(f"   Confianza: {result.get('confidence', 0):.1f}")
        print(f"   Tipo: {result.get('file_type', 'N/A')}")
        
        if not result['success']:
            print(f"   Error: {result.get('error', 'N/A')}")
        
        # Obtener recomendaciones
        recommendations = detector.get_processor_recommendations(filename)
        print(f"   Recomendaciones:")
        for rec in recommendations:
            status = "✅" if rec['recommended'] else "❌"
            print(f"     {status} {rec['processor']}: {rec['confidence']:.1f}")
        
        # Limpiar archivo
        os.remove(filename)
    
    # Mostrar estadísticas
    stats = detector.get_statistics()
    print(f"\n📊 Estadísticas del detector:")
    print(f"   Archivos analizados: {stats['files_analyzed']}")
    print(f"   Detecciones exitosas: {stats['successful_detections']}")
    print(f"   Tasa de éxito: {stats['success_rate']:.1f}%")
    print(f"   Confianza promedio: {stats['avg_confidence']:.1f}")
    print(f"   Procesadores soportados: {stats['supported_processors']}")
    print(f"   Extensiones soportadas: {stats['supported_extensions']}")
    
    print("\n✅ Test del auto-detector completado")
    
    return detector

if __name__ == "__main__":
    test_auto_detector()