"""
Cliente Python para la API REST de IANAE.

Uso:
    from src.sdk.ianae_client import IANAEClient

    client = IANAEClient("http://localhost:8000")
    conceptos = client.list_concepts()
    result = client.activate("Python", pasos=3)
"""
import time
from typing import Dict, List, Optional, Any

import requests


class IANAEError(Exception):
    """Error generico del cliente IANAE."""

    def __init__(self, message: str, status_code: int = 0, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class IANAEClient:
    """Cliente Python para la API REST de IANAE."""

    def __init__(self, base_url: str = "http://localhost:8000",
                 api_key: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 2,
                 retry_delay: float = 1.0):
        """
        Args:
            base_url: URL base de la API (sin / final)
            api_key: API key para autenticacion (opcional)
            timeout: timeout en segundos para requests
            max_retries: reintentos en caso de error de red
            retry_delay: segundos entre reintentos
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = requests.Session()

        if api_key:
            self._session.headers["X-API-Key"] = api_key

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Request con retry y error handling."""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.request(method, url, **kwargs)

                if response.status_code == 204:
                    return None

                if response.status_code >= 400:
                    detail = ""
                    try:
                        body = response.json()
                        detail = body.get("detail", str(body))
                    except (ValueError, KeyError):
                        detail = response.text

                    raise IANAEError(
                        f"HTTP {response.status_code}: {detail}",
                        status_code=response.status_code,
                        detail=detail,
                    )

                return response.json()

            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                raise IANAEError(f"No se pudo conectar a {url}: {e}") from e

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                raise IANAEError(f"Timeout conectando a {url}") from e

        raise IANAEError(f"Fallo tras {self.max_retries + 1} intentos: {last_error}")

    # --- Health ---

    def health(self) -> Dict:
        """Verifica el estado del servidor."""
        return self._request("GET", "/health")

    # --- Concepts ---

    def list_concepts(self, categoria: Optional[str] = None,
                      limit: int = 50, offset: int = 0) -> List[Dict]:
        """Lista conceptos del sistema."""
        params = {"limit": limit, "offset": offset}
        if categoria:
            params["categoria"] = categoria
        return self._request("GET", "/api/v1/concepts", params=params)

    def get_concept(self, name: str, include_vector: bool = False) -> Dict:
        """Detalle de un concepto."""
        params = {"include_vector": include_vector}
        return self._request("GET", f"/api/v1/concepts/{name}", params=params)

    def create_concept(self, nombre: str, categoria: str = "emergentes",
                       atributos: Optional[List[float]] = None,
                       incertidumbre: Optional[float] = None) -> Dict:
        """Crea un nuevo concepto."""
        body = {"nombre": nombre, "categoria": categoria}
        if atributos is not None:
            body["atributos"] = atributos
        if incertidumbre is not None:
            body["incertidumbre"] = incertidumbre
        return self._request("POST", "/api/v1/concepts", json=body)

    def delete_concept(self, name: str):
        """Elimina un concepto."""
        return self._request("DELETE", f"/api/v1/concepts/{name}")

    # --- Relations ---

    def create_relation(self, concepto1: str, concepto2: str,
                        fuerza: Optional[float] = None,
                        bidireccional: bool = True) -> Dict:
        """Crea una relacion entre conceptos."""
        body = {
            "concepto1": concepto1,
            "concepto2": concepto2,
            "bidireccional": bidireccional,
        }
        if fuerza is not None:
            body["fuerza"] = fuerza
        return self._request("POST", "/api/v1/relations", json=body)

    # --- Activate ---

    def activate(self, concepto: str, pasos: int = 3,
                 temperatura: float = 0.1) -> Dict:
        """Activa un concepto y propaga."""
        body = {
            "concepto": concepto,
            "pasos": pasos,
            "temperatura": temperatura,
        }
        return self._request("POST", "/api/v1/activate", json=body)

    # --- Network ---

    def get_network(self) -> Dict:
        """Obtiene el grafo completo."""
        return self._request("GET", "/api/v1/network")

    # --- Stats ---

    def get_stats(self) -> Dict:
        """Estadisticas del sistema."""
        return self._request("GET", "/api/v1/stats")

    # --- Ingest ---

    def ingest(self, texto: str, max_conceptos: int = 10,
               categoria: str = "nlp_extraidos",
               umbral_relacion: float = 0.2) -> Dict:
        """Procesa texto via NLP."""
        body = {
            "texto": texto,
            "max_conceptos": max_conceptos,
            "categoria": categoria,
            "umbral_relacion": umbral_relacion,
        }
        return self._request("POST", "/api/v1/ingest", json=body)

    # --- Context manager ---

    def close(self):
        """Cierra la sesion HTTP."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
