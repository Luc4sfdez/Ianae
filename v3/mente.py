"""
Ianae v3 - Mente Viva
======================
Red de conceptos que vive, respira y olvida.
Cada concepto tiene fuerza, curiosidad y conexiones.
Lo que se usa se refuerza. Lo que se ignora se desvanece.
"""

import json
import math
import random
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from config import (
    VECTOR_DIM, FUERZA_INICIAL, DECAY_RATE, UMBRAL_OLVIDO,
    CURIOSIDAD_BASE, MAX_CONCEPTOS, CONEXION_MIN, ESTADO_FILE,
)


class Concepto:
    """Un nodo vivo en la red mental."""

    __slots__ = [
        "nombre", "vector", "fuerza", "curiosidad",
        "nacido", "ultimo_acceso", "accesos", "tags",
    ]

    def __init__(self, nombre, vector=None, fuerza=None, curiosidad=None):
        self.nombre = nombre
        self.vector = vector if vector is not None else _vec_aleatorio()
        self.fuerza = fuerza if fuerza is not None else FUERZA_INICIAL
        self.curiosidad = curiosidad if curiosidad is not None else CURIOSIDAD_BASE
        self.nacido = time.time()
        self.ultimo_acceso = time.time()
        self.accesos = 0
        self.tags = set()  # etiquetas libres (fuente, tipo, etc.)

    def tocar(self, boost=0.1):
        """Acceder al concepto lo refuerza."""
        self.ultimo_acceso = time.time()
        self.accesos += 1
        self.fuerza = min(1.0, self.fuerza + boost)

    def decaer(self, rate=DECAY_RATE):
        """El tiempo debilita lo que no se usa."""
        horas_sin_uso = (time.time() - self.ultimo_acceso) / 3600
        decay = rate * math.log1p(horas_sin_uso)
        self.fuerza = max(0.0, self.fuerza - decay)

    def vivo(self):
        return self.fuerza > UMBRAL_OLVIDO

    def edad_horas(self):
        return (time.time() - self.nacido) / 3600

    def interes(self):
        """Cuanto 'llama la atencion' este concepto ahora."""
        recencia = 1.0 / (1.0 + (time.time() - self.ultimo_acceso) / 3600)
        return self.fuerza * self.curiosidad * (1 + recencia)

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "vector": self.vector.tolist(),
            "fuerza": self.fuerza,
            "curiosidad": self.curiosidad,
            "nacido": self.nacido,
            "ultimo_acceso": self.ultimo_acceso,
            "accesos": self.accesos,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d):
        c = cls(
            d["nombre"],
            vector=np.array(d["vector"], dtype=np.float32),
            fuerza=d["fuerza"],
            curiosidad=d.get("curiosidad", CURIOSIDAD_BASE),
        )
        c.nacido = d.get("nacido", time.time())
        c.ultimo_acceso = d.get("ultimo_acceso", time.time())
        c.accesos = d.get("accesos", 0)
        c.tags = set(d.get("tags", []))
        return c


