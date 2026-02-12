"""Tests para el SDK Python de IANAE."""
import pytest
from unittest.mock import patch, MagicMock

from src.sdk.ianae_client import IANAEClient, IANAEError
import requests


# ==================== IANAEClient basics ====================

class TestClientInit:
    def test_default_url(self):
        client = IANAEClient()
        assert client.base_url == "http://localhost:8000"

    def test_custom_url(self):
        client = IANAEClient("http://example.com:9000/")
        assert client.base_url == "http://example.com:9000"

    def test_api_key_set(self):
        client = IANAEClient(api_key="my-key")
        assert client._session.headers["X-API-Key"] == "my-key"

    def test_no_api_key(self):
        client = IANAEClient()
        assert "X-API-Key" not in client._session.headers

    def test_context_manager(self):
        with IANAEClient() as client:
            assert isinstance(client, IANAEClient)


# ==================== Request method ====================

class TestClientRequests:
    @patch.object(requests.Session, "request")
    def test_get_success(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_req.return_value = mock_resp

        client = IANAEClient("http://localhost:8000")
        result = client.health()
        assert result == {"status": "ok"}
        mock_req.assert_called_once()

    @patch.object(requests.Session, "request")
    def test_post_with_json(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"concepto": "Python", "activaciones": []}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        result = client.activate("Python")
        assert result["concepto"] == "Python"

        # Verificar que se paso JSON en el body
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs.get("json") is not None

    @patch.object(requests.Session, "request")
    def test_404_raises_error(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "No encontrado"}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        with pytest.raises(IANAEError) as exc_info:
            client.get_concept("NoExiste")
        assert exc_info.value.status_code == 404

    @patch.object(requests.Session, "request")
    def test_401_raises_error(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"detail": "API key requerida"}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        with pytest.raises(IANAEError) as exc_info:
            client.list_concepts()
        assert exc_info.value.status_code == 401

    @patch.object(requests.Session, "request")
    def test_204_returns_none(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_req.return_value = mock_resp

        client = IANAEClient()
        result = client.delete_concept("Python")
        assert result is None

    @patch.object(requests.Session, "request")
    def test_connection_error_retries(self, mock_req):
        mock_req.side_effect = requests.exceptions.ConnectionError("refused")

        client = IANAEClient(max_retries=1, retry_delay=0.01)
        with pytest.raises(IANAEError, match="No se pudo conectar"):
            client.health()

        # Debe intentar 2 veces (1 + 1 retry)
        assert mock_req.call_count == 2

    @patch.object(requests.Session, "request")
    def test_timeout_retries(self, mock_req):
        mock_req.side_effect = requests.exceptions.Timeout("timeout")

        client = IANAEClient(max_retries=0, retry_delay=0.01)
        with pytest.raises(IANAEError, match="Timeout"):
            client.health()
        assert mock_req.call_count == 1

    @patch.object(requests.Session, "request")
    def test_retry_then_success(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}

        mock_req.side_effect = [
            requests.exceptions.ConnectionError("first fail"),
            mock_resp,
        ]

        client = IANAEClient(max_retries=1, retry_delay=0.01)
        result = client.health()
        assert result == {"status": "ok"}
        assert mock_req.call_count == 2


# ==================== SDK methods ====================

class TestClientMethods:
    @patch.object(requests.Session, "request")
    def test_list_concepts_params(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_req.return_value = mock_resp

        client = IANAEClient()
        client.list_concepts(categoria="tech", limit=10, offset=5)

        call_kwargs = mock_req.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params["categoria"] == "tech"
        assert params["limit"] == 10
        assert params["offset"] == 5

    @patch.object(requests.Session, "request")
    def test_create_concept_body(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"nombre": "Nuevo"}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        client.create_concept("Nuevo", categoria="tech", incertidumbre=0.1)

        call_kwargs = mock_req.call_args
        body = call_kwargs.kwargs.get("json", {})
        assert body["nombre"] == "Nuevo"
        assert body["categoria"] == "tech"
        assert body["incertidumbre"] == 0.1

    @patch.object(requests.Session, "request")
    def test_activate_body(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"concepto": "Python", "activaciones": []}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        client.activate("Python", pasos=5, temperatura=0.3)

        body = mock_req.call_args.kwargs.get("json", {})
        assert body["concepto"] == "Python"
        assert body["pasos"] == 5
        assert body["temperatura"] == 0.3

    @patch.object(requests.Session, "request")
    def test_ingest_body(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"conceptos_extraidos": 3}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        client.ingest("texto de prueba", max_conceptos=5)

        body = mock_req.call_args.kwargs.get("json", {})
        assert body["texto"] == "texto de prueba"
        assert body["max_conceptos"] == 5

    @patch.object(requests.Session, "request")
    def test_get_network(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"nodos": 10, "aristas": 15}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        result = client.get_network()
        assert result["nodos"] == 10

    @patch.object(requests.Session, "request")
    def test_get_stats(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"conceptos_total": 50}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        result = client.get_stats()
        assert result["conceptos_total"] == 50

    @patch.object(requests.Session, "request")
    def test_create_relation_body(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"concepto1": "A", "concepto2": "B", "fuerza": 0.5}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        result = client.create_relation("A", "B", fuerza=0.5)
        assert result["fuerza"] == 0.5

    @patch.object(requests.Session, "request")
    def test_get_concept_include_vector(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"nombre": "Python", "vector": [0.1] * 15}
        mock_req.return_value = mock_resp

        client = IANAEClient()
        client.get_concept("Python", include_vector=True)

        params = mock_req.call_args.kwargs.get("params", {})
        assert params["include_vector"] is True


# ==================== Error class ====================

class TestIANAEError:
    def test_error_attributes(self):
        err = IANAEError("test error", status_code=404, detail="not found")
        assert str(err) == "test error"
        assert err.status_code == 404
        assert err.detail == "not found"

    def test_error_defaults(self):
        err = IANAEError("simple error")
        assert err.status_code == 0
        assert err.detail == ""
