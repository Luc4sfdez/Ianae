#!/usr/bin/env python3
"""
core/manager.py - Manager Principal IANAE Completamente Integrado
Versión corregida que integra TODOS los componentes del sistema
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Imports ajustados para la estructura REAL de tu carpeta
from .database import IANAEDatabase, create_database

# Import del auto-detector (está en el nivel superior)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Los archivos están directamente en la carpeta, no en subcarpetas
from auto_detector import AutoDetector
from chatgpt import ChatGPTProcessor
from claude import ClaudeProcessor  
from cline import ClineProcessor

# Clase base está en base.py
try:
    from base import BaseProcessor, ProcessingError
except ImportError:
    # Crear una clase base mínima si no existe
    class ProcessingError(Exception):
        pass
    
    class BaseProcessor:
        def __init__(self, name):
            self.name = name
            self.stats = {'files_processed': 0, 'conversations_extracted': 0, 'messages_extracted': 0, 'errors_encountered': 0, 'processing_time_total': 0.0}
        
        def update_stats(self, conversations_processed, messages_processed, processing_time, errors=0):
            self.stats['files_processed'] += 1
            self.stats['conversations_extracted'] += conversations_processed
            self.stats['messages_extracted'] += messages_processed
            self.stats['errors_encountered'] += errors
            self.stats['processing_time_total'] += processing_time
        
        def get_stats(self):
            return self.stats.copy()
        
        def reset_stats(self):
            self.stats = {'files_processed': 0, 'conversations_extracted': 0, 'messages_extracted': 0, 'errors_encountered': 0, 'processing_time_total': 0.0}

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IANAECore:
    """
    Sistema Principal IANAE - Versión Completamente Integrada
    
    Orquesta TODOS los componentes:
    - AutoDetector para identificación automática de tipos
    - Procesadores especializados (ChatGPT, Claude, Cline) 
    - Base de datos SQLite optimizada con deduplicación
    - Estadísticas completas y gestión de archivos
    """
    
    def __init__(self, db_path: str = "ianae_memoria.db"):
        """
        Inicializa el sistema IANAE completo.
        
        Args:
            db_path: Ruta de la base de datos SQLite
        """
        self.db_path = db_path
        
        # Inicializar componentes principales
        logger.info(f"🧠 Inicializando IANAE Core con DB: {db_path}")
        
        # 1. Base de datos
        self.database = IANAEDatabase(db_path)
        logger.info("✅ Base de datos inicializada")
        
        # 2. Auto-detector
        self.detector = AutoDetector()
        logger.info("✅ Auto-detector inicializado")
        
        # 3. Procesadores especializados
        self.processors = {
            'chatgpt': ChatGPTProcessor(),
            'claude': ClaudeProcessor(),
            'cline': ClineProcessor()
        }
        logger.info(f"✅ Procesadores inicializados: {list(self.processors.keys())}")
        
        # 4. Estadísticas del sistema
        self.system_stats = {
            'files_processed': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'processing_time_total': 0.0,
            'errors_encountered': 0,
            'files_skipped': 0,
            'last_processing': None
        }
        
        logger.info("🚀 IANAE Core completamente inicializado")
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Procesa un archivo individual con auto-detección y procesador especializado.
        
        Args:
            file_path: Ruta del archivo a procesar
            
        Returns:
            Resultado completo del procesamiento
        """
        start_time = time.time()
        
        result = {
            'success': False,
            'filename': os.path.basename(file_path),
            'file_path': file_path,
            'detected_type': None,
            'processor_used': None,
            'stats': {},
            'processing_time': 0.0,
            'error': None,
            'conversations_added': 0,
            'messages_added': 0,
            'file_already_processed': False
        }
        
        try:
            logger.info(f"📄 Procesando archivo: {os.path.basename(file_path)}")
            
            # 1. Verificar si ya fue procesado
            is_processed, file_info = self.database.is_file_processed(file_path)
            if is_processed and not file_info.get('file_changed', False):
                result.update({
                    'success': True,
                    'file_already_processed': True,
                    'detected_type': file_info.get('processor_used', 'unknown'),
                    'processing_time': time.time() - start_time,
                    'message': 'Archivo ya procesado previamente'
                })
                self.system_stats['files_skipped'] += 1
                return result
            
            # 2. Auto-detección del tipo
            detection_result = self.detector.detect_file_type(file_path)
            
            if not detection_result['success']:
                result.update({
                    'error': f"Auto-detección falló: {detection_result.get('error', 'Tipo no soportado')}",
                    'processing_time': time.time() - start_time
                })
                self.system_stats['errors_encountered'] += 1
                return result
            
            detected_type = detection_result['processor']
            result['detected_type'] = detected_type
            
            # 3. Obtener procesador especializado
            if detected_type not in self.processors:
                result.update({
                    'error': f"Procesador no disponible para tipo: {detected_type}",
                    'processing_time': time.time() - start_time
                })
                self.system_stats['errors_encountered'] += 1
                return result
            
            processor = self.processors[detected_type]
            result['processor_used'] = detected_type
            
            # 4. Procesar con el procesador especializado
            logger.info(f"🔧 Usando procesador {detected_type} con confianza {detection_result['confidence']:.1f}%")
            
            conversaciones = processor.process_file(file_path)
            
            if not conversaciones:
                result.update({
                    'success': True,
                    'message': 'Archivo procesado pero sin conversaciones extraídas',
                    'processing_time': time.time() - start_time,
                    'stats': {
                        'total_conversations': 0,
                        'total_messages': 0
                    }
                })
                return result
            
            # 5. Guardar en base de datos
            db_stats = self.database.add_conversations_batch(conversaciones)
            
            # 6. Registrar procesamiento del archivo
            processing_stats = {
                'conversations_processed': len(conversaciones),
                'messages_processed': sum(len(conv['mensajes']) for conv in conversaciones),
                'processing_time': time.time() - start_time
            }
            
            self.database.register_file_processing(file_path, detected_type, processing_stats)
            
            # 7. Actualizar resultado
            result.update({
                'success': True,
                'conversations_added': db_stats['conversations_added'],
                'messages_added': db_stats['messages_added'],
                'processing_time': time.time() - start_time,
                'stats': {
                    'total_conversations': len(conversaciones),
                    'total_messages': processing_stats['messages_processed'],
                    'conversations_new': db_stats['conversations_added'],
                    'conversations_updated': db_stats['conversations_updated'],
                    'conversations_skipped': db_stats['conversations_skipped'],
                    'detection_confidence': detection_result['confidence']
                }
            })
            
            # 8. Actualizar estadísticas del sistema
            self._update_system_stats(processing_stats, True)
            
            logger.info(f"✅ Archivo procesado: {result['conversations_added']} conversaciones, "
                       f"{result['messages_added']} mensajes en {result['processing_time']:.2f}s")
            
        except ProcessingError as e:
            result.update({
                'error': f"Error de procesamiento: {str(e)}",
                'processing_time': time.time() - start_time
            })
            self._update_system_stats({'processing_time': time.time() - start_time}, False)
            logger.error(f"❌ Error procesando {file_path}: {e}")
            
        except Exception as e:
            result.update({
                'error': f"Error inesperado: {str(e)}",
                'processing_time': time.time() - start_time
            })
            self._update_system_stats({'processing_time': time.time() - start_time}, False)
            logger.error(f"💥 Error crítico procesando {file_path}: {e}")
        
        return result
    
    def process_directory(self, directory_path: str, extensions: List[str] = None, 
                         max_files: int = 100, recursive: bool = True) -> Dict[str, Any]:
        """
        Procesa un directorio completo de archivos.
        
        Args:
            directory_path: Ruta del directorio
            extensions: Extensiones a procesar (default: ['.json', '.md', '.txt'])
            max_files: Máximo número de archivos a procesar
            recursive: Si buscar recursivamente en subdirectorios
            
        Returns:
            Estadísticas completas del procesamiento por lotes
        """
        start_time = time.time()
        
        if extensions is None:
            extensions = ['.json', '.md', '.txt']
        
        result = {
            'success': False,
            'directory': directory_path,
            'files_found': 0,
            'files_processed': 0,
            'files_skipped': 0,
            'files_errors': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'processing_time': 0.0,
            'detailed_results': [],
            'error': None
        }
        
        try:
            if not os.path.exists(directory_path):
                result['error'] = f"Directorio no encontrado: {directory_path}"
                return result
            
            logger.info(f"📂 Procesando directorio: {directory_path}")
            logger.info(f"🔍 Extensiones: {extensions}, Máx archivos: {max_files}")
            
            # Encontrar archivos
            files_to_process = []
            
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensions):
                            files_to_process.append(os.path.join(root, file))
                            if len(files_to_process) >= max_files:
                                break
                    if len(files_to_process) >= max_files:
                        break
            else:
                for file in os.listdir(directory_path):
                    if os.path.isfile(os.path.join(directory_path, file)):
                        if any(file.lower().endswith(ext) for ext in extensions):
                            files_to_process.append(os.path.join(directory_path, file))
                            if len(files_to_process) >= max_files:
                                break
            
            result['files_found'] = len(files_to_process)
            
            if not files_to_process:
                result.update({
                    'success': True,
                    'processing_time': time.time() - start_time,
                    'message': 'No se encontraron archivos compatibles'
                })
                return result
            
            logger.info(f"📊 Encontrados {len(files_to_process)} archivos para procesar")
            
            # Procesar archivos uno por uno
            for i, file_path in enumerate(files_to_process):
                try:
                    logger.info(f"📄 Procesando {i+1}/{len(files_to_process)}: {os.path.basename(file_path)}")
                    
                    file_result = self.process_file(file_path)
                    
                    # Agregar a resultados detallados
                    result['detailed_results'].append({
                        'filename': os.path.basename(file_path),
                        'success': file_result['success'],
                        'detected_type': file_result.get('detected_type'),
                        'conversations': file_result.get('conversations_added', 0),
                        'messages': file_result.get('messages_added', 0),
                        'processing_time': file_result.get('processing_time', 0),
                        'error': file_result.get('error'),
                        'already_processed': file_result.get('file_already_processed', False)
                    })
                    
                    # Actualizar contadores
                    if file_result['success']:
                        result['files_processed'] += 1
                        result['total_conversations'] += file_result.get('conversations_added', 0)
                        result['total_messages'] += file_result.get('messages_added', 0)
                        
                        if file_result.get('file_already_processed'):
                            result['files_skipped'] += 1
                    else:
                        result['files_errors'] += 1
                    
                    # Log progreso cada 10 archivos
                    if (i + 1) % 10 == 0:
                        logger.info(f"📈 Progreso: {i+1}/{len(files_to_process)} archivos, "
                                   f"{result['total_conversations']} conversaciones")
                
                except Exception as e:
                    logger.error(f"❌ Error procesando {file_path}: {e}")
                    result['files_errors'] += 1
                    result['detailed_results'].append({
                        'filename': os.path.basename(file_path),
                        'success': False,
                        'error': str(e)
                    })
            
            # Finalizar resultado
            result.update({
                'success': True,
                'processing_time': time.time() - start_time
            })
            
            logger.info(f"🎉 Directorio procesado: {result['files_processed']} archivos, "
                       f"{result['total_conversations']} conversaciones, "
                       f"{result['total_messages']} mensajes en {result['processing_time']:.2f}s")
            
        except Exception as e:
            result.update({
                'error': f"Error procesando directorio: {str(e)}",
                'processing_time': time.time() - start_time
            })
            logger.error(f"💥 Error crítico en directorio {directory_path}: {e}")
        
        return result
    
    def search_conversations(self, query: str, platform: str = None, 
                           limit: int = 50, date_from: str = None, 
                           date_to: str = None) -> List[Dict[str, Any]]:
        """
        Busca conversaciones en la base de datos.
        
        Args:
            query: Texto a buscar
            platform: Filtrar por plataforma (chatgpt, claude, cline)
            limit: Máximo número de resultados
            date_from: Fecha inicio (YYYY-MM-DD)
            date_to: Fecha fin (YYYY-MM-DD)
            
        Returns:
            Lista de conversaciones que coinciden
        """
        try:
            logger.info(f"🔍 Buscando: '{query}' en plataforma: {platform or 'todas'}")
            
            results = self.database.search_conversations(
                query=query,
                platform=platform,
                date_from=date_from,
                date_to=date_to,
                limit=limit
            )
            
            logger.info(f"📊 Encontrados {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            return []
    
    def get_conversation_details(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles completos de una conversación.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Conversación completa con mensajes o None
        """
        try:
            return self.database.get_conversation_details(conversation_id)
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversación {conversation_id}: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas completas del sistema.
        
        Returns:
            Diccionario con estadísticas de base de datos, procesadores y auto-detector
        """
        try:
            # Estadísticas de base de datos
            db_stats = self.database.get_statistics()
            
            # Estadísticas de procesadores
            processor_stats = {}
            for name, processor in self.processors.items():
                processor_stats[name] = processor.get_stats()
            
            # Estadísticas del auto-detector
            detector_stats = self.detector.get_statistics()
            
            # Estadísticas del sistema
            system_stats = self.system_stats.copy()
            system_stats['last_updated'] = datetime.now().isoformat()
            
            return {
                'database': db_stats,
                'processors': processor_stats,
                'auto_detector': detector_stats,
                'system': system_stats,
                'summary': {
                    'total_conversations': db_stats.get('total_conversations', 0),
                    'total_messages': db_stats.get('total_messages', 0),
                    'total_files_processed': system_stats['files_processed'],
                    'supported_platforms': list(self.processors.keys()),
                    'database_file': self.db_path
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {
                'error': str(e),
                'summary': {
                    'total_conversations': 0,
                    'total_messages': 0,
                    'total_files_processed': 0
                }
            }
    
    def cleanup_database(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Limpia la base de datos eliminando duplicados y datos corruptos.
        
        Args:
            dry_run: Si True, solo reporta qué se eliminaría
            
        Returns:
            Estadísticas de la limpieza
        """
        try:
            logger.info(f"🧹 Limpieza de base de datos (dry_run={dry_run})")
            result = self.database.cleanup_database(dry_run=dry_run)
            logger.info(f"✅ Limpieza completada: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            return {'error': str(e)}
    
    def export_conversations(self, output_path: str, format: str = 'json',
                           platform: str = None, query: str = None) -> Dict[str, Any]:
        """
        Exporta conversaciones en el formato especificado.
        
        Args:
            output_path: Ruta del archivo de salida
            format: Formato de exportación ('json', 'csv', 'txt')
            platform: Filtrar por plataforma
            query: Filtrar por búsqueda
            
        Returns:
            Resultado de la exportación
        """
        try:
            logger.info(f"📤 Exportando conversaciones a {output_path} (formato: {format})")
            
            # Buscar conversaciones según filtros
            conversations = self.search_conversations(
                query=query or "",
                platform=platform,
                limit=10000  # Exportar todas las que coincidan
            )
            
            if not conversations:
                return {
                    'success': False,
                    'error': 'No se encontraron conversaciones para exportar'
                }
            
            # Obtener detalles completos si es necesario
            if format in ['json', 'txt']:
                detailed_conversations = []
                for conv in conversations:
                    details = self.get_conversation_details(conv['id'])
                    if details:
                        detailed_conversations.append(details)
                conversations = detailed_conversations
            
            # Exportar según formato
            if format == 'json':
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, indent=2, ensure_ascii=False)
            
            elif format == 'csv':
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Título', 'Plataforma', 'Fecha', 'Mensajes'])
                    for conv in conversations:
                        writer.writerow([
                            conv['id'],
                            conv['title'],
                            conv['platform'],
                            conv.get('created_at', ''),
                            conv.get('total_messages', 0)
                        ])
            
            elif format == 'txt':
                with open(output_path, 'w', encoding='utf-8') as f:
                    for conv in conversations:
                        f.write(f"=== {conv['title']} ===\n")
                        f.write(f"ID: {conv['id']}\n")
                        f.write(f"Plataforma: {conv['platform']}\n")
                        f.write(f"Fecha: {conv.get('created_at', 'N/A')}\n\n")
                        
                        for msg in conv.get('messages', []):
                            f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")
                        
                        f.write("\n" + "="*50 + "\n\n")
            
            result = {
                'success': True,
                'output_path': output_path,
                'format': format,
                'conversations_exported': len(conversations),
                'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
            }
            
            logger.info(f"✅ Exportación completada: {result['conversations_exported']} conversaciones")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en exportación: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_processor_info(self, processor_name: str = None) -> Dict[str, Any]:
        """
        Obtiene información detallada de procesadores.
        
        Args:
            processor_name: Nombre específico del procesador o None para todos
            
        Returns:
            Información de procesadores
        """
        try:
            if processor_name:
                if processor_name in self.processors:
                    return self.processors[processor_name].get_processor_info()
                else:
                    return {'error': f'Procesador {processor_name} no encontrado'}
            else:
                return {name: proc.get_processor_info() 
                       for name, proc in self.processors.items()}
        except Exception as e:
            logger.error(f"❌ Error obteniendo info de procesadores: {e}")
            return {'error': str(e)}
    
    def reset_system_stats(self):
        """Reinicia las estadísticas del sistema"""
        self.system_stats = {
            'files_processed': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'processing_time_total': 0.0,
            'errors_encountered': 0,
            'files_skipped': 0,
            'last_processing': None
        }
        
        # También reiniciar estadísticas de componentes
        for processor in self.processors.values():
            processor.reset_stats()
        
        self.detector.reset_statistics()
        
        logger.info("🔄 Estadísticas del sistema reiniciadas")
    
    def _update_system_stats(self, processing_stats: Dict, success: bool):
        """Actualiza estadísticas internas del sistema"""
        self.system_stats['files_processed'] += 1
        self.system_stats['processing_time_total'] += processing_stats.get('processing_time', 0)
        self.system_stats['last_processing'] = datetime.now().isoformat()
        
        if success:
            self.system_stats['total_conversations'] += processing_stats.get('conversations_processed', 0)
            self.system_stats['total_messages'] += processing_stats.get('messages_processed', 0)
        else:
            self.system_stats['errors_encountered'] += 1
    
    def close(self):
        """Cierra el sistema y libera recursos"""
        try:
            self.database.close()
            logger.info("🔐 Sistema IANAE cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando sistema: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def __str__(self) -> str:
        """Representación string del sistema"""
        stats = self.get_statistics()
        return (f"<IANAECore(db='{self.db_path}', "
                f"conversations={stats['summary']['total_conversations']}, "
                f"processors={len(self.processors)})>")


# Funciones de utilidad

def create_ianae_system(db_path: str = "ianae_memoria.db", 
                       db_config: Optional[Dict] = None) -> IANAECore:
    """
    Crea una nueva instancia del sistema IANAE completo.
    
    Args:
        db_path: Ruta de la base de datos
        db_config: Configuración adicional (no usado actualmente)
        
    Returns:
        Instancia completa de IANAECore
    """
    logger.info(f"🏗️ Creando sistema IANAE completo con DB: {db_path}")
    return IANAECore(db_path)

def get_system_info() -> Dict[str, Any]:
    """
    Obtiene información general del sistema IANAE.
    
    Returns:
        Información del sistema y componentes disponibles
    """
    return {
        'version': '4.0.0',
        'components': {
            'auto_detector': 'Sistema inteligente de detección de tipos',
            'processors': {
                'chatgpt': 'Procesador para exportaciones JSON de ChatGPT',
                'claude': 'Procesador para exportaciones JSON de Claude',
                'cline': 'Procesador para archivos Markdown de Cline/Continue'
            },
            'database': 'Base de datos SQLite optimizada con deduplicación',
            'manager': 'Orquestador principal del sistema'
        },
        'supported_formats': ['.json', '.md', '.txt'],
        'features': [
            'Auto-detección de tipos de archivo',
            'Procesamiento especializado por plataforma',
            'Deduplicación automática',
            'Búsqueda full-text',
            'Exportación en múltiples formatos',
            'Estadísticas detalladas',
            'Procesamiento por lotes',
            'Limpieza de base de datos'
        ]
    }


# Testing rápido del sistema integrado
def test_integrated_system():
    """Función de prueba del sistema completamente integrado"""
    print("🧪 TESTING Sistema IANAE Integrado")
    print("=" * 50)
    
    # Crear sistema de prueba
    with IANAECore("test_integrated.db") as ianae:
        print(f"Sistema creado: {ianae}")
        
        # Obtener estadísticas iniciales
        stats = ianae.get_statistics()
        print(f"Estadísticas iniciales: {stats['summary']}")
        
        # Información de procesadores
        proc_info = ianae.get_processor_info()
        print(f"Procesadores disponibles: {list(proc_info.keys())}")
        
        # Información del sistema
        system_info = get_system_info()
        print(f"Versión del sistema: {system_info['version']}")
        print(f"Formatos soportados: {system_info['supported_formats']}")
    
    # Limpiar archivo de prueba
    if os.path.exists("test_integrated.db"):
        os.remove("test_integrated.db")
    
    print("✅ Test del sistema integrado completado")

if __name__ == "__main__":
    test_integrated_system()