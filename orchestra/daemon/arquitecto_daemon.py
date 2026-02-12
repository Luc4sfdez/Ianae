"""
Daemon Arquitecto Autonomo para IANAE.

Ciclo:
  1. Poll docs-service cada CHECK_INTERVAL segundos
  2. Si hay docs nuevos -> construir contexto
  3. Buscar en cache -> si hit, usar respuesta cacheada
  4. Si miss -> llamar LLM via ProviderChain (DeepSeek -> Qwen -> Anthropic)
  5. Ejecutar: publicar orden, responder duda, escalar, o nada
  6. Repetir

Uso:
  python arquitecto_daemon.py

Requisito:
  Al menos una API key: DEEPSEEK_API_KEY, DASHSCOPE_API_KEY o ANTHROPIC_API_KEY
"""

import time
import json
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DOCS_SERVICE_URL,
    LLM_PROVIDERS,
    ANTHROPIC_MODEL,
    MAX_TOKENS,
    CHECK_INTERVAL,
    LOG_FILE,
    SYSTEM_PROMPT_FILE,
    IGNORE_TYPES,
    IGNORE_AUTHORS,
    MAX_DAILY_API_CALLS,
    CACHE_TTL_SECONDS,
    CACHE_MAX_ENTRIES,
)
from docs_client import DocsClient
from response_parser import parse_architect_response
from structured_logger import get_logger
from retry_manager import retry_with_backoff, APICallManager
from llm_provider import ProviderChain
from response_cache import ResponseCache

# ============================================
# LOGGING ESTRUCTURADO
# ============================================

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Logger estructurado con formato JSON
json_log_file = LOG_FILE.replace('.log', '_structured.json')
logger = get_logger("arquitecto", json_log_file)

# API Call Manager con retry + circuit breaker
api_manager = APICallManager(max_failures=3, cooldown_seconds=60)


# ============================================
# CONTEXTO
# ============================================

def build_context(snapshot, new_docs):
    context = "# ESTADO ACTUAL DEL PROYECTO IANAE\n\n"

    if snapshot:
        context += f"## Snapshot\n```json\n{json.dumps(snapshot, indent=2, ensure_ascii=False)}\n```\n\n"

    if new_docs:
        context += "## DOCUMENTOS NUEVOS\n\n"
        for doc in new_docs:
            context += f"### [{doc.get('category', '?')}] {doc.get('title', 'Sin titulo')}\n"
            context += f"- Author: {doc.get('author', '?')}\n"
            context += f"- Priority: {doc.get('priority', '?')}\n"
            context += f"- Tags: {doc.get('tags', [])}\n"

            content = doc.get("content", "")
            if len(content) < 3000:
                context += f"\n{content}\n\n"
            else:
                context += f"\nResumen: {content[:500]}...\n\n"

    return context


def build_user_message(context):
    return (
        f"{context}\n\n"
        "---\n"
        "Basandote en el estado actual y los documentos nuevos:\n"
        "1. Si hay una DUDA de un worker, resuelvela y publica respuesta\n"
        "2. Si hay un REPORTE de tarea completada, decide siguiente orden\n"
        "3. Si hay algo que escalar a Lucas, escalalo\n"
        "4. Si no hay accion necesaria, di none\n\n"
        "Responde con UN SOLO bloque JSON."
    )


# ============================================
# FILTROS
# ============================================

def filter_docs(docs):
    filtered = []
    for doc in docs:
        category = doc.get("category", "")
        author = doc.get("author", "")
        if category in IGNORE_TYPES:
            continue
        if author in IGNORE_AUTHORS:
            continue
        filtered.append(doc)
    return filtered


# ============================================
# EJECUTAR ACCION
# ============================================

def call_llm_with_retry(provider_chain, max_tokens, system, messages):
    """
    Llama al LLM via ProviderChain con retry automatico.

    Envuelve la llamada con:
    - Retry con backoff exponencial (3 intentos)
    - Circuit breaker (se detiene tras 3 fallos consecutivos)
    """
    @api_manager.with_protection
    def api_call():
        return provider_chain.chat(
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )

    return api_call()


