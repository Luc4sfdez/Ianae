"""
Logging estructurado para Orchestra
Formato JSON para fácil parsing y análisis
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """
    Formateador que produce logs en JSON estructurado.

    Ejemplo de output:
    {
        "timestamp": "2026-02-10T17:30:45.123456",
        "level": "INFO",
        "logger": "daemon",
        "message": "Orden publicada",
        "doc_id": 5,
        "worker": "worker-core"
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        # Datos base
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Añadir campos extra si existen
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Añadir exception si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    Logger estructurado con métodos convenientes.

    Uso:
        logger = StructuredLogger("daemon")
        logger.info("Orden publicada", doc_id=5, worker="worker-core")
        logger.error("API call failed", error=str(e), retry_count=2)
    """

    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # Handler para archivo JSON
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)

        # Handler para consola (formato legible)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('[%(levelname)s] %(message)s')
        )
        self.logger.addHandler(console_handler)

    def _log(self, level: int, message: str, **kwargs):
        """Log interno con campos extra"""
        extra = {'extra_fields': kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log nivel DEBUG"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log nivel INFO"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log nivel WARNING"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log nivel ERROR"""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log nivel CRITICAL"""
        self._log(logging.CRITICAL, message, **kwargs)


def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """
    Factory para crear loggers estructurados.

    Args:
        name: Nombre del logger (daemon, worker-core, etc.)
        log_file: Path al archivo de log JSON (opcional)

    Returns:
        StructuredLogger configurado

    Ejemplo:
        logger = get_logger("daemon", "logs/daemon.json")
        logger.info("Sistema iniciado", version="1.0.0")
    """
    return StructuredLogger(name, log_file)


# Ejemplo de uso
if __name__ == "__main__":
    # Test
    logger = get_logger("test", "test_structured.log")

    logger.info("Test iniciado", component="structured_logger")
    logger.warning("Advertencia de prueba", retry_count=1, max_retries=3)
    logger.error("Error de prueba", error_code=500, endpoint="/api/test")

    print("\n[OK] Log estructurado escrito en test_structured.log")
    print("[OK] Revisar el archivo para ver formato JSON")
