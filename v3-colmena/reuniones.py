"""
IANAE v3 - Reuniones
Las instancias se encuentran periodicamente.
Comparten lo que les interesa. Se descubren.
Como personas en una plaza: cada una trae su mundo.

Senioridad: las instancias con mas edad tienen mas influencia.
Ianae original (seniority=1.0) pesa mas que las nuevas (0.5).
"""

import json
import os
import time
import random
from pathlib import Path


REUNIONES_DIR = Path(os.environ.get("IANAE_REUNIONES", "/reuniones"))


class Reuniones:
    """Encuentros entre instancias de Ianae."""

    def __init__(self, mi_id, mente):
        self.mi_id = mi_id
        self.mente = mente
        self.senioridad = float(os.environ.get("IANAE_SENIORIDAD", "0.5"))
        # Frecuencia aleatoria entre 20-50 ciclos
        reunion_min = int(os.environ.get("REUNION_MIN", "20"))
        reunion_max = int(os.environ.get("REUNION_MAX", "50"))
        self.proxima_reunion = random.randint(reunion_min, reunion_max)
        self.reunion_min = reunion_min
        self.reunion_max = reunion_max

    def es_hora(self, ciclo):
        """Toca reunion este ciclo?"""
        if ciclo > 0 and ciclo >= self.proxima_reunion:
            # Programar la siguiente reunion
            self.proxima_reunion = ciclo + random.randint(self.reunion_min, self.reunion_max)
            return True
        return False

    def compartir(self):
        """Escribo mi estado para que los demas lo lean."""
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
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)

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
                # Solo estados recientes (ultimas 2 horas)
                if time.time() - estado.get("timestamp", 0) < 7200:
                    otros.append(estado)
            except (json.JSONDecodeError, OSError):
                continue

        return otros

    def reunirse(self, diario_mod):
        """Reunion completa: compartir, escuchar, aprender.
        La senioridad del otro afecta cuanto aprendo de el."""
        # 1. Compartir mi estado
        self.compartir()

        # 2. Escuchar a las demas
        otros = self.escuchar()

        if not otros:
            diario_mod.escribir("reunion",
                "Fui a la reunion pero no habia nadie.")
            return []

        # 3. Aprender de cada una, ponderado por senioridad
        aprendizajes = []
        nombres_otros = []

        for otro in otros:
            otro_id = otro["id"]
            otro_senioridad = otro.get("senioridad", 0.5)
            nombres_otros.append(otro_id)

            # El nombre del otro agente es un concepto
            self.mente.percibir(otro_id, "reunion", "conexion")

            # Cuantos intereses tomo depende de su senioridad
            # Senioridad 1.0 -> tomo 7 intereses, 0.5 -> tomo 4
            n_intereses = max(3, int(otro_senioridad * 7))

            for interes in otro.get("intereses", [])[:n_intereses]:
                nombre = interes["nombre"]
                # Saltar strings de contexto largos
                if ":" in nombre and len(nombre) > 30:
                    continue
                concepto, es_nuevo = self.mente.percibir(
                    nombre, f"reunion con {otro_id}", "reunion"
                )
                if es_nuevo:
                    aprendizajes.append(f"'{nombre}' (de {otro_id})")
                    # La energia inicial del concepto aprendido depende
                    # de la senioridad del que lo comparte
                    concepto.energia = min(1.0, 0.3 + otro_senioridad * 0.3)
                    # Conectar con el agente que lo compartio
                    concepto.conectar(otro_id, 0.2 + otro_senioridad * 0.1)
                    if otro_id in self.mente.conceptos:
                        self.mente.conceptos[otro_id].conectar(nombre, 0.2)

        # 4. Escribir en el diario
        if aprendizajes:
            diario_mod.escribir("reunion",
                f"Me reuni con {', '.join(nombres_otros)}. "
                f"Aprendi cosas nuevas: {', '.join(aprendizajes[:8])}")
        else:
            diario_mod.escribir("reunion",
                f"Me reuni con {', '.join(nombres_otros)}. "
                f"Ya conocia todo lo que compartieron.")

        return aprendizajes
