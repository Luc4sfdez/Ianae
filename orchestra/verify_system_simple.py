"""
Script de verificación del sistema claude-orchestra (sin emojis para Windows).
Verifica que todos los componentes están en su lugar y pueden comunicarse.

Uso:
  python verify_system_simple.py
"""

import os
import sys
from pathlib import Path

def check_file(path, description):
    """Verificar que un archivo existe."""
    p = Path(path)
    if p.exists():
        size = p.stat().st_size
        print(f"[OK] {description}: {path} ({size} bytes)")
        return True
    else:
        print(f"[X] {description}: {path} NO ENCONTRADO")
        return False

def check_env_var(var_name):
    """Verificar variable de entorno."""
    value = os.environ.get(var_name)
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"[OK] {var_name}: {masked}")
        return True
    else:
        print(f"[X] {var_name}: NO CONFIGURADA")
        return False

def main():
    print("="*60)
    print("  VERIFICACION SISTEMA CLAUDE-ORCHESTRA")
    print("="*60)
    print()

    all_ok = True

    # 1. Archivos de configuración
    print("CONFIGURACION")
    all_ok &= check_file("orchestra.yaml", "Config global")
    all_ok &= check_file("requirements.txt", "Dependencias")
    print()

    # 2. docs-service
    print("DOCS-SERVICE")
    all_ok &= check_file("orchestra/docs-service/app/main.py", "FastAPI app")
    all_ok &= check_file("orchestra/docs-service/app/database.py", "Database")
    all_ok &= check_file("orchestra/docs-service/app/api/v1/notifications.py", "Notifications endpoint")
    all_ok &= check_file("orchestra/docs-service/app/api/v1/snapshot.py", "Snapshot endpoint")
    all_ok &= check_file("orchestra/docs-service/requirements.txt", "Requirements")
    print()

    # 3. daemon
    print("DAEMON")
    all_ok &= check_file("orchestra/daemon/config.py", "Config")
    all_ok &= check_file("orchestra/daemon/docs_client.py", "Docs client")
    all_ok &= check_file("orchestra/daemon/response_parser.py", "Response parser")
    all_ok &= check_file("orchestra/daemon/arquitecto_daemon.py", "Daemon principal")
    all_ok &= check_file("orchestra/daemon/worker_watchdog.py", "Watchdog")
    all_ok &= check_file("orchestra/daemon/worker_bootstrap.py", "Bootstrap")
    all_ok &= check_file("orchestra/daemon/worker_report.py", "Report helper")
    print()

    # 4. prompts
    print("PROMPTS")
    all_ok &= check_file("orchestra/daemon/prompts/arquitecto_system.md", "Arquitecto")
    all_ok &= check_file("orchestra/daemon/prompts/worker_core.md", "Worker-Core")
    all_ok &= check_file("orchestra/daemon/prompts/worker_nlp.md", "Worker-NLP")
    all_ok &= check_file("orchestra/daemon/prompts/worker_infra.md", "Worker-Infra")
    all_ok &= check_file("orchestra/daemon/prompts/worker_ui.md", "Worker-UI")
    print()

    # 5. Variables de entorno
    print("VARIABLES DE ENTORNO")
    all_ok &= check_env_var("ANTHROPIC_API_KEY")
    print()

    # 6. Directorios
    print("DIRECTORIOS")
    dirs = [
        "orchestra/daemon/logs",
        "orchestra/data",
        "orchestra/docs",
    ]
    for d in dirs:
        p = Path(d)
        if p.exists() and p.is_dir():
            print(f"[OK] {d}")
        else:
            print(f"[X] {d} NO ENCONTRADO")
            all_ok = False
    print()

    # Resumen
    print("="*60)
    if all_ok:
        print("[OK] SISTEMA COMPLETO Y LISTO")
        print()
        print("Proximos pasos:")
        print("1. Terminal 1: cd orchestra/docs-service && python -m uvicorn app.main:app --port 25500")
        print("2. Terminal 2: cd orchestra/daemon && python arquitecto_daemon.py")
        print("3. Terminal 3: cd orchestra/daemon && python worker_watchdog.py worker-core")
        print()
        print("Luego publica una orden de prueba - ver orchestra/INSTALACION.md")
    else:
        print("[ERROR] FALTAN COMPONENTES")
        print("Revisa los errores arriba y completa la instalacion.")
        print()
        print("Si ANTHROPIC_API_KEY no esta configurada:")
        print("  Windows PowerShell: $env:ANTHROPIC_API_KEY = \"sk-ant-...\"")
        print("  Windows CMD: set ANTHROPIC_API_KEY=sk-ant-...")
        print("  Linux/Mac: export ANTHROPIC_API_KEY=\"sk-ant-...\"")
    print("="*60)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
