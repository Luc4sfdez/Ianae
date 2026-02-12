"""Tests para DialogoIANAE — IANAE habla."""
import pytest

from src.core.nucleo import ConceptosLucas
from src.core.emergente import PensamientoLucas
from src.core.insights import InsightsEngine
from src.core.vida_autonoma import VidaAutonoma
from src.core.consciencia import Consciencia
from src.core.dialogo import DialogoIANAE


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("OpenCV", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    s.añadir_concepto("Tacografos", categoria="proyectos")
    s.añadir_concepto("RAG_System", categoria="proyectos")
    s.añadir_concepto("Lucas", categoria="lucas_personal")
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    s.añadir_concepto("Automatizacion", categoria="herramientas")

    s.relacionar("Python", "OpenCV", fuerza=0.9)
    s.relacionar("Python", "Tacografos", fuerza=0.85)
    s.relacionar("OpenCV", "Tacografos", fuerza=0.95)
    s.relacionar("Python", "RAG_System", fuerza=0.8)
    s.relacionar("RAG_System", "IANAE", fuerza=0.9)
    s.relacionar("Lucas", "Python", fuerza=0.95)
    s.relacionar("Lucas", "IANAE", fuerza=0.9)
    s.relacionar("Docker", "RAG_System", fuerza=0.7)
    s.relacionar("Automatizacion", "Python", fuerza=0.85)

    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def dialogo(sistema, tmp_path):
    pensamiento = PensamientoLucas(sistema)
    insights = InsightsEngine(sistema, pensamiento)
    vida = VidaAutonoma(
        sistema, pensamiento, insights,
        intervalo_base=0.01,
        diario_path=str(tmp_path / "diario.jsonl"),
        snapshot_dir=str(tmp_path / "snapshots"),
    )
    consciencia = Consciencia(vida, objetivos_path=str(tmp_path / "obj.json"))
    return DialogoIANAE(consciencia)


# ==================== TestExtraerConceptos ====================


class TestExtraerConceptos:
    def test_extrae_concepto_presente(self, dialogo):
        conceptos = dialogo._extraer_conceptos("Que sabes de Python?")
        assert "Python" in conceptos

    def test_extrae_multiples(self, dialogo):
        conceptos = dialogo._extraer_conceptos("Como se conectan Python y Docker?")
        assert "Python" in conceptos
        assert "Docker" in conceptos

    def test_no_extrae_inexistente(self, dialogo):
        conceptos = dialogo._extraer_conceptos("Que tal el clima?")
        assert len(conceptos) == 0

    def test_case_insensitive(self, dialogo):
        conceptos = dialogo._extraer_conceptos("cuéntame sobre python")
        assert "Python" in conceptos


# ==================== TestResponder ====================


class TestResponder:
    def test_retorna_estructura(self, dialogo):
        r = dialogo.responder("Hablame de Python")
        assert "pregunta" in r
        assert "respuesta" in r
        assert "conceptos_detectados" in r
        assert "timestamp" in r

    def test_respuesta_contiene_concepto(self, dialogo):
        r = dialogo.responder("Que sabes de Python?")
        assert "Python" in r["respuesta"]

    def test_respuesta_sin_conceptos_no_falla(self, dialogo):
        r = dialogo.responder("Hola, como estas?")
        assert isinstance(r["respuesta"], str)
        assert len(r["respuesta"]) > 0

    def test_respuesta_con_multiples_conceptos(self, dialogo):
        r = dialogo.responder("Python y OpenCV juntos?")
        assert "Python" in r["conceptos_detectados"]
        assert "OpenCV" in r["conceptos_detectados"]


# ==================== TestConversar ====================


class TestConversar:
    def test_conversar_retorna_string(self, dialogo):
        texto = dialogo.conversar("Hablame de Docker")
        assert isinstance(texto, str)
        assert len(texto) > 0

    def test_conversar_sobre_concepto(self, dialogo):
        texto = dialogo.conversar("Que conexiones tiene IANAE?")
        assert "IANAE" in texto


# ==================== TestHistorial ====================


class TestHistorial:
    def test_historial_vacio_inicial(self, dialogo):
        assert dialogo.historial() == []

    def test_historial_registra(self, dialogo):
        dialogo.conversar("Python")
        dialogo.conversar("Docker")
        h = dialogo.historial()
        assert len(h) == 2

    def test_historial_ultimos_n(self, dialogo):
        for _ in range(5):
            dialogo.conversar("Python")
        h = dialogo.historial(ultimos=3)
        assert len(h) == 3


# ==================== TestEstadoConversacion ====================


class TestEstadoConversacion:
    def test_estado_inicial(self, dialogo):
        e = dialogo.estado_conversacion()
        assert e["interacciones"] == 0
        assert e["conceptos_tocados"] == []

    def test_estado_con_interacciones(self, dialogo):
        dialogo.conversar("Python y Docker")
        e = dialogo.estado_conversacion()
        assert e["interacciones"] == 1
        assert "Python" in e["conceptos_tocados"]
        assert "pulso" in e
