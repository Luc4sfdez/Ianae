"""Tests para logging_config — configuracion de logging estructurado."""
import json
import logging
import os
import tempfile
import pytest

from src.core.logging_config import JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_format_basico(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Hola mundo", args=(), exc_info=None,
        )
        result = fmt.format(record)
        data = json.loads(result)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Hola mundo"
        assert "timestamp" in data

    def test_format_con_args(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="Valor: %d", args=(42,), exc_info=None,
        )
        result = fmt.format(record)
        data = json.loads(result)
        assert data["message"] == "Valor: 42"

    def test_format_con_exception(self):
        fmt = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Fallo", args=(), exc_info=exc_info,
        )
        result = fmt.format(record)
        data = json.loads(result)
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_format_con_extra_data(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Con datos", args=(), exc_info=None,
        )
        record.extra_data = {"clave": "valor"}
        result = fmt.format(record)
        data = json.loads(result)
        assert data["data"] == {"clave": "valor"}

    def test_json_valido_unicode(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Español: ñáéíóú", args=(), exc_info=None,
        )
        result = fmt.format(record)
        data = json.loads(result)
        assert "ñáéíóú" in data["message"]


class TestSetupLogging:
    def setup_method(self):
        """Limpiar handlers antes de cada test."""
        root = logging.getLogger()
        root.handlers.clear()

    def test_setup_consola(self):
        setup_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) >= 1

    def test_setup_json_format(self):
        setup_logging(json_format=True)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)

    def test_setup_readable_format(self):
        setup_logging(json_format=False)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert not isinstance(handler.formatter, JSONFormatter)

    def test_setup_con_archivo(self):
        d = tempfile.mkdtemp()
        try:
            log_path = os.path.join(d, "test.log")
            setup_logging(log_file=log_path)
            root = logging.getLogger()
            # Debe tener consola + archivo
            assert len(root.handlers) == 2

            # Escribir algo y verificar archivo
            logging.getLogger("test_file").info("Test message")
            for h in root.handlers:
                h.flush()
            assert os.path.exists(log_path)
        finally:
            # Cerrar handlers de archivo para liberar en Windows
            root = logging.getLogger()
            for h in list(root.handlers):
                if hasattr(h, "baseFilename"):
                    h.close()
                    root.removeHandler(h)

    def test_setup_silencia_ruidosos(self):
        setup_logging()
        watchdog_logger = logging.getLogger("watchdog")
        assert watchdog_logger.level >= logging.WARNING

    def test_setup_level_info(self):
        setup_logging(level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING
