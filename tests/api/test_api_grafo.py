"""Tests para los endpoints de Grafo Interactivo (Fase 15)."""
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


class TestDependenciasEndpoint:

    def test_dependencias_200(self, client):
        r = client.get("/api/v1/introspeccion/dependencias")
        assert r.status_code == 200
        data = r.json()
        assert "nodos" in data
        assert "aristas" in data
        assert "total_modulos" in data
        assert "total_dependencias" in data

    def test_dependencias_tiene_modulos(self, client):
        r = client.get("/api/v1/introspeccion/dependencias")
        data = r.json()
        assert len(data["nodos"]) > 0
        assert data["total_modulos"] == len(data["nodos"])

    def test_dependencias_aristas_validas(self, client):
        r = client.get("/api/v1/introspeccion/dependencias")
        data = r.json()
        nodo_ids = {n["id"] for n in data["nodos"]}
        for arista in data["aristas"]:
            assert arista["source"] in nodo_ids, f"source '{arista['source']}' not in nodos"
            assert arista["target"] in nodo_ids, f"target '{arista['target']}' not in nodos"

    def test_dependencias_nodo_campos(self, client):
        r = client.get("/api/v1/introspeccion/dependencias")
        data = r.json()
        for nodo in data["nodos"]:
            assert "id" in nodo
            assert "lineas" in nodo
            assert "clases" in nodo
            assert "es_core" in nodo


class TestNetworkForGraph:

    def test_network_conceptos_campos(self, client):
        r = client.get("/api/v1/network")
        assert r.status_code == 200
        data = r.json()
        assert len(data["conceptos"]) > 0
        for c in data["conceptos"]:
            assert "nombre" in c
            assert "categoria" in c
            assert "activaciones" in c
            assert "fuerza" in c

    def test_network_relaciones_campos(self, client):
        r = client.get("/api/v1/network")
        data = r.json()
        assert len(data["relaciones"]) > 0
        for rel in data["relaciones"]:
            assert "source" in rel
            assert "target" in rel
            assert "weight" in rel
