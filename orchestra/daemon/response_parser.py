"""
Parsea la respuesta JSON del Arquitecto IA.

Tolera variaciones de formato entre proveedores (Claude, DeepSeek, Qwen):
- JSON en bloque ```json ... ```
- JSON directo
- Strings multilinea sin escapar (comun en DeepSeek)
- JSON envuelto en texto extra
"""

import json
import re
import logging

logger = logging.getLogger("arquitecto.parser")


def _fix_multiline_strings(json_str):
    """
    Repara strings JSON con newlines sin escapar.

    Los LLMs a veces generan:
      "content": "linea 1
      linea 2"
    En vez de:
      "content": "linea 1\nlinea 2"
    """
    # Reemplazar newlines reales dentro de strings JSON por \n escapados
    fixed = []
    in_string = False
    escape_next = False

    for char in json_str:
        if escape_next:
            fixed.append(char)
            escape_next = False
            continue

        if char == '\\':
            fixed.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            fixed.append(char)
            continue

        if in_string and char == '\n':
            fixed.append('\\n')
            continue

        if in_string and char == '\r':
            continue

        fixed.append(char)

    return ''.join(fixed)


def _extract_json_block(text):
    """Extrae JSON de un bloque ```json ... ``` o ``` ... ```."""
    # Primero intentar ```json
    match = re.search(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Luego intentar ``` genérico
    match = re.search(r'```\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if content.startswith('{'):
            return content

    return None


def _extract_json_braces(text):
    """Extrae el primer objeto JSON {...} del texto."""
    start = text.find('{')
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return None


def parse_architect_response(response_text):
    """
    Extrae JSON de accion de la respuesta del LLM.

    Estrategias (en orden):
    1. Bloque ```json ... ```
    2. JSON directo
    3. Extraer primer {...} del texto
    Cada una intenta primero parse directo, luego con fix de multilinea.
    """
    strategies = []

    # Estrategia 1: bloque de codigo
    json_block = _extract_json_block(response_text)
    if json_block:
        strategies.append(("code_block", json_block))

    # Estrategia 2: texto completo
    strategies.append(("direct", response_text.strip()))

    # Estrategia 3: extraer por llaves
    json_braces = _extract_json_braces(response_text)
    if json_braces:
        strategies.append(("braces", json_braces))

    for name, candidate in strategies:
        # Intento directo
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "action" in parsed:
                logger.info(f"Parsed ({name}): action={parsed.get('action', '?')}")
                return parsed
        except json.JSONDecodeError:
            pass

        # Intento con fix de multilinea
        try:
            fixed = _fix_multiline_strings(candidate)
            parsed = json.loads(fixed)
            if isinstance(parsed, dict) and "action" in parsed:
                logger.info(f"Parsed ({name}+fix): action={parsed.get('action', '?')}")
                return parsed
        except json.JSONDecodeError:
            pass

    logger.warning(f"No se pudo parsear respuesta JSON (len={len(response_text)})")
    return {"action": "none", "reason": "No se pudo parsear respuesta"}
