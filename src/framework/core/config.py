# Configuration management 
#!/usr/bin/env python3
"""
IANAE Core Configuration Management
Gestión centralizada de configuración con soporte para YAML y variables de entorno
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    path: str = "data/databases/ianae.db"
    backup_path: str = "data/databases/ianae_backup.db"
    backup_interval: int = 3600  # segundos
    connection_timeout: int = 30
    max_connections: int = 10
    enable_wal: bool = True


@dataclass 
class LLMConfig:
    """Configuración de LLM"""
    provider: str = "lmstudio"
    endpoint: str = "http://localhost:1234/v1"
    model: str = "local-model"
    timeout: int = 60
    max_tokens: int = 1000
    temperature: float = 0.7
    max_context_length: int = 8000
    api_key: Optional[str] = None


@dataclass
class WebConfig:
    """Configuración web"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


@dataclass
class ProcessingConfig:
    """Configuración de procesamiento"""
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    supported_formats: list = None
    batch_size: int = 100
    worker_threads: int = 4
    temp_dir: str = "data/uploads"
    processed_dir: str = "data/processed"
    enable_deduplication: bool = True
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.json', '.md', '.txt', '.pdf', '.docx']


@dataclass
class CacheConfig:
    """Configuración de caché"""
    enabled: bool = True
    cache_dir: str = "data/cache"
    max_size_mb: int = 500
    ttl_seconds: int = 3600
    cleanup_interval: int = 1800


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    level: str = "INFO"
    log_dir: str = "data/logs"
    max_file_size: str = "10MB"
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True
    enable_console_logging: bool = True


