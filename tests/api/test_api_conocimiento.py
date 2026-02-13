"""Tests para los endpoints de Conocimiento Externo (Fase 13)."""
import pytest
from unittest.mock import patch, MagicMock
import json

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


class TestConocimientoEndpoints:

    def test_get_conocimiento_estado(self, client):
        r = client.get("/api/v1/conocimiento")
        assert r.status_code == 200
        data = r.json()
        assert "habilitado" in data
        assert "fuentes" in data

    def test_configurar_conocimiento(self, client):
        r = client.post("/api/v1/conocimiento/configurar", json={
            "habilitado": True,
            "probabilidad_externa": 0.5,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["habilitado"] is True
        assert data["probabilidad_externa"] == 0.5

    def test_explorar_deshabilitado(self, client):
        r = client.post("/api/v1/conocimiento/explorar", json={
            "concepto": "Python",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "deshabilitado"

    def test_explorar_habilitado_con_mock(self, client):
        # Habilitar primero
        client.post("/api/v1/conocimiento/configurar", json={"habilitado": True})
        # Mock la red para Wikipedia
        wiki_opensearch = json.dumps(["Python", ["Python (lenguaje)"], [], []]).encode("utf-8")
        wiki_extract = json.dumps({
            "query": {"pages": {"1": {"extract": "Python es un lenguaje"}}}
        }).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.side_effect = [wiki_opensearch, wiki_extract]
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("src.core.conocimiento_externo.urlopen", return_value=mock_resp):
            r = client.post("/api/v1/conocimiento/explorar", json={
                "concepto": "Python",
                "fuente": "wikipedia",
            })
        assert r.status_code == 200

    def test_get_fuentes(self, client):
        r = client.get("/api/v1/conocimiento/fuentes")
        assert r.status_code == 200
        data = r.json()
        assert "fuentes" in data
        assert "wikipedia" in data["fuentes"]
        assert "rss" in data["fuentes"]
        assert "web" in data["fuentes"]
        assert "archivos" in data["fuentes"]

    def test_agregar_rss(self, client):
        r = client.post("/api/v1/conocimiento/rss", json={
            "url": "https://example.com/feed.xml",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "https://example.com/feed.xml" in data["feeds"]
