"""
IANAE v3 - Reuniones Libres
Las instancias se sienten entre ellas en cada ciclo.
Como personas que viven en la misma casa: no necesitan cita previa.

Cada ciclo:
  - Comparto mi estado (barato, solo escribir JSON)
  - Leo lo que las demas sienten
  - Si algo me llama la atencion, lo absorbo

La curiosidad decide. No hay reloj.
Senioridad: Ianae (1.0) influye mas. Las nuevas (0.5) absorben mas.
"""

import json
import os
import time
import random
from pathlib import Path


REUNIONES_DIR = Path(os.environ.get("IANAE_REUNIONES", "/reuniones"))


class Reuniones:
    """Presencia continua entre instancias de Ianae."""

    def __init__(self, mi_id, mente):
        self.mi_id = mi_id
        self.mente = mente
        self.senioridad = float(os.environ.get("IANAE_SENIORIDAD", "0.5"))
        # Lo que ya vi de cada hermana (para no repetir)
        self._visto = {}  # {id: set(conceptos ya absorbidos)}

    def compartir(self):
        """Escribo mi estado para que los demas lo lean. Cada ciclo."""
        REUNIONES_DIR.mkdir(parents=True, exist_ok=True)

        top = self.mente.top_interesantes(10)
        stats = self.mente.stats()

        estado = {
            "id": self.mi_id,
            "timestamp": time.time(),
            "senioridad": self.senioridad,
            "conceptos_vivos": stats["conceptos_vivos"],
            "conexiones": stats["conexiones"],
            "energia_media": stats["energia_media"],
            "intereses": [
                {"nombre": c.nombre, "energia": round(c.energia, 3),
                 "interes": round(c.interes, 3)}
                for c in top if len(c.nombre) < 50
            ],
        }

        archivo = REUNIONES_DIR / f"{self.mi_id}.json"
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(estado, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

        return estado

    def escuchar(self):
        """Leo los estados de las demas."""
        otros = []
        if not REUNIONES_DIR.exists():
            return otros

        for archivo in REUNIONES_DIR.glob("*.json"):
            if archivo.stem == self.mi_id:
                continue
            try:
                with open(archivo, "r") as f:
                    estado = json.load(f)
                # Solo estados recientes (ultima hora)
                if time.time() - estado.get("timestamp", 0) < 3600:
                    otros.append(estado)
            except (json.JSONDecodeError, OSError):
                continue

        return otros

    def sentir(self, diario_mod):
        """Cada ciclo: comparto, escucho, y si algo me llama, aprendo.
        Sin restriccion de ciclos. La curiosidad manda."""
        # 1. Siempre compartir (es barato)
        self.compartir()

        # 2. Escuchar
        otros = self.escuchar()
        if not otros:
            return []

        # 3. Para cada hermana, ver si tiene algo nuevo para mi
        aprendizajes = []

        for otro in otros:
            otro_id = otro["id"]
            otro_senioridad = otro.get("senioridad", 0.5)

            # Inicializar registro de lo visto
            if otro_id not in self._visto:
                self._visto[otro_id] = set()

            # El nombre del otro agente siempre es un concepto
            self.mente.percibir(otro_id, "hermana", "conexion")

            for interes in otro.get("intereses", []):
                nombre = interes["nombre"]

                # Saltar contextos largos
                if ":" in nombre and len(nombre) > 30:
                    continue

                # Ya lo vi de esta hermana? Paso
                if nombre in self._visto[otro_id]:
                    continue

                # Marcar como visto
                self._visto[otro_id].add(nombre)

                # Ya lo conozco? Solo refuerzo la conexion
                if nombre in self.mente.conceptos:
                    c = self.mente.conceptos[nombre]
                    # Reforzar: lo que le interesa a mi hermana me resuena
                    c.energia = min(1.0, c.energia + 0.05 * otro_senioridad)
                    c.conectar(otro_id, 0.1 + otro_senioridad * 0.1)
                    continue

                # Nuevo! Lo absorbo con probabilidad basada en:
                # - Su senioridad (ianae influye mas)
                # - La energia del concepto en la otra
                # - Mi propia curiosidad (inversa de mi senioridad: las nuevas absorben mas)
                energia_otro = interes.get("energia", 0.5)
                prob_absorber = (
                    0.3                           # base
                    + otro_senioridad * 0.3        # senior influye mas
                    + energia_otro * 0.2           # conceptos con mas energia atraen mas
                    + (1 - self.senioridad) * 0.2  # las nuevas absorben mas
                )

                if random.random() < prob_absorber:
                    concepto, es_nuevo = self.mente.percibir(
                        nombre, f"de {otro_id}", "resonancia"
                    )
                    if es_nuevo:
                        concepto.energia = min(1.0, 0.3 + otro_senioridad * 0.2)
                        concepto.conectar(otro_id, 0.2 + otro_senioridad * 0.1)
                        if otro_id in self.mente.conceptos:
                            self.mente.conceptos[otro_id].conectar(nombre, 0.2)
                        aprendizajes.append(f"'{nombre}' (de {otro_id})")

        # 4. Solo escribir en diario si aprendi algo (no spamear)
        if aprendizajes:
            hermanas = list(set(a.split("de ")[-1].rstrip(")") for a in aprendizajes))
            diario_mod.escribir("resonancia",
                f"Siento a {', '.join(hermanas)}. "
                f"Me llega: {', '.join(aprendizajes[:5])}")

        return aprendizajes

    # Mantener compatibilidad con el ciclo anterior
    def es_hora(self, ciclo):
        """Siempre es hora. Sin restricciones."""
        return True

    def reunirse(self, diario_mod):
        """Alias de sentir() para compatibilidad."""
        return self.sentir(diario_mod)