def execute_action(action_data, docs_client):
    action = action_data.get("action", "none")

    if action == "publish_order":
        result = docs_client.publish_order(
            title=action_data.get("title", "Orden del Arquitecto"),
            content=action_data.get("content", ""),
            tags=action_data.get("tags", []),
            priority=action_data.get("priority", "alta"),
        )
        if result:
            logger.info(
                "Orden publicada",
                title=action_data.get('title'),
                tags=action_data.get('tags')
            )
        return True

    elif action == "respond_doubt":
        worker = action_data.get("worker", "")
        result = docs_client.publish_duda_response(
            worker_name=worker,
            duda_title=action_data.get("duda_title", "Duda"),
            respuesta=action_data.get("response", ""),
        )
        if result:
            logger.info(
                "Respuesta a duda publicada",
                worker=worker,
                duda=action_data.get('duda_title')
            )
        return True

    elif action == "multiple":
        orders = action_data.get("orders", [])
        for order in orders:
            docs_client.publish_order(
                title=order.get("title", "Orden"),
                content=order.get("content", ""),
                tags=order.get("tags", []),
                priority=order.get("priority", "alta"),
            )
            logger.info("Orden multiple publicada", title=order.get('title'))
        return True

    elif action == "escalate":
        msg = action_data.get("message", "Requiere atencion")
        logger.warning("Escalado a Lucas", escalation=msg)
        print(f"\n{'='*60}")
        print(f"  ESCALADO A LUCAS: {msg}")
        print(f"{'='*60}\n")
        docs_client.publish_escalado(msg)
        return True

    elif action == "none":
        logger.info("Sin accion necesaria", reason=action_data.get('reason', 'N/A'))
        return False

    return False


# ============================================
# LOOP PRINCIPAL
# ============================================

