"""Tests para IngestaContinua — watcher de directorio + auto-ingesta NLP."""
import os
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.nucleo import ConceptosLucas
from src.core.ingesta_continua import IngestaContinua


@pytest.fixture
def sistema():
    return ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_pipeline(sistema):
    """Pipeline mock que simula extraccion NLP."""
    pipeline = MagicMock()
    pipeline.procesar.return_value = {
        "conceptos": [
            {"nombre": "test_concepto", "relevancia": 0.8, "tipo": "frecuencia"}
        ],
        "relaciones": [("test_concepto", "otro", 0.5)],
        "modo": "basico",
        "dim_original": 15,
        "dim_reducida": 15,
    }
    pipeline.procesar_largo.return_value = pipeline.procesar.return_value
    return pipeline


# ==================== Escanear ====================

class TestEscanear:
    def test_escanear_directorio_vacio(self, sistema, tmpdir):
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = MagicMock()
        assert ingesta.escanear_nuevos() == []

    def test_escanear_con_archivos_txt(self, sistema, tmpdir):
        (tmpdir / "a.txt").write_text("contenido", encoding="utf-8")
        (tmpdir / "b.md").write_text("contenido", encoding="utf-8")
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = MagicMock()
        nuevos = ingesta.escanear_nuevos()
        assert len(nuevos) == 2

    def test_escanear_ignora_otros_formatos(self, sistema, tmpdir):
        (tmpdir / "a.txt").write_text("ok", encoding="utf-8")
        (tmpdir / "b.py").write_text("no", encoding="utf-8")
        (tmpdir / "c.jpg").write_bytes(b"data")
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = MagicMock()
        nuevos = ingesta.escanear_nuevos()
        assert len(nuevos) == 1

    def test_escanear_no_repite_procesados(self, sistema, tmpdir):
        (tmpdir / "a.txt").write_text("ok", encoding="utf-8")
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = MagicMock()
        ingesta.marcar_procesado(str(tmpdir / "a.txt"))
        assert ingesta.escanear_nuevos() == []

    def test_escanear_directorio_inexistente(self, sistema):
        ingesta = IngestaContinua("/no/existe/dir", sistema)
        ingesta._pipeline = MagicMock()
        assert ingesta.escanear_nuevos() == []


# ==================== Procesar archivo ====================

class TestProcesarArchivo:
    def test_procesar_archivo_basico(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "test.txt"
        archivo.write_text("Python es un lenguaje de programacion", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        resultado = ingesta.procesar_archivo(archivo)

        assert resultado["archivo"] == str(archivo)
        assert resultado["palabras"] > 0
        assert resultado["tiempo_s"] > 0
        assert "error" not in resultado or resultado.get("conceptos_nuevos", 0) >= 0

    def test_procesar_archivo_vacio(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "vacio.txt"
        archivo.write_text("", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        resultado = ingesta.procesar_archivo(archivo)
        assert resultado["error"] == "vacio"

    def test_procesar_marca_como_procesado(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "test.txt"
        archivo.write_text("contenido", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_archivo(archivo)

        assert str(archivo) in ingesta._archivos_procesados

    def test_procesar_llama_callback(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "test.txt"
        archivo.write_text("contenido", encoding="utf-8")

        callback = MagicMock()
        ingesta = IngestaContinua(str(tmpdir), sistema, on_ingesta=callback)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_archivo(archivo)

        callback.assert_called_once()
        args = callback.call_args[0][0]
        assert "archivo" in args

    def test_procesar_texto_largo_usa_procesar_largo(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "largo.txt"
        texto = " ".join(["palabra"] * 300)
        archivo.write_text(texto, encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_archivo(archivo)

        mock_pipeline.procesar_largo.assert_called_once()

    def test_procesar_texto_corto_usa_procesar(self, sistema, tmpdir, mock_pipeline):
        archivo = tmpdir / "corto.txt"
        archivo.write_text("Python es genial", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_archivo(archivo)

        mock_pipeline.procesar.assert_called_once()


# ==================== Procesar pendientes ====================

class TestProcesarPendientes:
    def test_procesar_todos_pendientes(self, sistema, tmpdir, mock_pipeline):
        for i in range(3):
            (tmpdir / f"archivo_{i}.txt").write_text(f"contenido {i}", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        resultados = ingesta.procesar_pendientes()
        assert len(resultados) == 3

    def test_procesar_pendientes_vacio(self, sistema, tmpdir, mock_pipeline):
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        assert ingesta.procesar_pendientes() == []


# ==================== Log y estadisticas ====================

class TestEstadisticas:
    def test_estadisticas_vacio(self, sistema, tmpdir):
        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = MagicMock()
        stats = ingesta.estadisticas()
        assert stats["archivos_procesados"] == 0

    def test_estadisticas_con_procesados(self, sistema, tmpdir, mock_pipeline):
        (tmpdir / "a.txt").write_text("contenido", encoding="utf-8")
        (tmpdir / "b.txt").write_text("mas contenido aqui", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_pendientes()

        stats = ingesta.estadisticas()
        assert stats["archivos_procesados"] == 2
        assert stats["palabras_totales"] > 0
        assert stats["tiempo_total_s"] > 0

    def test_log_property(self, sistema, tmpdir, mock_pipeline):
        (tmpdir / "a.txt").write_text("contenido", encoding="utf-8")

        ingesta = IngestaContinua(str(tmpdir), sistema)
        ingesta._pipeline = mock_pipeline
        ingesta.procesar_pendientes()

        log = ingesta.log
        assert len(log) == 1
        assert "archivo" in log[0]
