"""Tests para la API REST de IANAE."""
import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.core.nucleo import ConceptosLucas
from src.api.main import app, set_sistema, get_sistema
from src.api.auth import add_api_key, remove_api_key, _VALID_KEYS, rate_limiter


@pytest.fixture(autouse=True)
def reset_state():
    """Reset del sistema y auth para cada test."""
    sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    sistema.añadir_concepto("Python", categoria="tecnologias")
    sistema.añadir_concepto("OpenCV", categoria="tecnologias")
    sistema.añadir_concepto("IANAE", categoria="conceptos_ianae")
    sistema.relacionar("Python", "OpenCV", fuerza=0.8)
    sistema.relacionar("Python", "IANAE", fuerza=0.9)
    set_sistema(sistema)

    # Sin auth para tests por defecto
    _VALID_KEYS.clear()
    rate_limiter.reset()
    yield
    _VALID_KEYS.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ==================== Health ====================

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert data["conceptos"] == 3

    def test_health_no_auth_required(self, client):
        add_api_key("test-key")
        r = client.get("/health")
        assert r.status_code == 200
        remove_api_key("test-key")


# ==================== List Concepts ====================

class TestListConcepts:
    def test_list_all(self, client):
        r = client.get("/api/v1/concepts")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3
        nombres = {c["nombre"] for c in data}
        assert "Python" in nombres
        assert "OpenCV" in nombres

    def test_list_filter_by_categoria(self, client):
        r = client.get("/api/v1/concepts", params={"categoria": "tecnologias"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert all(c["categoria"] == "tecnologias" for c in data)

    def test_list_filter_no_match(self, client):
        r = client.get("/api/v1/concepts", params={"categoria": "no_existe"})
        assert r.status_code == 200
        assert r.json() == []

    def test_list_pagination(self, client):
        r = client.get("/api/v1/concepts", params={"limit": 2, "offset": 0})
        assert len(r.json()) == 2

        r2 = client.get("/api/v1/concepts", params={"limit": 2, "offset": 2})
        assert len(r2.json()) == 1

    def test_concept_response_fields(self, client):
        r = client.get("/api/v1/concepts")
        c = r.json()[0]
        assert "nombre" in c
        assert "categoria" in c
        assert "activaciones" in c
        assert "fuerza" in c
        assert "vector_dim" in c
        assert c["vector_dim"] == 15


# ==================== Get Concept ====================

class TestGetConcept:
    def test_get_existing(self, client):
        r = client.get("/api/v1/concepts/Python")
        assert r.status_code == 200
        data = r.json()
        assert data["nombre"] == "Python"
        assert data["categoria"] == "tecnologias"
        assert "vecinos" in data
        assert len(data["vecinos"]) == 2  # OpenCV + IANAE

    def test_get_with_vector(self, client):
        r = client.get("/api/v1/concepts/Python", params={"include_vector": True})
        data = r.json()
        assert data["vector"] is not None
        assert len(data["vector"]) == 15

    def test_get_without_vector(self, client):
        r = client.get("/api/v1/concepts/Python")
        assert r.json()["vector"] is None

    def test_get_not_found(self, client):
        r = client.get("/api/v1/concepts/NoExiste")
        assert r.status_code == 404

    def test_vecinos_sorted_by_fuerza(self, client):
        r = client.get("/api/v1/concepts/Python")
        vecinos = r.json()["vecinos"]
        fuerzas = [v["fuerza"] for v in vecinos]
        assert fuerzas == sorted(fuerzas, reverse=True)


# ==================== Create Concept ====================

class TestCreateConcept:
    def test_create_basic(self, client):
        r = client.post("/api/v1/concepts", json={
            "nombre": "FastAPI",
            "categoria": "tecnologias",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "FastAPI"
        assert data["categoria"] == "tecnologias"
        assert data["vector_dim"] == 15

    def test_create_with_vector(self, client):
        vec = [0.1] * 15
        r = client.post("/api/v1/concepts", json={
            "nombre": "Nuevo",
            "atributos": vec,
        })
        assert r.status_code == 201

    def test_create_duplicate(self, client):
        r = client.post("/api/v1/concepts", json={"nombre": "Python"})
        assert r.status_code == 409

    def test_create_wrong_vector_dim(self, client):
        r = client.post("/api/v1/concepts", json={
            "nombre": "Malo",
            "atributos": [0.1] * 10,
        })
        assert r.status_code == 422

    def test_create_empty_name(self, client):
        r = client.post("/api/v1/concepts", json={"nombre": ""})
        assert r.status_code == 422

    def test_concept_appears_in_list(self, client):
        client.post("/api/v1/concepts", json={"nombre": "Nuevo"})
        r = client.get("/api/v1/concepts")
        nombres = {c["nombre"] for c in r.json()}
        assert "Nuevo" in nombres


# ==================== Delete Concept ====================

class TestDeleteConcept:
    def test_delete_existing(self, client):
        r = client.delete("/api/v1/concepts/OpenCV")
        assert r.status_code == 204

        r2 = client.get("/api/v1/concepts/OpenCV")
        assert r2.status_code == 404

    def test_delete_not_found(self, client):
        r = client.delete("/api/v1/concepts/NoExiste")
        assert r.status_code == 404

    def test_delete_removes_from_list(self, client):
        client.delete("/api/v1/concepts/OpenCV")
        r = client.get("/api/v1/concepts")
        nombres = {c["nombre"] for c in r.json()}
        assert "OpenCV" not in nombres


# ==================== Relations ====================

class TestRelations:
    def test_create_relation(self, client):
        r = client.post("/api/v1/relations", json={
            "concepto1": "OpenCV",
            "concepto2": "IANAE",
            "fuerza": 0.7,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["concepto1"] == "OpenCV"
        assert data["concepto2"] == "IANAE"
        assert data["fuerza"] > 0

    def test_create_relation_not_found(self, client):
        r = client.post("/api/v1/relations", json={
            "concepto1": "Python",
            "concepto2": "NoExiste",
        })
        assert r.status_code == 404

    def test_relation_appears_in_network(self, client):
        client.post("/api/v1/relations", json={
            "concepto1": "OpenCV",
            "concepto2": "IANAE",
            "fuerza": 0.5,
        })
        r = client.get("/api/v1/network")
        rels = r.json()["relaciones"]
        pares = {(rel["source"], rel["target"]) for rel in rels}
        assert ("OpenCV", "IANAE") in pares or ("IANAE", "OpenCV") in pares


# ==================== Activate ====================

class TestActivate:
    def test_activate_basic(self, client):
        r = client.post("/api/v1/activate", json={"concepto": "Python"})
        assert r.status_code == 200
        data = r.json()
        assert data["concepto"] == "Python"
        assert len(data["activaciones"]) > 0
        assert len(data["top_activados"]) > 0

    def test_activate_with_params(self, client):
        r = client.post("/api/v1/activate", json={
            "concepto": "Python",
            "pasos": 5,
            "temperatura": 0.3,
        })
        assert r.status_code == 200
        # pasos + 1 = 6 (initial + 5 steps)
        assert len(r.json()["activaciones"]) > 0

    def test_activate_not_found(self, client):
        r = client.post("/api/v1/activate", json={"concepto": "NoExiste"})
        assert r.status_code == 404

    def test_top_activados_sorted(self, client):
        r = client.post("/api/v1/activate", json={"concepto": "Python"})
        top = r.json()["top_activados"]
        activaciones = [t["activacion"] for t in top]
        assert activaciones == sorted(activaciones, reverse=True)


# ==================== Network ====================

class TestNetwork:
    def test_network_structure(self, client):
        r = client.get("/api/v1/network")
        assert r.status_code == 200
        data = r.json()
        assert data["nodos"] == 3
        assert data["aristas"] == 2
        assert len(data["conceptos"]) == 3
        assert len(data["relaciones"]) == 2

    def test_network_categorias(self, client):
        r = client.get("/api/v1/network")
        cats = r.json()["categorias"]
        assert "tecnologias" in cats
        assert cats["tecnologias"] == 2


# ==================== Stats ====================

class TestStats:
    def test_stats_structure(self, client):
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["conceptos_total"] == 3
        assert data["aristas_total"] == 2
        assert "categorias" in data
        assert "metricas" in data


# ==================== Ingest ====================

class TestIngest:
    def test_ingest_text(self, client):
        r = client.post("/api/v1/ingest", json={
            "texto": "Python es un lenguaje de programacion utilizado en inteligencia artificial",
            "max_conceptos": 5,
        })
        # Puede ser 200 o 503 (si NLP no disponible)
        if r.status_code == 200:
            data = r.json()
            assert data["conceptos_extraidos"] > 0
            assert "modo_nlp" in data
        else:
            assert r.status_code == 503

    def test_ingest_empty_text(self, client):
        r = client.post("/api/v1/ingest", json={"texto": ""})
        assert r.status_code == 422


# ==================== Auth ====================

class TestAuth:
    def test_no_auth_by_default(self, client):
        r = client.get("/api/v1/concepts")
        assert r.status_code == 200

    def test_auth_required_when_keys_set(self, client):
        add_api_key("my-secret-key")
        r = client.get("/api/v1/concepts")
        assert r.status_code == 401

    def test_auth_valid_key(self, client):
        add_api_key("my-secret-key")
        r = client.get("/api/v1/concepts", headers={"X-API-Key": "my-secret-key"})
        assert r.status_code == 200

    def test_auth_invalid_key(self, client):
        add_api_key("my-secret-key")
        r = client.get("/api/v1/concepts", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 403

    def test_auth_multiple_keys(self, client):
        add_api_key("key1")
        add_api_key("key2")
        r1 = client.get("/api/v1/concepts", headers={"X-API-Key": "key1"})
        r2 = client.get("/api/v1/concepts", headers={"X-API-Key": "key2"})
        assert r1.status_code == 200
        assert r2.status_code == 200


# ==================== Rate Limiting ====================

class TestRateLimit:
    def test_rate_limit_allows_normal_traffic(self, client):
        for _ in range(5):
            r = client.get("/api/v1/concepts")
            assert r.status_code == 200

    def test_rate_limit_blocks_excess(self, client):
        rate_limiter.rpm = 3
        for i in range(3):
            r = client.get("/api/v1/concepts")
            assert r.status_code == 200

        r = client.get("/api/v1/concepts")
        assert r.status_code == 429
        rate_limiter.rpm = 60  # restaurar


# ==================== OpenAPI Docs ====================

class TestDocs:
    def test_openapi_schema(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "IANAE API"
        assert "/api/v1/concepts" in schema["paths"]
        assert "/api/v1/activate" in schema["paths"]
        assert "/api/v1/network" in schema["paths"]
        assert "/api/v1/ingest" in schema["paths"]

    def test_docs_page(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_feedback_in_schema(self, client):
        r = client.get("/openapi.json")
        assert "/api/v1/feedback" in r.json()["paths"]


# ==================== Feedback ====================

class TestFeedback:
    def test_feedback_relevante(self, client):
        r = client.post("/api/v1/feedback", json={
            "concepto": "Python",
            "tipo": "relevante",
            "intensidad": 0.8,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["tipo"] == "relevante"
        assert data["fuerza_despues"] > data["fuerza_antes"]
        assert "fortalecido" in data["mensaje"]

    def test_feedback_ruido(self, client):
        r = client.post("/api/v1/feedback", json={
            "concepto": "Python",
            "tipo": "ruido",
            "intensidad": 0.8,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["tipo"] == "ruido"
        assert data["fuerza_despues"] < data["fuerza_antes"]
        assert "debilitado" in data["mensaje"]

    def test_feedback_concepto_no_existe(self, client):
        r = client.post("/api/v1/feedback", json={
            "concepto": "NoExiste",
            "tipo": "relevante",
        })
        assert r.status_code == 404

    def test_feedback_tipo_invalido(self, client):
        r = client.post("/api/v1/feedback", json={
            "concepto": "Python",
            "tipo": "invalido",
        })
        assert r.status_code == 422

    def test_feedback_intensidad_default(self, client):
        r = client.post("/api/v1/feedback", json={
            "concepto": "Python",
            "tipo": "relevante",
        })
        assert r.status_code == 200

    def test_feedback_acumulativo(self, client):
        # Multiples feedbacks relevantes deben acumular
        r1 = client.post("/api/v1/feedback", json={
            "concepto": "Python", "tipo": "relevante", "intensidad": 0.5
        })
        fuerza1 = r1.json()["fuerza_despues"]

        r2 = client.post("/api/v1/feedback", json={
            "concepto": "Python", "tipo": "relevante", "intensidad": 0.5
        })
        fuerza2 = r2.json()["fuerza_despues"]
        assert fuerza2 >= fuerza1

    def test_feedback_ruido_no_baja_de_minimo(self, client):
        # Muchos ruidos no deben bajar fuerza a 0
        for _ in range(20):
            r = client.post("/api/v1/feedback", json={
                "concepto": "Python", "tipo": "ruido", "intensidad": 1.0
            })
        assert r.json()["fuerza_despues"] >= 0.05
