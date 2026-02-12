"""Tests para los endpoints de Insights en la API REST."""
import pytest
from fastapi.testclient import TestClient

from src.core.nucleo import ConceptosLucas
from src.core.insights import InsightsEngine
from src.api.main import app, set_sistema, set_insights
from src.api.auth import _VALID_KEYS, add_api_key, rate_limiter


@pytest.fixture(autouse=True)
def reset_state():
    """Reset del sistema, insights y auth para cada test."""
    sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    sistema.añadir_concepto("Python", categoria="tecnologias")
    sistema.añadir_concepto("OpenCV", categoria="tecnologias")
    sistema.añadir_concepto("IANAE", categoria="conceptos_ianae")
    sistema.añadir_concepto("Tacografos", categoria="proyectos")
    sistema.relacionar("Python", "OpenCV", fuerza=0.8)
    sistema.relacionar("Python", "IANAE", fuerza=0.9)
    sistema.relacionar("OpenCV", "Tacografos", fuerza=0.85)
    sistema.relacionar("Python", "Tacografos", fuerza=0.7)
    # Generar historial
    for _ in range(3):
        sistema.activar("Python", pasos=2, temperatura=0.1)
    set_sistema(sistema)
    set_insights(InsightsEngine(sistema))

    _VALID_KEYS.clear()
    rate_limiter.reset()
    yield
    _VALID_KEYS.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestPatronesEndpoint:
    def test_patrones_200(self, client):
        r = client.get("/api/v1/insights/patrones")
        assert r.status_code == 200
        data = r.json()
        assert "comunidades" in data
        assert "puentes" in data
        assert "clusters_densos" in data
        assert "conceptos_aislados" in data
        assert "narrativa" in data
        assert isinstance(data["comunidades"], list)

    def test_patrones_comunidades_contienen_nodos(self, client):
        r = client.get("/api/v1/insights/patrones")
        data = r.json()
        todos = set()
        for com in data["comunidades"]:
            todos.update(com)
        assert "Python" in todos


class TestRecomendacionesEndpoint:
    def test_recomendaciones_global(self, client):
        r = client.post("/api/v1/insights/recomendaciones", json={})
        assert r.status_code == 200
        data = r.json()
        assert "explorar" in data
        assert "conectar" in data
        assert "narrativa" in data

    def test_recomendaciones_por_concepto(self, client):
        r = client.post("/api/v1/insights/recomendaciones",
                        json={"concepto": "Python"})
        assert r.status_code == 200
        assert len(r.json()["narrativa"]) > 0

    def test_recomendaciones_concepto_404(self, client):
        r = client.post("/api/v1/insights/recomendaciones",
                        json={"concepto": "NoExiste"})
        assert r.status_code == 404


class TestPredictivoEndpoint:
    def test_predictivo_200(self, client):
        r = client.get("/api/v1/insights/predictivo")
        assert r.status_code == 200
        data = r.json()
        assert "tendencias" in data
        assert "gaps_conocimiento" in data
        assert "proximas_tecnologias" in data
        assert "narrativa" in data


class TestInsightsSchema:
    def test_schema_contiene_paths(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/api/v1/insights/patrones" in paths
        assert "/api/v1/insights/recomendaciones" in paths
        assert "/api/v1/insights/predictivo" in paths


class TestInsightsAuth:
    def test_auth_requerida(self, client):
        add_api_key("test-key")
        r = client.get("/api/v1/insights/patrones")
        assert r.status_code == 401

        r2 = client.get("/api/v1/insights/patrones",
                        headers={"X-API-Key": "test-key"})
        assert r2.status_code == 200
