"""
Ianae v3 - Diario
==================
Escribe lo que piensa y observa.
Un archivo por dia, formato markdown.
"""

from datetime import datetime
from pathlib import Path

from config import DIARIO_DIR


class Diario:
    """El diario de Ianae: registro de sus observaciones y pensamientos."""

    def __init__(self):
        self.entradas_hoy = 0

    def _archivo_hoy(self):
        return DIARIO_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"

    def escribir(self, tipo, contenido, estado_mente=None):
        """Escribe una entrada en el diario."""
        archivo = self._archivo_hoy()
        ahora = datetime.now().strftime("%H:%M:%S")
        es_nuevo = not archivo.exists()

        with open(archivo, "a") as f:
            if es_nuevo:
                f.write(f"# Diario de Ianae - {datetime.now().strftime('%Y-%m-%d')}\n\n")

            emoji = {
                "observacion": "👁️",
                "pensamiento": "💭",
                "conexion": "🔗",
                "idea": "💡",
                "sueno": "🌙",
                "despertar": "🌅",
                "curiosidad": "🔍",
                "olvido": "🍂",
                "hablar": "📢",
                "estado": "📊",
            }.get(tipo, "📝")

            f.write(f"### {emoji} [{ahora}] {tipo.capitalize()}\n\n")
            f.write(f"{contenido}\n\n")

            if estado_mente:
                f.write(f"*Estado: {estado_mente['conceptos_vivos']} conceptos, ")
                f.write(f"{estado_mente['conexiones']} conexiones, ")
                f.write(f"ciclo #{estado_mente['ciclos']}*\n\n")

            f.write("---\n\n")

        self.entradas_hoy += 1

    def leer_hoy(self):
        """Lee el diario de hoy."""
        archivo = self._archivo_hoy()
        if archivo.exists():
            return archivo.read_text()
        return ""

    def ultimas_entradas(self, n=5):
        """Lee las ultimas N entradas de los diarios recientes."""
        archivos = sorted(DIARIO_DIR.glob("*.md"), reverse=True)
        entradas = []
        for archivo in archivos[:3]:
            texto = archivo.read_text()
            bloques = texto.split("---")
            for bloque in reversed(bloques):
                bloque = bloque.strip()
                if bloque and "###" in bloque:
                    entradas.append(bloque)
                    if len(entradas) >= n:
                        return entradas
        return entradas
