"""
Verificacion de Sistema IANAE-Orchestra
Comprueba que todo esta listo para modo multi-worker
"""

import requests
import sys
from pathlib import Path

def check(name, condition, error_msg=""):
    """Helper para verificaciones"""
    if condition:
        print(f"[OK] {name}")
        return True
    else:
        print(f"[X] {name}")
        if error_msg:
            print(f"  -> {error_msg}")
        return False

def main():
    print("="*60)
    print("  VERIFICACION SISTEMA ORCHESTRA - MULTI-WORKER")
    print("="*60)
    print()

    all_good = True

    # 1. Servicios base
    print("[1] Servicios Base")
    print("-"*60)

    try:
        r = requests.get("http://localhost:25500/health", timeout=2)
        all_good &= check("docs-service (25500)", r.status_code == 200)
    except:
        all_good &= check("docs-service (25500)", False, "No responde - arrancalo primero")

    try:
        r = requests.get("http://localhost:25501/", timeout=2)
        check("dashboard (25501)", r.status_code == 200, "Opcional pero recomendado")
    except:
        check("dashboard (25501)", False, "Opcional - puedes arrancarlo despues")

    print()

    # 2. Archivos de configuracion
    print("[2] Archivos de Configuracion")
    print("-"*60)

    base = Path("E:/ianae-final")

    all_good &= check("orchestra.yaml", (base / "orchestra.yaml").exists())
    all_good &= check("daemon config.py", (base / "orchestra/daemon/config.py").exists())
    all_good &= check("prompt arquitecto", (base / "orchestra/daemon/prompts/arquitecto_system.md").exists())
    all_good &= check("prompt worker-core", (base / "orchestra/daemon/prompts/worker_core.md").exists())
    all_good &= check("prompt worker-infra", (base / "orchestra/daemon/prompts/worker_infra.md").exists())
    all_good &= check("prompt worker-nlp", (base / "orchestra/daemon/prompts/worker_nlp.md").exists())
    all_good &= check("prompt worker-ui", (base / "orchestra/daemon/prompts/worker_ui.md").exists())

    print()

    # 3. Scripts de daemon
    print("[3] Scripts del Daemon")
    print("-"*60)

    all_good &= check("arquitecto_daemon.py", (base / "orchestra/daemon/arquitecto_daemon.py").exists())
    all_good &= check("worker_watchdog.py", (base / "orchestra/daemon/worker_watchdog.py").exists())
    all_good &= check("worker_report.py", (base / "orchestra/daemon/worker_report.py").exists())
    all_good &= check("docs_client.py", (base / "orchestra/daemon/docs_client.py").exists())

    print()

    # 4. Ordenes pendientes
    print("[4] Ordenes Pendientes para Workers")
    print("-"*60)

    try:
        r = requests.get("http://localhost:25500/api/v1/docs?limit=100", timeout=3)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("docs", [])

            # Contar ordenes por worker
            core_orders = len([d for d in docs if "worker-core" in str(d.get("tags", "")) and d.get("status") == "pending"])
            infra_orders = len([d for d in docs if "worker-infra" in str(d.get("tags", "")) and d.get("status") == "pending"])
            nlp_orders = len([d for d in docs if "worker-nlp" in str(d.get("tags", "")) and d.get("status") == "pending"])
            ui_orders = len([d for d in docs if "worker-ui" in str(d.get("tags", "")) and d.get("status") == "pending"])

            print(f"  worker-core:  {core_orders} ordenes pendientes")
            print(f"  worker-infra: {infra_orders} ordenes pendientes")
            print(f"  worker-nlp:   {nlp_orders} ordenes pendientes")
            print(f"  worker-ui:    {ui_orders} ordenes pendientes")

            if infra_orders > 0:
                check("Orden para worker-infra", True, "Lista para arrancar")
            else:
                check("Orden para worker-infra", False, "Publicar orden primero")

    except Exception as e:
        print(f"  Error consultando ordenes: {e}")

    print()

    # 5. Variable de entorno
    print("[5] Variables de Entorno")
    print("-"*60)

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    all_good &= check("ANTHROPIC_API_KEY", api_key is not None and api_key.startswith("sk-ant-"))

    print()

    # Resumen
    print("="*60)
    if all_good:
        print("[OK] SISTEMA LISTO PARA MULTI-WORKER")
        print()
        print("Siguiente paso:")
        print("  Ejecuta: orchestra\\start_multi_worker.bat")
        print()
        print("O manualmente:")
        print("  1. Terminal 1: cd orchestra\\daemon && python arquitecto_daemon.py")
        print("  2. Terminal 2-5: cd orchestra\\daemon && python worker_watchdog.py <worker-name>")
        print("  3. Abre 4 sesiones Claude Code y lee los prompts correspondientes")
        print()
        return 0
    else:
        print("[X] SISTEMA NO ESTA LISTO")
        print()
        print("Corrige los errores marcados con [X] y vuelve a ejecutar")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
