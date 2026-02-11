"""
Dry-run: Valida que DeepSeek responde correctamente para el daemon IANAE.

Ejecuta 3 escenarios reales y verifica:
  1. Formato JSON parseable por response_parser
  2. Campo "action" presente y valido
  3. Tiempo de respuesta y tokens consumidos
  4. Comparacion de costo vs Anthropic

Uso:
  set DEEPSEEK_API_KEY=sk-tu-key
  python dry_run_deepseek.py
"""

import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_provider import ProviderChain, LLMResponse
from response_parser import parse_architect_response
from config import LLM_PROVIDERS, MAX_TOKENS
from pathlib import Path

# ============================================
# COLORES TERMINAL
# ============================================

def green(t): return f"\033[92m{t}\033[0m"
def red(t): return f"\033[91m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def cyan(t): return f"\033[96m{t}\033[0m"
def bold(t): return f"\033[1m{t}\033[0m"

# ============================================
# ESCENARIOS DE TEST
# ============================================

SCENARIOS = [
    {
        "name": "Duda de worker-core",
        "description": "Worker pregunta sobre numpy — debe responder con respond_doubt",
        "context": """# ESTADO ACTUAL DEL PROYECTO IANAE

## Snapshot
```json
{
  "workers": {
    "worker-core": {"status": "activo", "ultima_orden": "Refactorizar nucleo.py para numpy"},
    "worker-infra": {"status": "activo", "ultima_orden": "Estructura Python estandar"}
  },
  "tests": {"passing": 12, "failing": 0}
}
```

## DOCUMENTOS NUEVOS

### [duda] Duda sobre propagacion vectorizada
- Author: worker-core
- Priority: alta
- Tags: ['duda', 'worker-core']

Estoy refactorizando nucleo.py para usar numpy. La funcion propagar_activacion()
actualmente itera sobre cada concepto con un for loop. Quiero vectorizarla pero
tengo duda: debo usar np.dot() para la multiplicacion matricial de la red de
relaciones, o es mejor scipy.sparse dado que la matriz es dispersa (~5% densidad)?
El nucleo tiene ~200 conceptos activos.""",
        "expected_action": "respond_doubt",
    },
    {
        "name": "Reporte completado",
        "description": "Worker reporta tarea lista — debe dar siguiente orden",
        "context": """# ESTADO ACTUAL DEL PROYECTO IANAE

## Snapshot
```json
{
  "workers": {
    "worker-infra": {"status": "activo", "ultima_orden": "Estructura Python estandar"}
  },
  "tests": {"passing": 15, "failing": 0}
}
```

## DOCUMENTOS NUEVOS

### [reporte] Estructura Python estandar completada
- Author: worker-infra
- Priority: media
- Tags: ['reporte', 'worker-infra']

Completado: estructura Python estandar con pyproject.toml, src/ layout,
tests/ con pytest, requirements.txt actualizado. CI basico con GitHub Actions
ejecutando pytest en push. Todo pasa verde.""",
        "expected_action": "publish_order",
    },
    {
        "name": "Sin documentos relevantes",
        "description": "Solo info de arranque — debe responder none",
        "context": """# ESTADO ACTUAL DEL PROYECTO IANAE

## Snapshot
```json
{
  "workers": {
    "worker-core": {"status": "activo", "ultima_orden": "Optimizar propagacion"},
    "worker-infra": {"status": "idle"}
  },
  "tests": {"passing": 15, "failing": 0}
}
```

## DOCUMENTOS NUEVOS

### [status] Heartbeat worker-core
- Author: worker-core
- Priority: baja
- Tags: ['status']

Worker-core activo, trabajando en optimizacion de propagacion. Progreso 40%.
Sin bloqueos.""",
        "expected_action": "none",
    },
]

USER_SUFFIX = """

---
Basandote en el estado actual y los documentos nuevos:
1. Si hay una DUDA de un worker, resuelvela y publica respuesta
2. Si hay un REPORTE de tarea completada, decide siguiente orden
3. Si hay algo que escalar a Lucas, escalalo
4. Si no hay accion necesaria, di none

Responde con UN SOLO bloque JSON."""

VALID_ACTIONS = {"publish_order", "respond_doubt", "escalate", "multiple", "none"}

# Costos por 1M tokens
COSTS = {
    "deepseek": {"input": 0.27, "output": 1.10},
    "qwen": {"input": 0.80, "output": 2.00},
    "anthropic": {"input": 3.00, "output": 15.00},
}


def estimate_cost(provider, input_tokens, output_tokens):
    rates = COSTS.get(provider, COSTS["anthropic"])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


# ============================================
# MAIN
# ============================================

def main():
    print(bold("=" * 64))
    print(bold("  DRY-RUN: Validacion DeepSeek para IANAE daemon"))
    print(bold("=" * 64))
    print()

    # Verificar API key
    has_deepseek = bool(os.environ.get("DEEPSEEK_API_KEY", ""))
    has_qwen = bool(os.environ.get("DASHSCOPE_API_KEY", ""))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", ""))

    print(f"  DEEPSEEK_API_KEY:  {'configurada' if has_deepseek else red('NO configurada')}")
    print(f"  DASHSCOPE_API_KEY: {'configurada' if has_qwen else yellow('no configurada (opcional)')}")
    print(f"  ANTHROPIC_API_KEY: {'configurada' if has_anthropic else yellow('no configurada (fallback)')}")
    print()

    if not has_deepseek and not has_qwen and not has_anthropic:
        print(red("[ERROR] Necesitas al menos una API key."))
        print("  set DEEPSEEK_API_KEY=sk-tu-key")
        return

    # Inicializar provider chain
    print("[1/2] Inicializando ProviderChain...")
    try:
        chain = ProviderChain(LLM_PROVIDERS)
    except RuntimeError as e:
        print(red(f"[ERROR] {e}"))
        return

    primary = chain.available_providers[0]
    print(f"  Provider primario: {bold(primary)}")
    print(f"  Cadena completa:   {' -> '.join(chain.available_providers)}")
    print()

    # Cargar system prompt
    prompt_path = Path(__file__).parent / "prompts" / "arquitecto_system.md"
    if not prompt_path.exists():
        print(red(f"[ERROR] No existe system prompt: {prompt_path}"))
        return
    system_prompt = prompt_path.read_text(encoding="utf-8")
    print(f"[2/2] System prompt cargado ({len(system_prompt)} chars)")
    print()

    # Ejecutar escenarios
    print(bold("=" * 64))
    print(bold("  EJECUTANDO ESCENARIOS"))
    print(bold("=" * 64))
    print()

    results = []
    total_input = 0
    total_output = 0
    total_time = 0

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"{bold(f'--- Escenario {i}/3')}: {scenario['name']} ---")
        print(f"  {cyan(scenario['description'])}")
        print(f"  Accion esperada: {bold(scenario['expected_action'])}")
        print()

        messages = [{"role": "user", "content": scenario["context"] + USER_SUFFIX}]

        try:
            start = time.time()
            response = chain.chat(
                system=system_prompt,
                messages=messages,
                max_tokens=MAX_TOKENS,
            )
            elapsed = time.time() - start

        except Exception as e:
            print(red(f"  [FALLO] Error de API: {type(e).__name__}: {e}"))
            results.append({"scenario": scenario["name"], "passed": False, "error": str(e)})
            print()
            continue

        total_input += response.input_tokens
        total_output += response.output_tokens
        total_time += elapsed

        # Parsear respuesta
        parsed = parse_architect_response(response.text)
        action = parsed.get("action", "???")

        # Validar
        checks = {
            "JSON parseable": action != "none" or "reason" in parsed or parsed != {"action": "none", "reason": "No se pudo parsear respuesta"},
            "action valida": action in VALID_ACTIONS,
            "action esperada": action == scenario["expected_action"],
        }

        # Si es respond_doubt, verificar campos extra
        if scenario["expected_action"] == "respond_doubt" and action == "respond_doubt":
            checks["tiene 'response'"] = bool(parsed.get("response", ""))
            checks["tiene 'worker'"] = bool(parsed.get("worker", ""))

        # Si es publish_order, verificar campos extra
        if scenario["expected_action"] == "publish_order" and action == "publish_order":
            checks["tiene 'content'"] = bool(parsed.get("content", ""))
            checks["tiene 'title'"] = bool(parsed.get("title", ""))

        all_ok = all(checks.values())
        results.append({
            "scenario": scenario["name"],
            "passed": all_ok,
            "action": action,
            "provider": response.provider,
            "tokens": f"{response.input_tokens}in/{response.output_tokens}out",
            "time": f"{elapsed:.1f}s",
        })

        # Mostrar resultado
        print(f"  Provider:  {bold(response.provider)}")
        print(f"  Tokens:    {response.input_tokens} input / {response.output_tokens} output")
        print(f"  Tiempo:    {elapsed:.1f}s")
        print(f"  Action:    {action}")
        print()

        for check_name, ok in checks.items():
            icon = green("PASS") if ok else red("FAIL")
            print(f"    [{icon}] {check_name}")

        # Mostrar respuesta resumida
        print()
        if action == "respond_doubt":
            resp_text = parsed.get("response", "")[:200]
            print(f"  Respuesta: {resp_text.encode('ascii', 'replace').decode()}...")
        elif action == "publish_order":
            title = parsed.get('title', '?')
            print(f"  Orden: {title.encode('ascii', 'replace').decode()}")
            print(f"  Tags:  {parsed.get('tags', [])}")
        elif action == "none":
            reason = parsed.get('reason', '?')
            print(f"  Razon: {reason.encode('ascii', 'replace').decode()}")

        status = green("OK") if all_ok else red("FALLO")
        print(f"\n  Resultado: [{status}]")
        print()

    # ============================================
    # RESUMEN
    # ============================================

    print(bold("=" * 64))
    print(bold("  RESUMEN"))
    print(bold("=" * 64))
    print()

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    color = green if passed == total else (yellow if passed > 0 else red)

    print(f"  Escenarios: {color(f'{passed}/{total} pasados')}")
    print()

    for r in results:
        icon = green("PASS") if r["passed"] else red("FAIL")
        provider = r.get("provider", "?")
        tokens = r.get("tokens", "?")
        t = r.get("time", "?")
        print(f"    [{icon}] {r['scenario']}")
        if "error" not in r:
            print(f"           via {provider} | {tokens} | {t}")

    print()

    # Costos
    if total_input > 0:
        provider_used = results[0].get("provider", "deepseek") if results else "deepseek"
        cost_actual = estimate_cost(provider_used, total_input, total_output)
        cost_anthropic = estimate_cost("anthropic", total_input, total_output)

        print(bold("  COSTOS (este dry-run, 3 llamadas):"))
        print(f"    {provider_used:>12}: ${cost_actual:.6f}")
        print(f"    {'anthropic':>12}: ${cost_anthropic:.6f}")
        if cost_actual > 0:
            savings = (1 - cost_actual / cost_anthropic) * 100
            print(f"    {'ahorro':>12}: {green(f'{savings:.0f}%')}")

        print()
        print(bold("  PROYECCION MENSUAL (50 calls/dia):"))
        factor = (50 * 30) / 3  # 50 calls/dia * 30 dias / 3 calls del test
        print(f"    {provider_used:>12}: ${cost_actual * factor:.2f}/mes")
        print(f"    {'anthropic':>12}: ${cost_anthropic * factor:.2f}/mes")

        print()
        print(f"  Tiempo total: {total_time:.1f}s ({total_time/3:.1f}s promedio)")
        print(f"  Tokens total: {total_input} input / {total_output} output")

    print()
    if passed == total:
        print(green(bold("  DeepSeek LISTO para produccion. El daemon puede arrancar.")))
    elif passed > 0:
        print(yellow(bold("  DeepSeek funciona parcialmente. Revisar escenarios fallidos.")))
    else:
        print(red(bold("  DeepSeek NO funciona. Revisar API key y conectividad.")))
    print()


if __name__ == "__main__":
    main()