def main():
    print("=" * 60)
    print("  ARQUITECTO DAEMON AUTONOMO — IANAE")
    print("=" * 60)
    print(f"  docs-service: {DOCS_SERVICE_URL}")
    print(f"  Intervalo:    {CHECK_INTERVAL}s")
    print(f"  Max tokens:   {MAX_TOKENS}")
    print(f"  Max API/dia:  {MAX_DAILY_API_CALLS}")
    print(f"  Cache TTL:    {CACHE_TTL_SECONDS}s")
    print(f"  Log:          {LOG_FILE}")
    print("=" * 60)

    # Inicializar ProviderChain
    print("\n[PROVIDERS] Inicializando cadena LLM...")
    try:
        provider_chain = ProviderChain(LLM_PROVIDERS)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    providers = provider_chain.available_providers
    print(f"[OK] Providers disponibles: {' -> '.join(providers)}")
    for name in providers:
        print(f"   -> {name}")
    print()

    # Inicializar cache
    response_cache = ResponseCache(
        ttl_seconds=CACHE_TTL_SECONDS,
        max_entries=CACHE_MAX_ENTRIES,
    )
    cache_stats = response_cache.stats()
    print(f"[OK] Cache: {cache_stats['valid_entries']} entradas validas")

    # System prompt
    prompt_path = Path(SYSTEM_PROMPT_FILE)
    if not prompt_path.exists():
        print(f"[ERROR] No existe: {SYSTEM_PROMPT_FILE}")
        return
    system_prompt = prompt_path.read_text(encoding="utf-8")
    print(f"[OK] System prompt: {len(system_prompt)} chars")

    # docs-service
    docs_client = DocsClient(DOCS_SERVICE_URL)
    health = docs_client.health_check()
    if not health:
        print("[ERROR] docs-service no responde. Arrancalo primero.")
        return
    print(f"[OK] docs-service: {health}")

    print(f"\n[LOOP] Cada {CHECK_INTERVAL}s. Ctrl+C para parar.\n")

    last_check = datetime.now(timezone.utc).isoformat()
    api_calls_today = 0
    cache_hits_today = 0
    orders_published = 0
    current_date = datetime.now().date()

    try:
        while True:
            # Reset contador diario
            today = datetime.now().date()
            if today != current_date:
                api_calls_today = 0
                cache_hits_today = 0
                current_date = today
                logger.info("Contador diario reseteado", date=str(today))

            # Poll
            new_docs = docs_client.get_new_docs(last_check)
            new_docs = filter_docs(new_docs)

            if new_docs:
                print(f"\n[ALERTA] {len(new_docs)} doc(s) nuevo(s):")
                logger.info("Documentos nuevos detectados", count=len(new_docs))

                for d in new_docs:
                    tags = d.get("tags", [])
                    es_duda = "duda" in tags if isinstance(tags, list) else "duda" in str(tags)
                    tipo = "DUDA" if es_duda else d.get("category", "?")
                    print(f"   -> [{tipo}] {d.get('title','?')} (de {d.get('author','?')})")

                # Contexto
                snapshot = docs_client.get_snapshot()
                context = build_context(snapshot, new_docs)
                user_message = build_user_message(context)
                messages = [{"role": "user", "content": user_message}]

                # Intentar cache primero
                cached = response_cache.get(system_prompt, messages)
                if cached:
                    response_text = cached["text"]
                    cache_hits_today += 1
                    print(f"[CACHE] Hit! (provider original: {cached['provider']})")
                    logger.info(
                        "Cache hit",
                        original_provider=cached["provider"],
                        cache_hits_today=cache_hits_today,
                    )
                else:
                    # Verificar limite diario
                    if api_calls_today >= MAX_DAILY_API_CALLS:
                        logger.warning(
                            "Limite diario de API alcanzado",
                            limit=MAX_DAILY_API_CALLS,
                            calls_today=api_calls_today
                        )
                        print(f"[LIMITE] {MAX_DAILY_API_CALLS} llamadas hoy. No se consulta API.")
                        last_check = datetime.now(timezone.utc).isoformat()
                        time.sleep(CHECK_INTERVAL)
                        continue

                    # Llamar LLM con retry automatico
                    print("[IA] Consultando LLM...")
                    try:
                        llm_response = call_llm_with_retry(
                            provider_chain,
                            MAX_TOKENS,
                            system_prompt,
                            messages,
                        )
                        response_text = llm_response.text
                        api_calls_today += 1
                        logger.info(
                            "LLM call exitoso",
                            provider=llm_response.provider,
                            model=llm_response.model,
                            api_call_number=api_calls_today,
                            input_tokens=llm_response.input_tokens,
                            output_tokens=llm_response.output_tokens,
                        )
                        print(f"   [via {llm_response.provider}] "
                              f"{llm_response.input_tokens}in/{llm_response.output_tokens}out tokens")

                        # Guardar en cache
                        response_cache.put(
                            system_prompt, messages,
                            response_text, llm_response.provider,
                        )
                    except Exception as e:
                        logger.error("Error en LLM call", error=str(e), error_type=type(e).__name__)
                        time.sleep(CHECK_INTERVAL)
                        continue

                # Ejecutar
                action_data = parse_architect_response(response_text)
                acted = execute_action(action_data, docs_client)
                if acted:
                    orders_published += 1

                last_check = datetime.now(timezone.utc).isoformat()
                print(f"   [API hoy: {api_calls_today}/{MAX_DAILY_API_CALLS} | "
                      f"Cache hits: {cache_hits_today} | Ordenes: {orders_published}]")

            else:
                print(".", end="", flush=True)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n[STOP] Daemon parado.")
        print(f"  Providers:    {' -> '.join(providers)}")
        print(f"  API calls hoy: {api_calls_today}")
        print(f"  Cache hits:    {cache_hits_today}")
        print(f"  Ordenes:       {orders_published}")


if __name__ == "__main__":
    main()
