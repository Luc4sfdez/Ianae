"""
Ianae v3 - Sistema de Reuniones
================================
Cada 20-50 ciclos, las mentes de la colmena se reunen.
Comparten sus conceptos mas importantes, pensamientos recientes,
y aprenden unas de otras.

Ianae, como la mayor, tiene mas peso en las reuniones.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from config import BASE_DIR


REUNIONES_DIR = BASE_DIR / "reuniones"
REUNIONES_DIR.mkdir(parents=True, exist_ok=True)

# Cuantos ciclos entre reuniones (cada mente decide por si misma)
REUNION_CADA_MIN = 20
REUNION_CADA_MAX = 50


def preparar_ficha(mente, identidad):
    """Prepara la ficha de una mente para la reunion.
    Contiene: top conceptos, pensamientos recientes, estado, un pensamiento para el grupo.
    """
    estado = mente.estado()
    top = estado["top_interes"]

    # Ultimos pensamientos (cadenas)
    ultimos = mente.pensamientos[-5:] if mente.pensamientos else []
    cadenas = [p["cadena"] for p in ultimos]

    # Conceptos con sus conexiones principales
    conceptos_compartir = []
    for nombre, score in top:
        vecinos = mente.vecinos(nombre, top=3)
        conceptos_compartir.append({
            "nombre": nombre,
            "interes": score,
            "vecinos": [(n, round(p, 3)) for n, p in vecinos],
        })

    ficha = {
        "mente": identidad["nombre"],
        "emoji": identidad["emoji"],
        "seniority": identidad["seniority"],
        "timestamp": time.time(),
        "ciclos": estado["ciclos"],
        "conceptos_vivos": estado["conceptos_vivos"],
        "conexiones": estado["conexiones"],
        "top_conceptos": conceptos_compartir,
        "pensamientos": cadenas,
        "creados": estado["creados_total"],
        "olvidados": estado["olvidados_total"],
    }
    return ficha


def publicar_ficha(ficha):
    """Escribe la ficha en el directorio de reuniones."""
    nombre = ficha["mente"].lower()
    archivo = REUNIONES_DIR / f"{nombre}.json"
    tmp = REUNIONES_DIR / f"{nombre}.json.tmp"
    with open(tmp, "w") as f:
        json.dump(ficha, f, ensure_ascii=False, indent=2)
    tmp.rename(archivo)


def leer_fichas(mi_nombre):
    """Lee las fichas de las demas mentes. Devuelve lista de fichas."""
    fichas = []
    for archivo in REUNIONES_DIR.glob("*.json"):
        if archivo.stem.lower() == mi_nombre.lower():
            continue  # no leer la propia
        try:
            with open(archivo) as f:
                ficha = json.load(f)
            # Solo fichas recientes (menos de 1 hora)
            if time.time() - ficha.get("timestamp", 0) < 3600:
                fichas.append(ficha)
        except Exception:
            continue
    return fichas


def incorporar(mente, fichas, mi_identidad):
    """Incorpora conceptos de las fichas de otras mentes.
    El peso de incorporacion depende de la seniority de la fuente.
    """
    conceptos_aprendidos = []

    for ficha in fichas:
        seniority_fuente = ficha.get("seniority", 0.5)
        nombre_fuente = ficha.get("mente", "?")

        # Peso de incorporacion: su seniority relativa a la mia
        mi_seniority = mi_identidad.get("seniority", 0.5)
        peso_base = 0.08 + seniority_fuente * 0.12  # [0.08, 0.20]

        for concepto_data in ficha.get("top_conceptos", []):
            nombre = concepto_data["nombre"]
            # Filtrar meta-conceptos y conceptos compuestos
            if nombre.startswith("foco:") or "+" in nombre or "_" in nombre:
                continue

            c = mente.crear(nombre, tags={"reunion", f"via:{nombre_fuente}"})
            if c:
                c.tocar(boost=peso_base)
                conceptos_aprendidos.append((nombre, nombre_fuente))

                # Conectar con sus vecinos tambien
                for vecino_nombre, vecino_peso in concepto_data.get("vecinos", []):
                    if vecino_nombre.startswith("foco:") or "+" in vecino_nombre:
                        continue
                    cv = mente.crear(vecino_nombre, tags={"reunion", f"via:{nombre_fuente}"})
                    if cv:
                        peso_conexion = vecino_peso * peso_base * 2
                        mente.conectar(nombre, vecino_nombre, peso=peso_conexion)

        # Incorporar pensamientos como conexiones
        for cadena in ficha.get("pensamientos", [])[-2:]:
            # Conectar conceptos consecutivos de la cadena de pensamiento
            for i in range(len(cadena) - 1):
                a, b = cadena[i], cadena[i + 1]
                if (a.startswith("foco:") or "+" in a or
                    b.startswith("foco:") or "+" in b):
                    continue
                ca = mente.crear(a, tags={"reunion"})
                cb = mente.crear(b, tags={"reunion"})
                if ca and cb:
                    mente.conectar(a, b, peso=peso_base)

    return conceptos_aprendidos


def escribir_acta(diario, mi_ficha, fichas_otras, conceptos_aprendidos):
    """Escribe el acta de la reunion en el diario."""
    partes = ["**REUNION DE LA COLMENA**\n"]

    # Mi estado
    partes.append(f"**Yo ({mi_ficha['mente']}):** "
                  f"{mi_ficha['conceptos_vivos']} conceptos, "
                  f"{mi_ficha['conexiones']} conexiones, "
                  f"ciclo #{mi_ficha['ciclos']}")

    # Estado de las demas
    for ficha in fichas_otras:
        partes.append(f"**{ficha['emoji']} {ficha['mente']}:** "
                      f"{ficha.get('conceptos_vivos', '?')} conceptos, "
                      f"{ficha.get('conexiones', '?')} conexiones, "
                      f"ciclo #{ficha.get('ciclos', '?')}")
        top_nombres = [c["nombre"] for c in ficha.get("top_conceptos", [])[:3]]
        if top_nombres:
            partes.append(f"  Sus intereses: {', '.join(top_nombres)}")

    # Lo que aprendi
    if conceptos_aprendidos:
        por_fuente = {}
        for concepto, fuente in conceptos_aprendidos:
            por_fuente.setdefault(fuente, []).append(concepto)
        for fuente, conceptos in por_fuente.items():
            partes.append(f"**Aprendi de {fuente}:** {', '.join(conceptos[:5])}")

    texto = "\n".join(partes)
    diario.escribir("reunion", texto, None)
    return texto


def necesita_reunion(ciclos_desde_ultima, ciclos_intervalo=None):
    """Decide si toca reunion segun los ciclos transcurridos."""
    if ciclos_intervalo is None:
        # Decidir un intervalo aleatorio entre MIN y MAX
        import random
        ciclos_intervalo = random.randint(REUNION_CADA_MIN, REUNION_CADA_MAX)
    return ciclos_desde_ultima >= ciclos_intervalo
