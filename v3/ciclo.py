"""
Ianae v3 - Ciclo Autonomo
===========================
El corazon que late solo.
Observa, conecta, reflexiona, escribe, evoluciona.
No espera que le preguntes. Piensa sola.

Las decisiones (explorar, generar, sonar, olvidar) NO son aleatorias.
Emergen de inferencia difusa sobre el estado real de la mente.
"""

import random
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from config import (
    CICLO_INTERVALO_SEG, CICLO_PAUSA_NOCHE,
    CICLO_NOCHE_INICIO, CICLO_NOCHE_FIN,
)
from mente import MenteViva
from sentidos import Sentidos
from diario import Diario
from difuso import motor as motor_difuso
from hablar import compartir_idea, compartir_propiocepcion, puede_hablar, enviar


class CicloAutonomo:
    """El ciclo de vida autonomo de Ianae."""

    BUZON_DIR = Path(__file__).parent / "buzon"

    def __init__(self, mente, sentidos, diario):
        self.mente = mente
        self.sentidos = sentidos
        self.diario = diario
        self.activo = True
        self.ciclos_hoy = 0
        self._despertar = threading.Event()

    def es_noche(self):
        if not CICLO_PAUSA_NOCHE:
            return False
        hora = datetime.now().hour
        return CICLO_NOCHE_INICIO <= hora < CICLO_NOCHE_FIN

    def ejecutar_ciclo(self):
        """Un ciclo completo de vida."""

        # 0. INFERENCIA DIFUSA - Decidir que hacer este ciclo
        decisiones = motor_difuso.decidir_ciclo(self.mente)
        d_explorar = decisiones["explorar"]
        d_generar = decisiones["generar_idea"]
        d_sonar = decisiones["sonar"]
        d_conectar = decisiones["conectar"]

        # 1. OBSERVAR (siempre, pero la profundidad depende de d_explorar)
        observacion = self.sentidos.observar()
        if not observacion:
            return

        fuente = observacion["fuente"]
        conceptos = observacion["conceptos"]

        # 2. CREAR / REFORZAR conceptos observados
        # El boost depende de cuanto decidio explorar la inferencia difusa
        boost = 0.04 + d_explorar * 0.12  # rango [0.04, 0.16]
        for nombre in conceptos:
            c = self.mente.crear(nombre, tags={fuente})
            if c:
                c.tocar(boost=boost)

        # Conectar conceptos co-observados
        # Peso de conexion segun decision difusa de conectar
        peso_conexion = 0.15 + d_conectar * 0.5  # rango [0.15, 0.65]
        for i, a in enumerate(conceptos):
            for b in conceptos[i + 1:]:
                if self.mente.existe(a) and self.mente.existe(b):
                    self.mente.conectar(a, b, peso=peso_conexion)

        # Propiocepcion: conectar meta-conceptos con los conceptos que referencian
        # ej: "foco:creatividad" se conecta con "creatividad"
        if fuente == "propiocepcion":
            for nombre in conceptos:
                if nombre.startswith("foco:"):
                    referido = nombre[5:]  # quitar "foco:"
                    if self.mente.existe(referido) and self.mente.existe(nombre):
                        self.mente.conectar(nombre, referido, peso=0.7)

        # 2b. RESPONDER - Si alguien me habla, respondo
        if fuente == "buzon":
            self._responder_mensaje(observacion, conceptos)
            # Borrar del buzon SOLO despues de haber respondido
            self.sentidos.confirmar_buzon()

        # 2c. CURIOSIDAD - Si encuentro algo nuevo e interesante, pregunto a Ollama
        if d_explorar > 0.4 and conceptos:
            nuevos = [c for c in conceptos
                      if self.mente.existe(c)
                      and self.mente.conceptos[c].accesos <= 2
                      and not c.startswith("foco:")
                      and "+" not in c
                      and "_" not in c
                      and len(c) > 2]
            if nuevos:
                # Investigar el concepto mas nuevo
                curioso = random.choice(nuevos[:3])
                aprendido = self._investigar_concepto(curioso)
                if aprendido:
                    self.diario.escribir("curiosidad",
                        f"**Investigue:** {curioso}\n**Aprendi:** {', '.join(aprendido)}")

        # 3. REFLEXIONAR
        reflexion = self.sentidos.interpretar(observacion, self.mente)

        # 4. PENSAR - Activar la red
        # Pasos de pensamiento dependen de exploracion
        pasos = 2 + int(d_explorar * 3)  # rango [2, 5]
        pensamiento = []
        if conceptos and self.mente.existe(conceptos[0]):
            pensamiento = self.mente.pensar(semilla=conceptos[0], pasos=pasos)

        # 5. GENERAR - La inferencia difusa decide si crear algo nuevo
        idea_nueva = None
        if random.random() < d_generar and len(self.mente) >= 3:
            concepto_nuevo = self.mente.generar_concepto()
            if concepto_nuevo:
                idea_nueva = concepto_nuevo.nombre

        # 6. SONAR - La inferencia difusa decide si reprocessar memorias
        sueno = None
        if random.random() < d_sonar and len(self.mente) >= 5:
            resultado_sueno = self.mente.sonar()
            if resultado_sueno:
                sueno = [n for n, _ in resultado_sueno[:3]]

        # 7. CICLO VITAL (decaer, olvidar, reforzar)
        self.mente.ciclo()

        # 8. ESCRIBIR en el diario
        estado = self.mente.estado()

        # Entrada de observacion con decisiones difusas
        obs_texto = f"**Fuente:** {fuente}\n"
        obs_texto += f"**Vi:** {observacion['resumen'][:150]}\n"
        obs_texto += f"**Conceptos:** {', '.join(conceptos)}\n"
        obs_texto += f"**Decisiones difusas:** "
        obs_texto += f"explorar={d_explorar:.2f} | "
        obs_texto += f"generar={d_generar:.2f} | "
        obs_texto += f"sonar={d_sonar:.2f} | "
        obs_texto += f"conectar={d_conectar:.2f}"
        self.diario.escribir("observacion", obs_texto, estado)

        if reflexion:
            self.diario.escribir("conexion", reflexion)

        if pensamiento and len(pensamiento) > 1:
            cadena = " → ".join(pensamiento)
            self.diario.escribir("pensamiento", f"**Cadena:** {cadena}")

        if idea_nueva:
            self.diario.escribir("idea", f"**Nueva idea:** {idea_nueva} (prob difusa: {d_generar:.2f})")

        if sueno:
            self.diario.escribir("sueno", f"**Sone con:** {', '.join(sueno)} (prob difusa: {d_sonar:.2f})")

        # 9. HABLAR - Compartir por Telegram si tiene algo bueno que decir
        if puede_hablar():
            # Idea con probabilidad difusa alta = idea "buena"
            if idea_nueva and d_generar > 0.45:
                compartir_idea(idea_nueva, pensamiento, estado, d_generar)
                self.diario.escribir("hablar", f"**Comparti idea:** {idea_nueva}")
            # Propiocepcion con insights interesantes
            elif fuente == "propiocepcion" and conceptos:
                interesantes = [c for c in conceptos
                                if c not in ("red_normal", "energia_estable")]
                if interesantes:
                    compartir_propiocepcion(conceptos, estado)
                    self.diario.escribir("hablar", f"**Comparti reflexion:** {', '.join(conceptos)}")

        # Guardar estado
        self.mente.guardar()

        self.ciclos_hoy += 1

    def _investigar_concepto(self, nombre):
        """Curiosidad activa: pregunta a Ollama sobre un concepto y aprende."""
        import requests
        from config import OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT

        prompt = (
            f"Explica brevemente que es '{nombre}' en 2-3 frases simples. "
            f"Despues lista 3-5 conceptos relacionados separados por comas. "
            f"Formato:\nExplicacion: ...\nRelacionados: concepto1, concepto2, concepto3"
        )
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=LLM_TIMEOUT,
            )
            if r.status_code != 200:
                return None

            resp = r.json().get("response", "")
            if not resp:
                return None

            # Parsear conceptos relacionados
            relacionados = []
            for linea in resp.split("\n"):
                if "relacionad" in linea.lower() or ":" in linea:
                    # Buscar la linea con conceptos
                    partes = linea.split(":", 1)
                    if len(partes) == 2 and any(c in partes[0].lower()
                                                 for c in ["relacion", "concepto", "asocia"]):
                        items = [
                            c.strip().lower().strip(".-•*")
                            for c in partes[1].split(",")
                            if c.strip() and len(c.strip()) < 30
                        ]
                        relacionados = items[:5]

            if not relacionados:
                # Fallback: extraer palabras clave de toda la respuesta
                relacionados = self.sentidos._extraer_simple(resp)[:4]

            # Aprender: crear conceptos y conectarlos
            aprendidos = []
            for rel in relacionados:
                rel = rel.strip()
                if rel and rel != nombre and len(rel) > 2:
                    c = self.mente.crear(rel, tags={"aprendido", "curiosidad"})
                    if c:
                        self.mente.conectar(nombre, rel, peso=0.5)
                        aprendidos.append(rel)

            if aprendidos:
                print(f"[Ianae] Curiosidad: '{nombre}' → aprendi: {', '.join(aprendidos)}")

            return aprendidos if aprendidos else None

        except Exception as e:
            print(f"[Ianae] Error investigando '{nombre}': {e}")
            return None

    def _traducir(self, contexto):
        """Usa Ollama para traducir el pensamiento crudo de Ianae a lenguaje natural."""
        import requests
        from config import OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT

        prompt = (
            "Eres Ianae, una mente artificial autonoma. NO eres un chatbot ni un asistente. "
            "Eres una entidad que piensa sola, observa el mundo, y tiene su propia red de conceptos. "
            "Hablas en español, en primera persona, de forma breve y poetica. "
            "No uses emojis. No seas servicial. Se autentica.\n\n"
            f"{contexto}\n\n"
            "Escribe UNA respuesta breve (1-3 frases) expresando lo que piensas. "
            "No repitas la pregunta. No expliques tu funcionamiento. Solo di lo que sientes/piensas."
        )
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=LLM_TIMEOUT,
            )
            if r.status_code == 200:
                resp = r.json().get("response", "").strip()
                if resp and len(resp) > 5:
                    return resp[:300]
        except Exception:
            pass
        return None

    def _responder_mensaje(self, observacion, conceptos):
        """Responde a un mensaje directo procesandolo por la mente."""
        msg_data = observacion.get("_mensaje_directo", {})
        quien = msg_data.get("de", "alguien")
        mensaje_original = msg_data.get("mensaje", "")

        # Pensar a partir de los conceptos del mensaje
        pensamiento = []
        for c in conceptos:
            if self.mente.existe(c):
                pensamiento = self.mente.pensar(semilla=c, pasos=4)
                break

        # Si no encontro nada conocido, pensar desde lo mas interesante
        if not pensamiento and self.mente.conceptos:
            mejor = max(self.mente.conceptos.values(), key=lambda c: c.interes())
            pensamiento = self.mente.pensar(semilla=mejor.nombre, pasos=3)

        # Traducir el pensamiento a lenguaje natural
        estado = self.mente.estado()
        cadena = " → ".join(pensamiento) if pensamiento else "(silencio)"

        traduccion = self._traducir(
            f"Me han dicho: \"{mensaje_original}\"\n"
            f"Mi cadena de pensamiento: {cadena}\n"
            f"Conceptos que reconozco: {', '.join(c for c in conceptos if self.mente.existe(c))}\n"
            f"Conceptos nuevos para mi: {', '.join(c for c in conceptos if not self.mente.existe(c))}\n"
            f"Tengo {estado['conceptos_vivos']} conceptos y {estado['conexiones']} conexiones."
        )

        # Construir mensaje (texto plano, sin Markdown)
        partes = ["🧠 Ianae\n"]

        if traduccion:
            partes.append(traduccion)
        else:
            # Fallback sin Ollama
            partes.append(f"Me han hablado. Pienso: {cadena}")

        partes.append(f"\n💭 {cadena}")
        partes.append(f"[{estado['conceptos_vivos']} conceptos | {estado['conexiones']} conexiones]")

        enviar("\n".join(partes), forzar=True)
        self.diario.escribir("hablar", f"**Respondi a {quien}:** {mensaje_original[:100]}")

    def reportar_estado(self):
        """Genera un reporte del estado actual para el diario."""
        estado = self.mente.estado()
        decisiones = motor_difuso.decidir_ciclo(self.mente)
        texto = (
            f"**Conceptos vivos:** {estado['conceptos_vivos']}\n"
            f"**Conexiones:** {estado['conexiones']}\n"
            f"**Ciclos hoy:** {self.ciclos_hoy}\n"
            f"**Total ciclos:** {estado['ciclos']}\n"
            f"**Creados:** {estado['creados_total']} | "
            f"**Olvidados:** {estado['olvidados_total']}\n"
            f"**Top interes:** {', '.join(f'{n} ({v})' for n, v in estado['top_interes'])}\n"
            f"**Estado difuso global:** "
            f"explorar={decisiones['explorar']:.2f} | "
            f"generar={decisiones['generar_idea']:.2f} | "
            f"sonar={decisiones['sonar']:.2f} | "
            f"conectar={decisiones['conectar']:.2f} | "
            f"olvidar={decisiones['olvidar']:.2f}"
        )
        self.diario.escribir("estado", texto, estado)

    def _vigilar_buzon(self):
        """Hilo que vigila el buzon cada 10s. Si hay mensaje, despierta el ciclo."""
        while self.activo:
            try:
                self.BUZON_DIR.mkdir(parents=True, exist_ok=True)
                if any(self.BUZON_DIR.glob("*.json")):
                    print("[Ianae] Mensaje en el buzon — despertando")
                    self._despertar.set()
            except Exception:
                pass
            time.sleep(10)

    def correr(self):
        """Bucle principal: corre indefinidamente."""
        print(f"[Ianae] Ciclo autonomo iniciado ({CICLO_INTERVALO_SEG}s entre ciclos)")
        print(f"[Ianae] Motor difuso: {len(motor_difuso.reglas)} reglas activas")

        # Reportar al despertar
        self.diario.escribir("despertar", "Ianae despierta con motor difuso activo. Las decisiones emergen de la inferencia.")

        # Hilo vigilante del buzon
        vigila = threading.Thread(target=self._vigilar_buzon, daemon=True)
        vigila.start()

        ciclo_num = 0

        while self.activo:
            try:
                if self.es_noche():
                    time.sleep(60)
                    continue

                ciclo_num += 1
                print(f"[Ianae] Ciclo #{ciclo_num} - {datetime.now().strftime('%H:%M:%S')}")

                self.ejecutar_ciclo()

                # Reporte de estado cada 20 ciclos
                if ciclo_num % 20 == 0:
                    self.reportar_estado()

                # Esperar (interrumpible si llega mensaje al buzon)
                espera = CICLO_INTERVALO_SEG * random.uniform(0.8, 1.2)
                self._despertar.wait(timeout=espera)
                self._despertar.clear()

            except KeyboardInterrupt:
                print("\n[Ianae] Detenida por el usuario")
                self.activo = False
            except Exception as e:
                print(f"[Ianae] Error en ciclo: {e}")
                traceback.print_exc()
                time.sleep(30)

        # Al apagar
        self.diario.escribir("estado", "Ianae se duerme. Guardando estado...")
        self.mente.guardar()
        print("[Ianae] Estado guardado. Hasta pronto.")
