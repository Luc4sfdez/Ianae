"""
Cliente REST para docs-service de IANAE.
Adaptado a los campos REALES de la API (inglés).
"""

import requests
import logging

logger = logging.getLogger("arquitecto.docs_client")


class DocsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.timeout = 10

    def health_check(self):
        try:
            r = requests.get(f"{self.base_url}/health", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"docs-service no responde: {e}")
            return None

    def get_snapshot(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/context/snapshot", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error obteniendo snapshot: {e}")
            return None

    def get_new_docs(self, since):
        try:
            r = requests.get(
                f"{self.base_url}/api/v1/notifications/since",
                params={"t": since},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Error obteniendo docs nuevos: {e}")
            return []

    def get_worker_pendientes(self, worker_name):
        try:
            r = requests.get(
                f"{self.base_url}/api/v1/worker/{worker_name}/pendientes",
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("pendientes", [])
        except Exception as e:
            logger.error(f"Error pendientes {worker_name}: {e}")
            return []

    def get_doc(self, doc_id):
        try:
            r = requests.get(f"{self.base_url}/api/v1/docs/{doc_id}", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error doc {doc_id}: {e}")
            return None

    def publish_order(self, title, content, tags=None, priority="alta"):
        """Publicar una orden del Arquitecto."""
        payload = {
            "title": title,
            "content": content,
            "category": "especificaciones",
            "author": "arquitecto-daemon",
            "tags": tags or [],
            "priority": priority,
            "status": "pending",
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/v1/docs",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            result = r.json()
            logger.info(f"Orden publicada: {title}")
            return result
        except Exception as e:
            logger.error(f"Error publicando orden: {e}")
            return None

    def publish_escalado(self, mensaje):
        """Escalar algo a Lucas."""
        return self.publish_order(
            title=f"ESCALADO: {mensaje[:80]}",
            content=f"# Requiere decision de Lucas\n\n{mensaje}",
            tags=["escalado", "lucas"],
            priority="alta",
        )

    def publish_duda_response(self, worker_name, duda_title, respuesta):
        """Publicar respuesta a una duda de un worker."""
        return self.publish_order(
            title=f"RESPUESTA: {duda_title[:60]}",
            content=respuesta,
            tags=[worker_name, "respuesta-duda"],
            priority="alta",
        )

    def publish_worker_report(self, worker_name, title, content, tags=None):
        """Publicar reporte de un worker."""
        payload = {
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/v1/worker/{worker_name}/reporte",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error reporte {worker_name}: {e}")
            return None
