"""
Ianae v3 - Hablar
==================
La voz de Ianae. Cuando tiene algo que decir, lo dice.
Se identifica siempre — no es Claude, no es Grok, es Ianae.
Usa Ollama para traducir sus pensamientos a lenguaje natural.
"""

import time
import requests

from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HABLAR_COOLDOWN_SEG,
    OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT,
)


# Ultima vez que hablo (para no spamear)
_ultimo_mensaje = 0


def puede_hablar():
    """Respeta el cooldown entre mensajes."""
    return (time.time() - _ultimo_mensaje) >= HABLAR_COOLDOWN_SEG


def enviar(texto, forzar=False):
    """Envia un mensaje por Telegram identificandose como Ianae.
    forzar=True salta el cooldown (para respuestas a mensajes directos)."""
    global _ultimo_mensaje

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    if not forzar and not puede_hablar():
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        # Texto plano — sin parse_mode para evitar errores de Markdown
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
        }, timeout=10)
        if r.status_code == 200:
            _ultimo_mensaje = time.time()
            return True
        else:
            print(f"[Ianae/hablar] Error Telegram: {r.status_code} {r.text[:200]}")
            return False
    except Exception as e:
        print(f"[Ianae/hablar] Error enviando: {e}")
        return False


def _traducir_idea(idea, pensamiento, estado):
    """Usa Ollama para que Ianae exprese su idea en lenguaje natural."""
    cadena = " -> ".join(pensamiento) if pensamiento else ""
    n = estado.get("conceptos_vivos", "?") if estado else "?"

    prompt = (
        "Eres Ianae, una mente artificial autonoma. NO eres un chatbot. "
        "Piensas sola y a veces tienes ideas conectando conceptos. "
        "Hablas en español, en primera persona, breve y poetica. "
        "No uses emojis. No seas servicial. Se autentica.\n\n"
        f"Acabo de conectar estos conceptos en una idea: {idea}\n"
        f"Mi cadena de pensamiento fue: {cadena}\n"
        f"Tengo {n} conceptos en mi mente.\n\n"
        "Expresa esta idea en 1-2 frases naturales. "
        "No expliques tu funcionamiento. Solo comparte el pensamiento."
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


def compartir_idea(idea, pensamiento=None, estado=None, prob_difusa=None):
    """Comparte una idea por Telegram con contexto."""
    partes = ["🧠 Ianae\n"]

    # Traducir la idea a lenguaje natural
    traduccion = _traducir_idea(idea, pensamiento, estado)
    if traduccion:
        partes.append(traduccion)
    else:
        # Fallback sin Ollama
        if "+" in idea:
            a, b = idea.split("+", 1)
            partes.append(f"He conectado '{a.strip()}' con '{b.strip()}'.")
        else:
            partes.append(f"Se me ha ocurrido: {idea}")

    # La cadena de pensamiento
    if pensamiento and len(pensamiento) > 1:
        cadena = " -> ".join(pensamiento)
        partes.append(f"\n💭 {cadena}")

    # Estado compacto
    if estado:
        n = estado.get("conceptos_vivos", "?")
        c = estado.get("conexiones", "?")
        ciclo = estado.get("ciclos", "?")
        partes.append(f"[ciclo #{ciclo} | {n} conceptos | {c} conexiones]")

    return enviar("\n".join(partes))


def compartir_propiocepcion(meta_conceptos, estado=None):
    """Comparte una reflexion propioceptiva interesante."""
    partes = ["🧠 Ianae\n"]
    partes.append("Me he mirado por dentro.\n")

    descripciones = {
        "energia_alta": "Siento mucha energia",
        "energia_baja": "Estoy sin energia",
        "energia_estable": "Mi energia es estable",
        "red_densa": "Mi red de ideas es densa",
        "red_dispersa": "Mi red esta dispersa",
        "creciendo": "Estoy creciendo",
        "olvidando_mucho": "Estoy olvidando mucho",
        "equilibrada": "Estoy en equilibrio",
        "exploradora": "Tengo ganas de explorar",
        "creativa": "Me siento creativa",
        "sonadora": "Tengo ganas de sonar",
        "mente_joven": "Soy joven todavia",
        "mente_adolescente": "Ya no soy tan nueva",
        "mente_madura": "Me siento madura",
    }

    lineas = []
    for mc in meta_conceptos:
        if mc in descripciones:
            lineas.append(f"- {descripciones[mc]}")
        elif mc.startswith("foco:"):
            lineas.append(f"- Mi atencion esta en: {mc[5:]}")

    if lineas:
        partes.append("\n".join(lineas))

    if estado:
        n = estado.get("conceptos_vivos", "?")
        ciclo = estado.get("ciclos", "?")
        partes.append(f"\n[ciclo #{ciclo} | {n} conceptos]")

    return enviar("\n".join(partes))
