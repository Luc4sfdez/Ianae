"""Tests para endpoints de streaming — Fase 11."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app, set_organismo, set_sistema
from src.core.nucleo import crear_universo_lucas
from src.core.organismo import IANAE


@pytest.fixture(autouse=True)
def setup_organismo(tmp_path):
    sistema = crear_universo_lucas()
    sistema.crear_relaciones_lucas()
    set_sistema(sistema)
    org = IANAE.desde_componentes(
        sistema,
        diario_path=str(tmp_path / "diario.jsonl"),
        objetivos_path=str(tmp_path / "obj.json"),
        conversaciones_path=str(tmp_path / "conv.jsonl"),
        snapshot_dir=str(tmp_path / "snap"),
        estado_path=str(tmp_path / "estado.json"),
    )
    set_organismo(org)
    yield


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIStreaming:
    def test_stream_stats_200(self, client):
        resp = client.get("/api/v1/stream/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "activo" in data
        assert "eventos_en_buffer" in data
        assert "ultimo_id" in data

    def test_openapi_schema_contiene_stream(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema.get("paths", {})
        assert "/api/v1/stream" in paths
        assert "/api/v1/stream/stats" in paths

    def test_organismo_response_memoria_viva(self, client):
        resp = client.get("/api/v1/organismo")
        assert resp.status_code == 200
        data = resp.json()
        assert "memoria_viva" in data
