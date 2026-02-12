"""Tests para endpoints del organismo IANAE en la API REST."""
import pytest
from fastapi.testclient import TestClient

from src.core.nucleo import ConceptosLucas
from src.core.organismo import IANAE
from src.api.main import app, set_sistema, set_organismo
from src.api.auth import _VALID_KEYS, rate_limiter


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """Reset del sistema y organismo para cada test."""
    sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    sistema.añadir_concepto("Python", categoria="tecnologias")
    sistema.añadir_concepto("OpenCV", categoria="tecnologias")
    sistema.añadir_concepto("Docker", categoria="tecnologias")
    sistema.añadir_concepto("IANAE", categoria="conceptos_ianae")
    sistema.añadir_concepto("Tacografos", categoria="proyectos")
    sistema.relacionar("Python", "OpenCV", fuerza=0.8)
    sistema.relacionar("Python", "IANAE", fuerza=0.9)
    sistema.relacionar("OpenCV", "Tacografos", fuerza=0.85)
    sistema.relacionar("Python", "Tacografos", fuerza=0.7)
    sistema.relacionar("Docker", "IANAE", fuerza=0.6)
    for _ in range(3):
        sistema.activar("Python", pasos=2, temperatura=0.1)

    set_sistema(sistema)
    org = IANAE.desde_componentes(
        sistema,
        diario_path=str(tmp_path / "diario.jsonl"),
        objetivos_path=str(tmp_path / "obj.json"),
        conversaciones_path=str(tmp_path / "conv.jsonl"),
        snapshot_dir=str(tmp_path / "snap"),
        intervalo_base=0.01,
    )
    set_organismo(org)

    _VALID_KEYS.clear()
    rate_limiter.reset()
    yield
    _VALID_KEYS.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ==================== TestChat ====================


class TestChatEndpoint:
    def test_chat_200(self, client):
        r = client.post("/api/v1/chat", json={"mensaje": "Hablame de Python"})
        assert r.status_code == 200
        data = r.json()
        assert "respuesta" in data
        assert "conceptos_detectados" in data
        assert "Python" in data["conceptos_detectados"]

    def test_chat_sin_conceptos(self, client):
        r = client.post("/api/v1/chat", json={"mensaje": "Hola mundo"})
        assert r.status_code == 200
        assert isinstance(r.json()["respuesta"], str)

    def test_chat_coherencia_presente(self, client):
        r = client.post("/api/v1/chat", json={"mensaje": "Python y OpenCV"})
        data = r.json()
        assert "coherencia" in data
        assert isinstance(data["coherencia"], float)


# ==================== TestSuenos ====================


class TestSuenosEndpoint:
    def test_imaginar_conexion(self, client):
        r = client.post("/api/v1/suenos/imaginar", json={
            "tipo": "conexion", "a": "Docker", "b": "Tacografos"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["tipo"] == "conexion"
        assert "hipotesis" in data

    def test_imaginar_concepto(self, client):
        r = client.post("/api/v1/suenos/imaginar", json={
            "tipo": "concepto", "nombre": "ML",
            "categoria": "tecnologias", "conectar_a": ["Python"]
        })
        assert r.status_code == 200
        assert r.json()["tipo"] == "concepto"

    def test_imaginar_conexion_sin_params_422(self, client):
        r = client.post("/api/v1/suenos/imaginar", json={"tipo": "conexion"})
        assert r.status_code == 422


# ==================== TestConsciencia ====================


class TestConscienciaEndpoint:
    def test_consciencia_200(self, client):
        r = client.get("/api/v1/consciencia")
        assert r.status_code == 200
        data = r.json()
        assert "pulso" in data
        assert "superficie" in data
        assert "corrientes" in data
        assert "sesgos" in data
        assert "narrativa" in data


# ==================== TestOrganismo ====================


class TestOrganismoEndpoint:
    def test_organismo_estado_200(self, client):
        r = client.get("/api/v1/organismo")
        assert r.status_code == 200
        data = r.json()
        assert "conceptos" in data
        assert "pulso" in data
        assert data["conceptos"] == 5


# ==================== TestDiario ====================


class TestDiarioEndpoint:
    def test_diario_vacio(self, client):
        r = client.get("/api/v1/vida/diario")
        assert r.status_code == 200
        data = r.json()
        assert data["entradas"] == []
        assert data["total"] == 0

    def test_diario_con_datos(self, client):
        # Generar un ciclo primero via chat (que internamente ejecuta activaciones)
        client.post("/api/v1/chat", json={"mensaje": "Python"})
        # El diario se llena solo si hay ciclos de vida, no de chat
        r = client.get("/api/v1/vida/diario?ultimos=5")
        assert r.status_code == 200


# ==================== TestSchemaOrganismo ====================


class TestSchemaOrganismo:
    def test_schema_contiene_nuevos_paths(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/api/v1/chat" in paths
        assert "/api/v1/suenos/imaginar" in paths
        assert "/api/v1/consciencia" in paths
        assert "/api/v1/organismo" in paths
        assert "/api/v1/vida/diario" in paths
