@echo off
REM ============================================================
REM   ORCHESTRA - ARRANQUE MULTI-WORKER
REM   Levanta todos los servicios y watchdogs necesarios
REM ============================================================

echo.
echo ============================================================
echo   INICIANDO ORCHESTRA - SISTEMA MULTI-WORKER
echo ============================================================
echo.

REM Cambiar al directorio correcto (donde esta el script)
cd /d "%~dp0\.."

REM Verificar que estamos en el directorio correcto
if not exist "orchestra" (
    echo [ERROR] No se pudo encontrar el directorio orchestra
    echo El script debe estar en E:\ianae-final\orchestra\
    pause
    exit /b 1
)

echo [INFO] Directorio de trabajo: %CD%
echo.

echo [1/6] Verificando servicios base...
echo.

REM Verificar docs-service
curl -s http://localhost:25500/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docs-service no esta activo en puerto 25500
    echo Arrancalo primero: cd orchestra\docs-service ^&^& python -m uvicorn app.main:app --port 25500
    pause
    exit /b 1
)
echo     [OK] docs-service activo

REM Verificar dashboard
curl -s http://localhost:25501/ >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Dashboard no activo en puerto 25501
    echo No es critico, pero puedes arrancarlo: cd src\ui ^&^& python -m uvicorn app.main:app --port 25501
) else (
    echo     [OK] Dashboard activo
)

echo.
echo [2/6] Arrancando daemon...
echo.
start "DAEMON-ARQUITECTO" cmd /k "cd orchestra\daemon && python arquitecto_daemon.py"
timeout /t 3 /nobreak >nul
echo     [OK] Daemon arrancado en nueva ventana

echo.
echo [3/6] Arrancando watchdog worker-core...
echo.
start "WATCHDOG-CORE" cmd /k "cd orchestra\daemon && python worker_watchdog.py worker-core"
timeout /t 2 /nobreak >nul
echo     [OK] Watchdog worker-core activo

echo.
echo [4/6] Arrancando watchdog worker-infra...
echo.
start "WATCHDOG-INFRA" cmd /k "cd orchestra\daemon && python worker_watchdog.py worker-infra"
timeout /t 2 /nobreak >nul
echo     [OK] Watchdog worker-infra activo

echo.
echo [5/6] Arrancando watchdog worker-nlp...
echo.
start "WATCHDOG-NLP" cmd /k "cd orchestra\daemon && python worker_watchdog.py worker-nlp"
timeout /t 2 /nobreak >nul
echo     [OK] Watchdog worker-nlp activo

echo.
echo [6/6] Arrancando watchdog worker-ui...
echo.
start "WATCHDOG-UI" cmd /k "cd orchestra\daemon && python worker_watchdog.py worker-ui"
timeout /t 2 /nobreak >nul
echo     [OK] Watchdog worker-ui activo

echo.
echo ============================================================
echo   SISTEMA MULTI-WORKER INICIADO
echo ============================================================
echo.
echo Ventanas abiertas:
echo   - DAEMON-ARQUITECTO (coordinador IA)
echo   - WATCHDOG-CORE (monitor worker-core)
echo   - WATCHDOG-INFRA (monitor worker-infra)
echo   - WATCHDOG-NLP (monitor worker-nlp)
echo   - WATCHDOG-UI (monitor worker-ui)
echo.
echo Proximos pasos:
echo   1. Abre 4 sesiones de Claude Code (una por worker)
echo   2. En cada una, lee el prompt correspondiente:
echo      - Worker-Core:  orchestra/daemon/prompts/worker_core.md
echo      - Worker-Infra: orchestra/daemon/prompts/worker_infra.md
echo      - Worker-NLP:   orchestra/daemon/prompts/worker_nlp.md
echo      - Worker-UI:    orchestra/daemon/prompts/worker_ui.md
echo   3. Los watchdogs mostraran las ordenes automaticamente
echo   4. Los workers ejecutan las tareas de forma autonoma
echo.
echo Dashboard: http://localhost:25501
echo.
echo Presiona Ctrl+C en cada ventana para detener
echo ============================================================
echo.
pause
