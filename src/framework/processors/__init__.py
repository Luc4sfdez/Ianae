#!/usr/bin/env python3
"""
processors/__init__.py - Módulo de Procesadores IANAE
Exporta todos los procesadores especializados y componentes base
"""

from .base import BaseProcessor, ProcessingError, load_file_safely, load_json_safely, get_file_preview, validate_file_path
from .chatgpt import ChatGPTProcessor
from .claude import ClaudeProcessor
from .cline import ClineProcessor

__version__ = "4.0.0"
__author__ = "Lucas - IANAE System"

# Exports principales
__all__ = [
    # Clase base
    'BaseProcessor',
    'ProcessingError',
    
    # Procesadores especializados
    'ChatGPTProcessor',
    'ClaudeProcessor', 
    'ClineProcessor',
    
    # Funciones de utilidad
    'load_file_safely',
    'load_json_safely',
    'get_file_preview',
    'validate_file_path',
    
    # Registry de procesadores
    'get_all_processors',
    'get_processor_by_name',
    'get_supported_formats'
]

# Registry de procesadores disponibles
AVAILABLE_PROCESSORS = {
    'chatgpt': ChatGPTProcessor,
    'claude': ClaudeProcessor,
    'cline': ClineProcessor
}

def get_all_processors():
    """
    Obtiene instancias de todos los procesadores disponibles.
    
    Returns:
        Dict con nombre -> instancia de procesador
    """
    return {name: processor_class() for name, processor_class in AVAILABLE_PROCESSORS.items()}

def get_processor_by_name(name: str):
    """
    Obtiene un procesador específico por nombre.
    
    Args:
        name: Nombre del procesador ('chatgpt', 'claude', 'cline')
        
    Returns:
        Instancia del procesador o None si no existe
    """
    if name in AVAILABLE_PROCESSORS:
        return AVAILABLE_PROCESSORS[name]()
    return None

def get_supported_formats():
    """
    Obtiene todos los formatos soportados por los procesadores.
    
    Returns:
        Set con todas las extensiones soportadas
    """
    formats = set()
    for processor_class in AVAILABLE_PROCESSORS.values():
        processor = processor_class()
        formats.update(processor.supported_formats)
    return formats

def get_processors_info():
    """
    Obtiene información detallada de todos los procesadores.
    
    Returns:
        Dict con información de cada procesador
    """
    info = {}
    for name, processor_class in AVAILABLE_PROCESSORS.items():
        processor = processor_class()
        info[name] = {
            'name': processor.name,
            'supported_formats': processor.supported_formats,
            'description': processor.__doc__ or f"Procesador para {name}",
            'version': getattr(processor, 'version', '1.0.0')
        }
    return info

# Información del módulo
MODULE_INFO = {
    'name': 'IANAE Processors',
    'version': __version__,
    'author': __author__,
    'description': 'Procesadores especializados para conversaciones de ChatGPT, Claude y Cline',
    'processors_count': len(AVAILABLE_PROCESSORS),
    'supported_formats': list(get_supported_formats())
}

def get_module_info():
    """Obtiene información del módulo de procesadores"""
    return MODULE_INFO.copy()
