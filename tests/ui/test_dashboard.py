"""Tests para el dashboard backend (FastAPI)."""
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.nucleo import ConceptosLucas

# Importar helpers y app
from src.ui.app.main import (
    app,
    get_relative_time,
    get_minutes_since,
    build_network_data,
    ConnectionManager,
)
from fastapi.testclient import TestClient


# ==================== Helper Functions ====================

class TestGetRelativeTime:
    def test_ahora(self):
        ts = datetime.now().isoformat()
        assert get_relative_time(ts) == "ahora"

    def test_hace_minutos(self):
        ts = (datetime.now() - timedelta(minutes=5)).isoformat()
        assert "5 min" in get_relative_time(ts)

    def test_hace_horas(self):
        ts = (datetime.now() - timedelta(hours=3)).isoformat()
        assert "3h" in get_relative_time(ts)

    def test_hace_dias(self):
        ts = (datetime.now() - timedelta(days=2)).isoformat()
        assert "2d" in get_relative_time(ts)

    def test_none(self):
        assert get_relative_time(None) == "nunca"

    def test_vacio(self):
        assert get_relative_time("") == "nunca"

    def test_invalido(self):
        assert get_relative_time("no-es-fecha") == "desconocido"


class TestGetMinutesSince:
    def test_reciente(self):
        ts = (datetime.now() - timedelta(minutes=3)).isoformat()
        result = get_minutes_since(ts)
        assert 2 <= result <= 4

    def test_invalido(self):
        assert get_minutes_since("basura") == 999999


# ==================== build_network_data ====================

class TestBuildNetworkData:
    def _make_sistema(self):
        s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        s.añadir_concepto("A", atributos=np.ones(15), categoria="tecnologias")
        s.añadir_concepto("B", atributos=np.ones(15) * 0.5, categoria="proyectos")
        s.relacionar("A", "B", fuerza=0.7)
        return s

    def test_estructura_basica(self):
        s = self._make_sistema()
        data = build_network_data(s)
        assert "nodes" in data
        assert "links" in data
        assert "metricas" in data
        assert "timestamp" in data

    def test_nodos_correctos(self):
        s = self._make_sistema()
        data = build_network_data(s)
        nombres = {n["id"] for n in data["nodes"]}
        assert "A" in nombres
        assert "B" in nombres

    def test_links_correctos(self):
        s = self._make_sistema()
        data = build_network_data(s)
        assert len(data["links"]) == 1
        link = data["links"][0]
        assert link["weight"] == 0.7

    def test_colores_por_categoria(self):
        s = self._make_sistema()
        data = build_network_data(s)
        for node in data["nodes"]:
            if node["id"] == "A":
                assert node["color"] == "#FF6B6B"  # tecnologias
            elif node["id"] == "B":
                assert node["color"] == "#4ECDC4"  # proyectos

    def test_con_activaciones(self):
        s = self._make_sistema()
        activaciones = {"A": 0.8, "B": 0.2}
        data = build_network_data(s, activaciones)
        for node in data["nodes"]:
            if node["id"] == "A":
                assert node["activacion_actual"] == 0.8

    def test_sin_duplicar_links(self):
        s = self._make_sistema()
        # networkx guarda arista bidireccional — build_network_data debe deduplicar
        data = build_network_data(s)
        assert len(data["links"]) == 1

    def test_categorias_conteo(self):
        s = self._make_sistema()
        data = build_network_data(s)
        cats = data["categorias"]
        assert cats.get("tecnologias", 0) >= 1
        assert cats.get("proyectos", 0) >= 1


# ==================== ConnectionManager ====================

class TestConnectionManager:
    def test_init_empty(self):
        cm = ConnectionManager()
        assert cm.active_connections == []

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        cm = ConnectionManager()
        ws = MagicMock()
        ws.accept = MagicMock(return_value=_async_return(None))
        await cm.connect(ws)
        assert len(cm.active_connections) == 1
        cm.disconnect(ws)
        assert len(cm.active_connections) == 0

    def test_disconnect_not_connected(self):
        cm = ConnectionManager()
        ws = MagicMock()
        cm.disconnect(ws)  # no debe lanzar error
        assert len(cm.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast(self):
        cm = ConnectionManager()
        ws = MagicMock()
        ws.accept = MagicMock(return_value=_async_return(None))
        ws.send_json = MagicMock(return_value=_async_return(None))
        await cm.connect(ws)
        await cm.broadcast({"type": "test"})
        ws.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_broken(self):
        cm = ConnectionManager()
        ws = MagicMock()
        ws.accept = MagicMock(return_value=_async_return(None))
        ws.send_json = MagicMock(side_effect=Exception("closed"))
        await cm.connect(ws)
        await cm.broadcast({"type": "test"})
        assert len(cm.active_connections) == 0


# ==================== API Endpoints (TestClient) ====================

@pytest.fixture
def client():
    """TestClient que mockea get_ianae para no depender de estado global."""
    sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    sistema.crear_conceptos_lucas()
    sistema.crear_relaciones_lucas()

    from src.core.emergente import PensamientoLucas
    pensamiento = PensamientoLucas(sistema)

    with patch("src.ui.app.main.get_ianae", return_value=(sistema, pensamiento)):
        with patch("src.ui.app.main._ianae_system", sistema):
            yield TestClient(app), sistema


class TestAPIEndpoints:
    def test_dashboard_html(self, client):
        tc, _ = client
        resp = tc.get("/")
        assert resp.status_code == 200
        assert "IANAE" in resp.text

    def test_api_status(self, client):
        tc, _ = client
        with patch("src.ui.app.main.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            resp = tc.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "services" in data
            assert "timestamp" in data

    def test_api_ianae_network(self, client):
        tc, sistema = client
        resp = tc.get("/api/ianae/network")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == len(sistema.conceptos)

    def test_api_ianae_metricas(self, client):
        tc, _ = client
        resp = tc.get("/api/ianae/metricas")
        assert resp.status_code == 200
        data = resp.json()
        assert "metricas" in data
        assert "conceptos_total" in data
        assert data["conceptos_total"] > 0

    def test_api_snapshots_list(self, client):
        tc, _ = client
        resp = tc.get("/api/ianae/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert "snapshots" in data

    def test_process_text_empty(self, client):
        tc, _ = client
        resp = tc.post("/api/ianae/process-text", json={"text": ""})
        assert resp.status_code == 400

    def test_process_text_valid(self, client):
        tc, sistema = client
        # Use a concept that exists in the universe
        concepto = list(sistema.conceptos.keys())[0]
        resp = tc.post("/api/ianae/process-text", json={
            "text": concepto,
            "profundidad": 2,
            "temperatura": 0.15
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "concepto_activado" in data
        assert "activaciones" in data
        assert "network" in data

    def test_experiment_ciclo_vital(self, client):
        tc, _ = client
        resp = tc.post("/api/ianae/experiment/ciclo_vital", json={
            "params": {"num_ciclos": 3}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "resultado" in data
        assert "network" in data

    def test_experiment_invalid(self, client):
        tc, _ = client
        resp = tc.post("/api/ianae/experiment/no_existe", json={"params": {}})
        assert resp.status_code == 400

    def test_api_documents_docs_offline(self, client):
        tc, _ = client
        import requests as req_lib
        with patch("src.ui.app.main.requests.get", side_effect=req_lib.exceptions.ConnectionError("connection refused")):
            resp = tc.get("/api/documents")
            assert resp.status_code == 503


# ==================== Helpers ====================

async def _async_return(value):
    """Helper para crear coroutines que retornan un valor."""
    return value
