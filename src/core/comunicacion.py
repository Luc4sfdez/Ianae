"""
Canal de Comunicacion entre instancias IANAE — Fase 16.

Cada instancia escribe mensajes JSON a un outbox y lee de un inbox.
Tipos de mensaje: concepto, descubrimiento, saludo.
"""
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class CanalComunicacion:
    """Comunicacion file-based entre instancias IANAE."""

    def __init__(
        self,
        instancia_id: Optional[str] = None,
        outbox_dir: str = "data/comm/outbox",
        inbox_dir: str = "data/comm/inbox",
    ):
        self.instancia_id = instancia_id or str(uuid.uuid4())[:8]
        self.outbox_dir = outbox_dir
        self.inbox_dir = inbox_dir
        self._procesados: set = set()

        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.inbox_dir, exist_ok=True)

    def enviar(self, tipo: str, payload: Dict[str, Any]) -> str:
        """Escribe un mensaje JSON al outbox. Retorna el ID del mensaje."""
        msg_id = f"{self.instancia_id}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        mensaje = {
            "id": msg_id,
            "tipo": tipo,
            "origen": self.instancia_id,
            "timestamp": time.time(),
            "payload": payload,
        }
        ruta = os.path.join(self.outbox_dir, f"{msg_id}.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(mensaje, f, ensure_ascii=False, default=str)
        return msg_id

    def recibir(self, max_mensajes: int = 10) -> List[Dict[str, Any]]:
        """Lee mensajes nuevos del inbox."""
        mensajes: List[Dict[str, Any]] = []
        if not os.path.isdir(self.inbox_dir):
            return mensajes

        archivos = sorted(
            f for f in os.listdir(self.inbox_dir)
            if f.endswith(".json") and f not in self._procesados
        )

        for nombre in archivos[:max_mensajes]:
            ruta = os.path.join(self.inbox_dir, nombre)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    msg = json.load(f)
                mensajes.append(msg)
                self._procesados.add(nombre)
            except (json.JSONDecodeError, IOError):
                continue

        return mensajes

    def compartir_concepto(self, sistema, nombre: str) -> Optional[str]:
        """Comparte un concepto del grafo con otras instancias."""
        if nombre not in sistema.conceptos:
            return None
        data = sistema.conceptos[nombre]
        payload = {
            "nombre": nombre,
            "categoria": data.get("categoria", "emergentes"),
            "vector": data["actual"].tolist() if isinstance(data["actual"], np.ndarray) else list(data["actual"]),
            "fuerza": data.get("fuerza", 1.0),
            "activaciones": data.get("activaciones", 0),
        }
        return self.enviar("concepto", payload)

    def compartir_descubrimiento(
        self, concepto: str, conexiones: List[str], score: float
    ) -> str:
        """Comparte un descubrimiento con otras instancias."""
        payload = {
            "concepto": concepto,
            "conexiones": conexiones,
            "score": score,
        }
        return self.enviar("descubrimiento", payload)

    def absorber_mensajes(self, sistema) -> List[Dict[str, Any]]:
        """Lee inbox y agrega conceptos al grafo."""
        mensajes = self.recibir()
        absorbidos: List[Dict[str, Any]] = []

        for msg in mensajes:
            tipo = msg.get("tipo", "")
            payload = msg.get("payload", {})

            if tipo == "concepto":
                nombre = payload.get("nombre", "")
                if nombre and nombre not in sistema.conceptos:
                    vector = payload.get("vector")
                    atributos = np.array(vector) if vector else None
                    try:
                        sistema.añadir_concepto(
                            nombre,
                            atributos=atributos,
                            categoria=payload.get("categoria", "emergentes"),
                        )
                        absorbidos.append({
                            "tipo": "concepto_absorbido",
                            "nombre": nombre,
                            "origen": msg.get("origen", "desconocido"),
                        })
                    except Exception as e:
                        logger.warning("Error absorbiendo concepto %s: %s", nombre, e)

            elif tipo == "descubrimiento":
                absorbidos.append({
                    "tipo": "descubrimiento_recibido",
                    "concepto": payload.get("concepto", ""),
                    "origen": msg.get("origen", "desconocido"),
                })

            elif tipo == "saludo":
                absorbidos.append({
                    "tipo": "saludo_recibido",
                    "origen": msg.get("origen", "desconocido"),
                })

        return absorbidos

    def anunciar(self, num_conceptos: int = 0) -> str:
        """Anuncia presencia a otras instancias."""
        return self.enviar("saludo", {
            "instancia": self.instancia_id,
            "conceptos": num_conceptos,
            "mensaje": "IANAE presente",
        })

    def estado(self) -> Dict[str, Any]:
        """Estado del canal: conteos de inbox/outbox."""
        outbox_count = len([
            f for f in os.listdir(self.outbox_dir)
            if f.endswith(".json")
        ]) if os.path.isdir(self.outbox_dir) else 0

        inbox_count = len([
            f for f in os.listdir(self.inbox_dir)
            if f.endswith(".json")
        ]) if os.path.isdir(self.inbox_dir) else 0

        return {
            "instancia_id": self.instancia_id,
            "outbox": outbox_count,
            "inbox": inbox_count,
            "procesados": len(self._procesados),
        }