class MenteViva:
    """La mente: una red de conceptos vivos con conexiones ponderadas."""

    def __init__(self):
        self.conceptos = {}                    # nombre -> Concepto
        self.conexiones = defaultdict(dict)    # nombre -> {nombre: peso}
        self.ciclos = 0
        self.conceptos_creados = 0
        self.conceptos_olvidados = 0
        self.pensamientos = []                 # historial breve

    # ── Conceptos ──

    def existe(self, nombre):
        return nombre in self.conceptos

    def crear(self, nombre, vector=None, curiosidad=None, tags=None):
        """Crea un concepto nuevo. Si ya existe, lo refuerza."""
        nombre = nombre.strip().lower()
        if not nombre:
            return None

        if nombre in self.conceptos:
            self.conceptos[nombre].tocar(boost=0.05)
            return self.conceptos[nombre]

        if len(self.conceptos) >= MAX_CONCEPTOS:
            self._podar()

        c = Concepto(nombre, vector=vector, curiosidad=curiosidad)
        if tags:
            c.tags.update(tags)
        self.conceptos[nombre] = c
        self.conceptos_creados += 1
        return c

    def conectar(self, a, b, peso=None):
        """Crea o refuerza una conexion entre dos conceptos."""
        if a not in self.conceptos or b not in self.conceptos:
            return
        if a == b:
            return

        if peso is None:
            # Peso basado en similitud vectorial
            va = self.conceptos[a].vector
            vb = self.conceptos[b].vector
            peso = float(_similitud(va, vb))

        peso = max(CONEXION_MIN, min(1.0, peso))

        # Bidireccional, promediando si ya existe
        for x, y in [(a, b), (b, a)]:
            if y in self.conexiones[x]:
                self.conexiones[x][y] = (self.conexiones[x][y] + peso) / 2
            else:
                self.conexiones[x][y] = peso

    def vecinos(self, nombre, top=5):
        """Devuelve los vecinos mas conectados."""
        if nombre not in self.conexiones:
            return []
        items = sorted(
            self.conexiones[nombre].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return items[:top]

    # ── Activacion / Pensamiento ──

    def activar(self, semilla, pasos=3, temperatura=0.5):
        """Propaga activacion desde un concepto semilla.
        Devuelve los conceptos mas activados (el 'pensamiento')."""
        if semilla not in self.conceptos:
            return []

        activacion = defaultdict(float)
        activacion[semilla] = 1.0
        self.conceptos[semilla].tocar()

        for paso in range(pasos):
            nueva = defaultdict(float)
            for nombre, nivel in activacion.items():
                if nivel < 0.01:
                    continue
                for vecino, peso in self.conexiones.get(nombre, {}).items():
                    if vecino in self.conceptos and self.conceptos[vecino].vivo():
                        ruido = random.gauss(0, temperatura * 0.1)
                        nueva[vecino] += nivel * peso * (1 + ruido)

            # Normalizar
            if nueva:
                maximo = max(nueva.values())
                if maximo > 0:
                    for k in nueva:
                        nueva[k] /= maximo

            # Combinar con activacion previa (decae)
            for k, v in nueva.items():
                activacion[k] = max(activacion[k] * 0.5, v)

        # Tocar los mas activados
        resultado = sorted(activacion.items(), key=lambda x: x[1], reverse=True)
        for nombre, nivel in resultado[:5]:
            if nombre in self.conceptos:
                self.conceptos[nombre].tocar(boost=nivel * 0.05)

        return resultado[:10]

    def pensar(self, semilla=None, pasos=4):
        """Genera una cadena de pensamiento.
        Si no hay semilla, elige el concepto mas 'interesante'."""
        if not self.conceptos:
            return []

        if semilla is None:
            semilla = self._mas_interesante()

        cadena = [semilla]
        actual = semilla

        for _ in range(pasos):
            activados = self.activar(actual, pasos=2)
            # Filtrar los que ya estan en la cadena
            candidatos = [(n, v) for n, v in activados if n not in cadena]
            if not candidatos:
                break

            # 70% mejor, 30% aleatorio (creatividad)
            if random.random() < 0.7 and candidatos:
                siguiente = candidatos[0][0]
            else:
                pesos = [v for _, v in candidatos]
                total = sum(pesos)
                if total > 0:
                    pesos = [p / total for p in pesos]
                    siguiente = random.choices(
                        [n for n, _ in candidatos], weights=pesos, k=1
                    )[0]
                else:
                    siguiente = random.choice([n for n, _ in candidatos])

            cadena.append(siguiente)
            actual = siguiente

        # Registrar pensamiento
        self.pensamientos.append({
            "cadena": cadena,
            "tiempo": datetime.now().isoformat(),
        })
        if len(self.pensamientos) > 100:
            self.pensamientos = self.pensamientos[-50:]

        return cadena

    def generar_concepto(self):
        """Crea un concepto nuevo combinando dos existentes.
        Como 'tener una idea' mezclando cosas."""
        if len(self.conceptos) < 2:
            return None

        # Elegir dos conceptos activos
        vivos = [c for c in self.conceptos.values() if c.vivo()]
        if len(vivos) < 2:
            return None

        pesos = [c.interes() for c in vivos]
        total = sum(pesos)
        if total == 0:
            padres = random.sample(vivos, 2)
        else:
            pesos_norm = [p / total for p in pesos]
            padres = list(np.random.choice(vivos, size=2, replace=False, p=pesos_norm))

        a, b = padres[0], padres[1]

        # Nuevo vector: mezcla + mutacion
        ratio = random.uniform(0.3, 0.7)
        nuevo_vec = a.vector * ratio + b.vector * (1 - ratio)
        mutacion = np.random.normal(0, 0.1, VECTOR_DIM).astype(np.float32)
        nuevo_vec = _normalizar(nuevo_vec + mutacion)

        # Nombre: combinacion
        nombre = f"{a.nombre}+{b.nombre}"

        nuevo = self.crear(nombre, vector=nuevo_vec, tags={"generado", "mezcla"})
        if nuevo and nuevo.accesos <= 1:  # recien creado
            self.conectar(nuevo.nombre, a.nombre, peso=0.6)
            self.conectar(nuevo.nombre, b.nombre, peso=0.6)

        return nuevo

    # ── Ciclo de vida ──

    def ciclo(self):
        """Un ciclo vital: decaer, olvidar, pensar."""
        self.ciclos += 1

        # Decaer todo
        for c in list(self.conceptos.values()):
            c.decaer()

        # Olvidar lo muerto
        olvidados = [n for n, c in self.conceptos.items() if not c.vivo()]
        for nombre in olvidados:
            self._olvidar(nombre)

        # Reforzar conexiones entre conceptos co-activos recientes
        recientes = sorted(
            self.conceptos.values(),
            key=lambda c: c.ultimo_acceso,
            reverse=True,
        )[:10]
        for i, a in enumerate(recientes):
            for b in recientes[i + 1:]:
                if a.nombre in self.conexiones and b.nombre in self.conexiones[a.nombre]:
                    self.conexiones[a.nombre][b.nombre] = min(
                        1.0, self.conexiones[a.nombre][b.nombre] + 0.01
                    )

        # Debilitar conexiones viejas
        for nombre in list(self.conexiones):
            for vecino in list(self.conexiones[nombre]):
                self.conexiones[nombre][vecino] *= 0.998
                if self.conexiones[nombre][vecino] < CONEXION_MIN:
                    del self.conexiones[nombre][vecino]
            if not self.conexiones[nombre]:
                del self.conexiones[nombre]

    def sonar(self):
        """Reprocessar memorias: activar conceptos aleatorios y ver que emerge.
        Como sonar."""
        if len(self.conceptos) < 3:
            return []

        vivos = [c for c in self.conceptos.values() if c.vivo()]
        if len(vivos) < 2:
            return []

        # Elegir 2-3 conceptos al azar y activarlos juntos
        n = min(3, len(vivos))
        semillas = random.sample(vivos, n)

        activacion = defaultdict(float)
        for s in semillas:
            for nombre, nivel in self.activar(s.nombre, pasos=2, temperatura=0.8):
                activacion[nombre] += nivel

        # Si dos conceptos no conectados se activan juntos, conectarlos
        top = sorted(activacion.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (a, _) in enumerate(top):
            for b, _ in top[i + 1:]:
                if b not in self.conexiones.get(a, {}):
                    self.conectar(a, b, peso=0.3)

        return [(n, v) for n, v in top]

    # ── Utilidades ──

    def _mas_interesante(self):
        """El concepto que mas 'llama la atencion' ahora."""
        mejor = max(self.conceptos.values(), key=lambda c: c.interes())
        return mejor.nombre

    def _olvidar(self, nombre):
        """Eliminar un concepto de la mente."""
        if nombre in self.conceptos:
            del self.conceptos[nombre]
            self.conceptos_olvidados += 1
        if nombre in self.conexiones:
            del self.conexiones[nombre]
        for n in list(self.conexiones):
            self.conexiones[n].pop(nombre, None)

    def _podar(self):
        """Eliminar los conceptos mas debiles para hacer espacio."""
        debiles = sorted(
            self.conceptos.values(),
            key=lambda c: c.fuerza,
        )
        # Quitar el 10%
        n_quitar = max(1, len(debiles) // 10)
        for c in debiles[:n_quitar]:
            self._olvidar(c.nombre)

    def estado(self):
        """Resumen del estado actual."""
        vivos = [c for c in self.conceptos.values() if c.vivo()]
        n_conexiones = sum(len(v) for v in self.conexiones.values()) // 2
        top = sorted(vivos, key=lambda c: c.interes(), reverse=True)[:5]
        return {
            "conceptos_vivos": len(vivos),
            "conexiones": n_conexiones,
            "ciclos": self.ciclos,
            "creados_total": self.conceptos_creados,
            "olvidados_total": self.conceptos_olvidados,
            "top_interes": [(c.nombre, round(c.interes(), 3)) for c in top],
        }

    # ── Persistencia ──

    def guardar(self, path=None):
        path = path or ESTADO_FILE
        data = {
            "version": 3,
            "guardado": datetime.now().isoformat(),
            "ciclos": self.ciclos,
            "conceptos_creados": self.conceptos_creados,
            "conceptos_olvidados": self.conceptos_olvidados,
            "conceptos": {n: c.to_dict() for n, c in self.conceptos.items()},
            "conexiones": {
                k: dict(v) for k, v in self.conexiones.items() if v
            },
            "pensamientos": self.pensamientos[-20:],
        }
        tmp = Path(str(path) + ".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.rename(path)

    def cargar(self, path=None):
        path = path or ESTADO_FILE
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        self.ciclos = data.get("ciclos", 0)
        self.conceptos_creados = data.get("conceptos_creados", 0)
        self.conceptos_olvidados = data.get("conceptos_olvidados", 0)
        self.pensamientos = data.get("pensamientos", [])
        for nombre, d in data.get("conceptos", {}).items():
            self.conceptos[nombre] = Concepto.from_dict(d)
        for nombre, vecinos in data.get("conexiones", {}).items():
            self.conexiones[nombre] = dict(vecinos)
        return True

    def __len__(self):
        return len(self.conceptos)

    def __repr__(self):
        return f"<MenteViva: {len(self.conceptos)} conceptos, {self.ciclos} ciclos>"


# ── Helpers ──

def _vec_aleatorio():
    v = np.random.randn(VECTOR_DIM).astype(np.float32)
    return _normalizar(v)


def _normalizar(v):
    norma = np.linalg.norm(v)
    if norma > 0:
        return v / norma
    return v


def _similitud(a, b):
    """Similitud coseno entre dos vectores."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
