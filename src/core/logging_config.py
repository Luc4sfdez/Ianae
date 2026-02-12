"""
Configuracion de logging estructurado para IANAE.

Uso:
    from src.core.logging_config import setup_logging
    setup_logging()  # Development (readable)
    setup_logging(json_format=True, log_file="ianae.log")  # Production (JSON)
"""
import logging
import logging.handlers
import json
import os
import sys
import time
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Formatter que emite logs en formato JSON (una linea por log)."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
):
    """
    Configura logging para toda la aplicacion IANAE.

    Args:
        level: nivel minimo ("DEBUG", "INFO", "WARNING", "ERROR")
        json_format: True para formato JSON (produccion)
        log_file: ruta a archivo de log (None = solo consola)
        max_bytes: tamano maximo del archivo antes de rotar
        backup_count: numero de archivos de backup
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Limpiar handlers existentes
    root_logger.handlers.clear()

    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Handler consola
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # Handler archivo con rotacion
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Silenciar loggers ruidosos de terceros
    for noisy in ["watchdog", "urllib3", "httpcore", "httpx", "sentence_transformers"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("src").info(
        "Logging configurado: level=%s, json=%s, file=%s",
        level, json_format, log_file or "none"
    )
