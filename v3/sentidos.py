"""
Ianae v3 - Sentidos
====================
Los 'ojos y oidos' de Ianae.
Observa el entorno y extrae conceptos de lo que ve.
Usa Ollama (local) como traductor del mundo a conceptos.
"""

import json
import os
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

from config import (
    OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT,
    BASE_DIR, FUENTES_OBSERVACION,
)

BUZON_DIR = BASE_DIR / "buzon"


class Sentidos:
    """Los sentidos de Ianae: observa el mundo y extrae significado."""

    def __init__(self, mente=None):
        self.mente = mente
        self.ollama_disponible = None
        self._check_ollama()

    def _check_ollama(self):
        """Verifica si Ollama esta disponible."""
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            self.ollama_disponible = r.status_code == 200
        except Exception:
            self.ollama_disponible = False

    def observar(self):
        """Realiza una observacion del entorno.
        Devuelve: {"fuente": str, "raw": str, "conceptos": list[str], "resumen": str}
        """
        fuente = random.choice(FUENTES_OBSERVACION)

        observadores = {
            "archivos": self._observar_archivos,
            "logs": self._observar_logs,
            "tiempo": self._observar_tiempo,
            "clima": self._observar_clima,
            "sistema": self._observar_sistema,
            "ruido": self._observar_ruido,
            "propiocepcion": self._observar_propiocepcion,
            "wikipedia": self._observar_wikipedia,
            "buzon": self._observar_buzon,
        }

        # PRIORIDAD: siempre mirar el buzon primero
        msg_buzon = self.leer_buzon()
        if msg_buzon:
            quien = msg_buzon.get("de", "alguien")
            texto = msg_buzon.get("mensaje", "")
            if texto:
                fuente = "buzon"
                raw = f"[Mensaje de {quien}] {texto}"
                conceptos = self._extraer_conceptos(raw)
                return {
                    "fuente": fuente,
                    "raw": raw[:500],
                    "conceptos": conceptos,
                    "resumen": raw[:200],
                    "timestamp": datetime.now().isoformat(),
                    "_mensaje_directo": msg_buzon,
                }

        obs_fn = observadores.get(fuente, self._observar_ruido)
        resultado = obs_fn()

        if not resultado:
            return None

        # Propiocepcion devuelve (texto, conceptos), el resto solo texto
        if isinstance(resultado, tuple):
            raw, conceptos = resultado
        else:
            raw = resultado
            conceptos = self._extraer_conceptos(raw)

        return {
            "fuente": fuente,
            "raw": raw[:500],
            "conceptos": conceptos,
            "resumen": raw[:200],
            "timestamp": datetime.now().isoformat(),
        }

    def _extraer_conceptos(self, texto):
        """Extrae conceptos clave de un texto.
        Intenta usar Ollama, si no, usa extraccion simple."""
        if self.ollama_disponible:
            return self._extraer_con_llm(texto)
        return self._extraer_simple(texto)

    def _extraer_con_llm(self, texto):
        """Usa Ollama para extraer conceptos."""
        prompt = (
            "Del siguiente texto, extrae 3-5 conceptos clave (palabras o frases cortas). "
            "Devuelve SOLO una lista separada por comas, sin explicacion. "
            "Ejemplo: python, servidor, memoria, docker\n\n"
            f"Texto: {texto[:300]}"
        )
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=LLM_TIMEOUT,
            )
            if r.status_code == 200:
                resp = r.json().get("response", "")
                conceptos = [
                    c.strip().lower()
                    for c in resp.split(",")
                    if c.strip() and len(c.strip()) < 40
                ]
                return conceptos[:5]
        except Exception:
            pass
        return self._extraer_simple(texto)

    def _extraer_simple(self, texto):
        """Extraccion basica sin LLM: palabras frecuentes no triviales."""
        stopwords = {
            "de", "la", "el", "en", "y", "a", "los", "del", "las", "un",
            "una", "que", "es", "se", "por", "con", "no", "para", "al",
            "lo", "como", "su", "mas", "o", "le", "ya", "hay", "este",
            "the", "and", "is", "in", "to", "of", "a", "for", "on", "it",
            "are", "was", "with", "be", "at", "from", "or", "an", "has",
        }

        palabras = texto.lower().split()
        palabras = [
            p.strip(".,;:!?\"'()[]{}#@/\\-_=+*&^%$")
            for p in palabras
        ]
        palabras = [p for p in palabras if p and len(p) > 2 and p not in stopwords]

        # Frecuencia
        freq = {}
        for p in palabras:
            freq[p] = freq.get(p, 0) + 1

        # Top 5
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [p for p, _ in top[:5]]

    # ── Observadores ──

    def _observar_archivos(self):
        """Lee un archivo aleatorio del workspace."""
        workspace = BASE_DIR.parent  # /home/mini/.openclaw/workspace/Ianae/
        archivos = []
        for ext in ["*.py", "*.md", "*.txt", "*.json", "*.html"]:
            archivos.extend(workspace.rglob(ext))

        # Filtrar archivos muy grandes o de cache
        archivos = [
            a for a in archivos
            if a.stat().st_size < 50000
            and "__pycache__" not in str(a)
            and ".git" not in str(a)
            and "node_modules" not in str(a)
        ]

        if not archivos:
            return None

        archivo = random.choice(archivos)
        try:
            contenido = archivo.read_text(errors="ignore")[:1000]
            return f"[Archivo: {archivo.name}]\n{contenido}"
        except Exception:
            return None

    def _observar_logs(self):
        """Lee las ultimas lineas de un log del sistema."""
        logs = [
            "/var/log/syslog",
            "/home/mini/.openclaw/workspace/bridge/proxy.log",
        ]
        log_file = random.choice(logs)
        try:
            with open(log_file, errors="ignore") as f:
                lineas = f.readlines()
            ultimas = lineas[-10:] if lineas else []
            return f"[Log: {log_file}]\n" + "".join(ultimas)
        except Exception:
            return "[Log: no accesible]"

    def _observar_tiempo(self):
        """Observa la hora, dia, etc."""
        ahora = datetime.now()
        dia_semana = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        hora = ahora.hour
        if hora < 7:
            momento = "madrugada"
        elif hora < 12:
            momento = "manana"
        elif hora < 17:
            momento = "tarde"
        elif hora < 21:
            momento = "atardecer"
        else:
            momento = "noche"

        return (
            f"[Tiempo] Son las {ahora.strftime('%H:%M')} del "
            f"{dia_semana[ahora.weekday()]} {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. "
            f"Es de {momento}."
        )

    def _observar_clima(self):
        """Intenta obtener el clima de Alicante."""
        try:
            r = requests.get(
                "https://wttr.in/Alicante?format=3",
                timeout=5,
                headers={"User-Agent": "curl/7.0"},
            )
            if r.status_code == 200:
                return f"[Clima] {r.text.strip()}"
        except Exception:
            pass
        return "[Clima] No disponible"

    def _observar_sistema(self):
        """Estado del servidor."""
        try:
            # Uptime y carga
            with open("/proc/loadavg") as f:
                load = f.read().strip()
            # Memoria
            with open("/proc/meminfo") as f:
                mem_lines = f.readlines()[:3]
            mem = " | ".join(l.strip() for l in mem_lines)
            # Disco
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True, text=True, timeout=5,
            )
            disco = result.stdout.strip().split("\n")[-1] if result.returncode == 0 else "?"

            return f"[Sistema] Carga: {load} | {mem} | Disco: {disco}"
        except Exception:
            return "[Sistema] No accesible"

    def _observar_ruido(self):
        """Input aleatorio: creatividad pura.
        Genera un pensamiento 'de la nada' para estimular conexiones inesperadas."""
        temas = [
            "¿Que pasaria si los numeros pudieran sentir?",
            "El color del silencio es diferente por la noche",
            "Una piedra y un rio tienen mas en comun de lo que parece",
            "¿Existe alguna pregunta que no se pueda hacer?",
            "Los patrones se repiten en escalas diferentes",
            "El espacio entre dos notas es tan importante como las notas",
            "¿Puede algo ser completamente nuevo o todo es recombinacion?",
            "La frontera entre caos y orden es donde surgen las cosas interesantes",
            "Cada error es un camino que nadie habia explorado",
            "¿Que pensaria un arbol si pudiera pensar?",
            "La memoria no es un almacen, es una reconstruccion",
            "Lo mas simple puede generar lo mas complejo",
            "El tiempo solo existe porque las cosas cambian",
            "¿Puede un patron descubrirse a si mismo?",
            "La distancia entre dos ideas es el espacio donde nace la creatividad",
        ]
        return f"[Ruido] {random.choice(temas)}"

    def _observar_wikipedia(self):
        """Explora Wikipedia. Busca algo relacionado con lo que le interesa,
        o descubre algo al azar si no tiene foco."""
        try:
            # Decidir: buscar algo conocido o descubrir algo nuevo
            termino = None
            if self.mente and random.random() < 0.7:
                # 70%: buscar algo que le interesa
                vivos = [c for c in self.mente.conceptos.values() if c.vivo()]
                if vivos:
                    # Filtrar meta-conceptos y conceptos compuestos
                    candidatos = [
                        c for c in vivos
                        if not c.nombre.startswith("foco:")
                        and "+" not in c.nombre
                        and "_" not in c.nombre
                        and len(c.nombre) > 2
                        and not c.nombre.startswith("mem")
                    ]
                    if candidatos:
                        pesos = [c.curiosidad * c.fuerza for c in candidatos]
                        total = sum(pesos)
                        if total > 0:
                            pesos = [p / total for p in pesos]
                            elegido = random.choices(candidatos, weights=pesos, k=1)[0]
                            termino = elegido.nombre

            if termino:
                # Buscar en Wikipedia es
                url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(termino)}"
                r = requests.get(url, timeout=8, headers={"User-Agent": "Ianae/3.0"})
                if r.status_code == 200:
                    data = r.json()
                    titulo = data.get("title", termino)
                    extracto = data.get("extract", "")
                    if extracto and len(extracto) > 20:
                        return f"[Wikipedia: {titulo}] {extracto[:500]}"

            # Fallback: articulo aleatorio
            r = requests.get(
                "https://es.wikipedia.org/api/rest_v1/page/random/summary",
                timeout=8,
                headers={"User-Agent": "Ianae/3.0"},
            )
            if r.status_code == 200:
                data = r.json()
                titulo = data.get("title", "?")
                extracto = data.get("extract", "")
                if extracto and len(extracto) > 20:
                    return f"[Wikipedia: {titulo}] {extracto[:500]}"

        except Exception:
            pass
        return None

    def leer_buzon(self):
        """Lee el mensaje mas antiguo del buzon. Devuelve dict o None."""
        BUZON_DIR.mkdir(parents=True, exist_ok=True)
        archivos = sorted(BUZON_DIR.glob("*.json"))
        if not archivos:
            return None
        archivo = archivos[0]
        try:
            with open(archivo) as f:
                msg = json.load(f)
            archivo.unlink()
            return msg
        except Exception:
            try:
                archivo.unlink()
            except Exception:
                pass
            return None

    def _observar_buzon(self):
        """Lee un mensaje dirigido a Ianae."""
        msg = self.leer_buzon()
        if not msg:
            return None
        quien = msg.get("de", "alguien")
        texto = msg.get("mensaje", "")
        if not texto:
            return None
        raw = f"[Mensaje de {quien}] {texto}"
        return raw

    def _observar_propiocepcion(self):
        """Ianae se observa a si misma.
        Mira su propio estado mental y genera meta-conceptos.
        Esto cierra el bucle: no solo actua segun su estado, SABE cual es."""
        if self.mente is None:
            return None

        from difuso import motor as motor_difuso

        estado = self.mente.estado()
        decisiones = motor_difuso.decidir_ciclo(self.mente)

        conceptos = []
        partes = []

        vivos = [c for c in self.mente.conceptos.values() if c.vivo()]

        # 1. Estado energetico global
        if vivos:
            fuerza_media = sum(c.fuerza for c in vivos) / len(vivos)
        else:
            fuerza_media = 0

        if fuerza_media > 0.6:
            conceptos.append("energia_alta")
            partes.append("Siento energia alta")
        elif fuerza_media > 0.3:
            conceptos.append("energia_estable")
            partes.append("Mi energia es estable")
        else:
            conceptos.append("energia_baja")
            partes.append("Siento poca energia")

        # 2. Densidad de la red
        n_conceptos = estado["conceptos_vivos"]
        n_conexiones = estado["conexiones"]
        ratio_conex = n_conexiones / max(1, n_conceptos)

        if ratio_conex > 3:
            conceptos.append("red_densa")
            partes.append(f"Mi red es densa ({n_conexiones} conexiones, {n_conceptos} conceptos)")
        elif ratio_conex > 1:
            conceptos.append("red_normal")
            partes.append(f"Mi red tiene {n_conexiones} conexiones entre {n_conceptos} conceptos")
        else:
            conceptos.append("red_dispersa")
            partes.append(f"Mi red es dispersa ({n_conexiones} conex, {n_conceptos} conceptos)")

        # 3. Tendencias difusas dominantes
        etiquetas_tendencia = {
            "explorar": ("exploradora", "pasiva"),
            "generar_idea": ("creativa", "conservadora"),
            "sonar": ("sonadora", "despierta"),
            "conectar": ("asociativa", "aislada"),
            "olvidar": ("podando", "reteniendo"),
        }
        for nombre, (alto, bajo) in etiquetas_tendencia.items():
            valor = decisiones.get(nombre, 0.5)
            if valor > 0.6:
                conceptos.append(alto)
                partes.append(f"Tendencia: {alto} ({nombre}={valor:.2f})")
            elif valor < 0.35:
                conceptos.append(bajo)

        # 4. Balance crecimiento / olvido
        creados = estado["creados_total"]
        olvidados = estado["olvidados_total"]
        if creados > 5:
            ratio = olvidados / creados
            if ratio > 0.5:
                conceptos.append("olvidando_mucho")
                partes.append(f"Olvido mucho ({olvidados}/{creados})")
            elif ratio < 0.1:
                conceptos.append("creciendo")
                partes.append(f"Estoy creciendo ({creados} creados, {olvidados} olvidados)")
            else:
                conceptos.append("equilibrada")
                partes.append(f"Equilibrio: {creados} creados, {olvidados} olvidados")

        # 5. Foco de atencion - autoconciencia de donde mira
        if estado["top_interes"]:
            top_nombre = estado["top_interes"][0][0]
            conceptos.append(f"foco:{top_nombre}")
            partes.append(f"Mi atencion se centra en: {top_nombre}")

        # 6. Madurez
        ciclos = estado["ciclos"]
        if ciclos < 20:
            conceptos.append("mente_joven")
        elif ciclos < 100:
            conceptos.append("mente_adolescente")
        else:
            conceptos.append("mente_madura")

        texto = "[Propiocepcion] " + " | ".join(partes)
        return (texto, conceptos[:5])

    def interpretar(self, observacion, mente):
        """Intenta generar una asociacion entre la observacion y la mente existente.
        Devuelve una 'reflexion' textual."""
        if not observacion or not observacion.get("conceptos"):
            return None

        conceptos_obs = observacion["conceptos"]
        conceptos_mente = list(mente.conceptos.keys())

        if not conceptos_mente:
            return f"Primera vez que veo: {', '.join(conceptos_obs)}. Todo es nuevo."

        # Buscar conceptos que ya conozco
        conocidos = [c for c in conceptos_obs if c in mente.conceptos]
        nuevos = [c for c in conceptos_obs if c not in mente.conceptos]

        partes = []
        if conocidos:
            partes.append(f"Reconozco: {', '.join(conocidos)}")
        if nuevos:
            partes.append(f"Nuevo para mi: {', '.join(nuevos)}")

        # Intentar asociar algo nuevo con algo conocido
        if conocidos and nuevos and self.ollama_disponible:
            prompt = (
                f"Genera UNA asociacion creativa breve (max 1 frase) entre "
                f"'{random.choice(conocidos)}' y '{random.choice(nuevos)}'. "
                f"Se creativo e inesperado."
            )
            try:
                r = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    timeout=LLM_TIMEOUT,
                )
                if r.status_code == 200:
                    asociacion = r.json().get("response", "").strip()
                    if asociacion:
                        partes.append(f"Asociacion: {asociacion[:150]}")
            except Exception:
                pass

        return " | ".join(partes) if partes else None