class ConfigManager:
    """
    Gestor centralizado de configuración para IANAE
    
    Carga configuración desde:
    1. Archivos YAML (config/)
    2. Variables de entorno 
    3. Valores por defecto
    """
    
    def __init__(self, config_dir: str = "config", environment: str = None):
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("IANAE_ENV", "development")
        
        # Configuraciones por categoría
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.web = WebConfig()
        self.processing = ProcessingConfig()
        self.cache = CacheConfig()
        self.logging = LoggingConfig()
        
        # Cargar configuración
        self._load_configuration()
        self._apply_environment_overrides()
        self._validate_configuration()
    
    def _load_configuration(self):
        """Carga configuración desde archivos YAML"""
        try:
            # Cargar configuración base
            default_config = self._load_yaml_file("default.yaml")
            if default_config:
                self._apply_config_dict(default_config)
                logger.info("✅ Configuración por defecto cargada")
            
            # Cargar configuración específica del entorno
            env_config = self._load_yaml_file(f"{self.environment}.yaml")
            if env_config:
                self._apply_config_dict(env_config)
                logger.info(f"✅ Configuración de {self.environment} cargada")
            
        except Exception as e:
            logger.warning(f"⚠️ Error cargando configuración YAML: {e}")
            logger.info("📋 Usando configuración por defecto")
    
    def _load_yaml_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Carga un archivo YAML específico"""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            logger.debug(f"📁 Archivo de configuración no encontrado: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.debug(f"📖 Cargado: {file_path}")
                return config
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parseando YAML {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error leyendo archivo {file_path}: {e}")
            return None
    
    def _apply_config_dict(self, config_dict: Dict[str, Any]):
        """Aplica configuración desde diccionario a dataclasses"""
        if not config_dict:
            return
        
        # Mapear secciones a dataclasses
        section_mapping = {
            'database': self.database,
            'llm': self.llm,
            'web': self.web,
            'processing': self.processing,
            'cache': self.cache,
            'logging': self.logging
        }
        
        for section_name, section_data in config_dict.items():
            if section_name in section_mapping and isinstance(section_data, dict):
                config_obj = section_mapping[section_name]
                
                # Actualizar atributos que existen en el dataclass
                for key, value in section_data.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
                        logger.debug(f"🔧 {section_name}.{key} = {value}")
    
    def _apply_environment_overrides(self):
        """Aplica variables de entorno como overrides"""
        env_mappings = {
            # Database
            'IANAE_DB_PATH': ('database', 'path'),
            'IANAE_DB_BACKUP_INTERVAL': ('database', 'backup_interval'),
            
            # LLM
            'IANAE_LLM_PROVIDER': ('llm', 'provider'),
            'IANAE_LLM_ENDPOINT': ('llm', 'endpoint'),
            'IANAE_LLM_MODEL': ('llm', 'model'),
            'IANAE_LLM_TIMEOUT': ('llm', 'timeout'),
            'IANAE_LLM_API_KEY': ('llm', 'api_key'),
            
            # Web
            'IANAE_WEB_HOST': ('web', 'host'),
            'IANAE_WEB_PORT': ('web', 'port'),
            'IANAE_WEB_DEBUG': ('web', 'debug'),
            
            # Processing
            'IANAE_MAX_FILE_SIZE': ('processing', 'max_file_size'),
            'IANAE_WORKER_THREADS': ('processing', 'worker_threads'),
            
            # Cache
            'IANAE_CACHE_ENABLED': ('cache', 'enabled'),
            'IANAE_CACHE_TTL': ('cache', 'ttl_seconds'),
            
            # Logging
            'IANAE_LOG_LEVEL': ('logging', 'level'),
            'IANAE_LOG_DIR': ('logging', 'log_dir'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                config_obj = getattr(self, section)
                
                # Convertir tipo apropiadamente
                current_value = getattr(config_obj, key)
                if isinstance(current_value, bool):
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(current_value, int):
                    env_value = int(env_value)
                elif isinstance(current_value, float):
                    env_value = float(env_value)
                
                setattr(config_obj, key, env_value)
                logger.debug(f"🌍 ENV override: {section}.{key} = {env_value}")
    
    def _validate_configuration(self):
        """Valida la configuración cargada"""
        errors = []
        
        # Validar rutas de directorio
        directories_to_check = [
            (self.database.path, "directorio de base de datos"),
            (self.processing.temp_dir, "directorio temporal"),
            (self.processing.processed_dir, "directorio de procesados"),
            (self.cache.cache_dir, "directorio de caché"),
            (self.logging.log_dir, "directorio de logs")
        ]
        
        for dir_path, description in directories_to_check:
            dir_path = Path(dir_path).parent if dir_path.endswith('.db') else Path(dir_path)
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 Creado {description}: {dir_path}")
                except Exception as e:
                    errors.append(f"No se pudo crear {description}: {dir_path} - {e}")
        
        # Validar configuración LLM
        if self.llm.timeout <= 0:
            errors.append("LLM timeout debe ser mayor a 0")
        
        if self.llm.max_tokens <= 0:
            errors.append("LLM max_tokens debe ser mayor a 0")
        
        # Validar configuración web
        if not (1 <= self.web.port <= 65535):
            errors.append("Puerto web debe estar entre 1 y 65535")
        
        # Validar configuración de procesamiento
        if self.processing.max_file_size <= 0:
            errors.append("Tamaño máximo de archivo debe ser mayor a 0")
        
        if self.processing.worker_threads <= 0:
            errors.append("Número de worker threads debe ser mayor a 0")
        
        # Reportar errores
        if errors:
            error_msg = "❌ Errores de configuración:\n" + "\n".join(f"  • {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError("Configuración inválida")
        else:
            logger.info("✅ Configuración validada correctamente")
    
    def get_full_config(self) -> Dict[str, Any]:
        """Retorna toda la configuración como diccionario"""
        return {
            'database': self.database.__dict__,
            'llm': self.llm.__dict__,
            'web': self.web.__dict__,
            'processing': self.processing.__dict__,
            'cache': self.cache.__dict__,
            'logging': self.logging.__dict__,
            'environment': self.environment
        }
    
    def save_config_to_file(self, filepath: str = None):
        """Guarda la configuración actual a un archivo YAML"""
        if filepath is None:
            filepath = self.config_dir / f"current_{self.environment}.yaml"
        
        try:
            config_dict = self.get_full_config()
            # Remover environment del dict para el archivo
            config_dict.pop('environment', None)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"💾 Configuración guardada en: {filepath}")
        except Exception as e:
            logger.error(f"❌ Error guardando configuración: {e}")
    
    def reload_configuration(self):
        """Recarga la configuración desde archivos"""
        logger.info("🔄 Recargando configuración...")
        
        # Resetear a valores por defecto
        self.__init__(str(self.config_dir), self.environment)
        
        logger.info("✅ Configuración recargada")
    
    def __str__(self) -> str:
        """Representación string de la configuración"""
        return f"IANAEConfig(env={self.environment}, db={self.database.path})"
    
    def __repr__(self) -> str:
        return self.__str__()


# Instancia global de configuración
config = ConfigManager()


def get_config() -> ConfigManager:
    """
    Obtiene la instancia global de configuración
    
    Returns:
        ConfigManager: Instancia de configuración
    """
    return config


def reload_config():
    """Recarga la configuración global"""
    global config
    config.reload_configuration()


# Funciones de conveniencia para acceso rápido
def get_db_config() -> DatabaseConfig:
    """Obtiene configuración de base de datos"""
    return config.database


def get_llm_config() -> LLMConfig:
    """Obtiene configuración de LLM"""
    return config.llm


def get_web_config() -> WebConfig:
    """Obtiene configuración web"""
    return config.web


def get_processing_config() -> ProcessingConfig:
    """Obtiene configuración de procesamiento"""
    return config.processing


if __name__ == "__main__":
    # Test básico del sistema de configuración
    print("🧪 TESTING IANAE CONFIG SYSTEM")
    print("=" * 40)
    
    try:
        # Mostrar configuración actual
        print(f"📍 Entorno: {config.environment}")
        print(f"📁 Base de datos: {config.database.path}")
        print(f"🤖 LLM Provider: {config.llm.provider}")
        print(f"🌐 Web: {config.web.host}:{config.web.port}")
        print(f"⚙️ Workers: {config.processing.worker_threads}")
        
        # Guardar configuración actual
        config.save_config_to_file("test_config.yaml")
        
        # Mostrar configuración completa
        print("\n📋 Configuración completa:")
        import json
        print(json.dumps(config.get_full_config(), indent=2, default=str))
        
        print("\n✅ Sistema de configuración funcionando correctamente")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()