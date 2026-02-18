#!/usr/bin/env python3
"""
Ianae v3 - Despertar
=====================
Punto de entrada principal.
Despierta la mente, arranca los sentidos, inicia el ciclo autonomo.

Uso:
    python3 despertar.py              # Arrancar el ciclo autonomo
    python3 despertar.py --estado     # Ver estado actual
    python3 despertar.py --diario     # Ver diario de hoy
    python3 despertar.py --pensar     # Un ciclo de pensamiento manual
    python3 despertar.py --reset      # Empezar de cero
"""

import argparse
import signal
import sys
from pathlib import Path

# Asegurar que el directorio de v3 esta en el path
sys.path.insert(0, str(Path(__file__).parent))

from config import ESTADO_FILE
from mente import MenteViva
from sentidos import Sentidos
from diario import Diario
from ciclo import CicloAutonomo


def main():
    parser = argparse.ArgumentParser(description="Ianae v3 - Mente Viva")
    parser.add_argument("--estado", action="store_true", help="Ver estado actual")
    parser.add_argument("--diario", action="store_true", help="Ver diario de hoy")
    parser.add_argument("--pensar", action="store_true", help="Un ciclo manual")
    parser.add_argument("--reset", action="store_true", help="Empezar de cero")
    args = parser.parse_args()

    # Inicializar la mente
    mente = MenteViva()

    if args.reset:
        print("[Ianae] Reset: empezando de cero.")
        if ESTADO_FILE.exists():
            ESTADO_FILE.unlink()
        print("[Ianae] Estado borrado. Ianae nace vacia.")
        return

    # Cargar estado previo si existe
    if mente.cargar():
        print(f"[Ianae] Mente recuperada: {len(mente)} conceptos, {mente.ciclos} ciclos")
    else:
        print("[Ianae] Primera vez. Ianae nace vacia.")

    # Solo estado
    if args.estado:
        estado = mente.estado()
        print(f"\n=== Estado de Ianae ===")
        print(f"  Conceptos vivos: {estado['conceptos_vivos']}")
        print(f"  Conexiones: {estado['conexiones']}")
        print(f"  Ciclos: {estado['ciclos']}")
        print(f"  Creados: {estado['creados_total']}")
        print(f"  Olvidados: {estado['olvidados_total']}")
        print(f"  Top interes:")
        for nombre, score in estado['top_interes']:
            print(f"    - {nombre}: {score}")
        return

    # Solo diario
    if args.diario:
        diario = Diario()
        texto = diario.leer_hoy()
        if texto:
            print(texto)
        else:
            print("[Ianae] No hay diario de hoy.")
        return

    # Sentidos y diario
    sentidos = Sentidos(mente=mente)
    diario = Diario()

    # Ciclo manual
    if args.pensar:
        ciclo = CicloAutonomo(mente, sentidos, diario)
        print("[Ianae] Ejecutando un ciclo de pensamiento...")
        ciclo.ejecutar_ciclo()
        estado = mente.estado()
        print(f"[Ianae] Hecho. {estado['conceptos_vivos']} conceptos, {estado['conexiones']} conexiones")
        print(f"[Ianae] Top: {', '.join(f'{n}({v})' for n, v in estado['top_interes'])}")
        return

    # Ciclo autonomo (modo normal)
    ciclo = CicloAutonomo(mente, sentidos, diario)

    # Manejar señales
    def shutdown(signum, frame):
        print("\n[Ianae] Señal recibida, apagando...")
        ciclo.activo = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print("[Ianae] === MENTE VIVA v3 ===")
    print(f"[Ianae] Ollama: {'SI' if sentidos.ollama_disponible else 'NO (modo simple)'}")
    print(f"[Ianae] Intervalo: {ciclo.mente.ciclos} ciclos previos")
    print("[Ianae] Ctrl+C para detener")
    print()

    ciclo.correr()


if __name__ == "__main__":
    main()
