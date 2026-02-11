@echo off
REM ============================================================
REM   IANAE-ORCHESTRA - INICIAR TODO EL SISTEMA
REM   Abre: Servicios + VSCode + 5 Sesiones Claude Code
REM ============================================================

echo.
echo ============================================================
echo   IANAE-ORCHESTRA - INICIAR SISTEMA COMPLETO
echo ============================================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0\.."

REM ============================================================
REM   PASO 1: VERIFICAR SERVICIOS BASE
REM ============================================================

echo [1/8] Verificando servicios base...
echo.

REM Verificar docs-service
curl -s http://localhost:25500/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] Arrancando docs-service...
    start "DOCS-SERVICE" cmd /k "cd E:\ianae-final\orchestra\docs-service && python -m uvicorn app.main:app --port 25500"
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] docs-service ya activo
)

REM Verificar dashboard
curl -s http://localhost:25501/ >nul 2>&1
if errorlevel 1 (
    echo [INFO] Arrancando dashboard...
    start "DASHBOARD" cmd /k "cd E:\ianae-final\src\ui && python -m uvicorn app.main:app --port 25501"
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] Dashboard ya activo
)

echo.
echo [2/8] Servicios base verificados

REM ============================================================
REM   PASO 2: ARRANCAR DAEMON Y WATCHDOGS
REM ============================================================

echo.
echo [3/8] Arrancando daemon arquitecto...
echo.
start "DAEMON-ARQUITECTO" cmd /k "cd E:\ianae-final\orchestra\daemon && python arquitecto_daemon.py"
timeout /t 3 /nobreak >nul

echo.
echo [4/8] Arrancando 4 watchdogs...
echo.
start "WATCHDOG-CORE" cmd /k "cd E:\ianae-final\orchestra\daemon && python worker_watchdog.py worker-core"
timeout /t 2 /nobreak >nul

start "WATCHDOG-INFRA" cmd /k "cd E:\ianae-final\orchestra\daemon && python worker_watchdog.py worker-infra"
timeout /t 2 /nobreak >nul

start "WATCHDOG-NLP" cmd /k "cd E:\ianae-final\orchestra\daemon && python worker_watchdog.py worker-nlp"
timeout /t 2 /nobreak >nul

start "WATCHDOG-UI" cmd /k "cd E:\ianae-final\orchestra\daemon && python worker_watchdog.py worker-ui"
timeout /t 2 /nobreak >nul

echo [OK] 4 watchdogs activos

REM ============================================================
REM   PASO 3: ABRIR VSCODE
REM ============================================================

echo.
echo [5/8] Abriendo VSCode en E:\ianae-final...
echo.

REM Intentar abrir con VSCode (buscar en rutas comunes)
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe" (
    start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe" "E:\ianae-final"
    echo [OK] VSCode abierto
) else if exist "C:\Program Files\Microsoft VS Code\Code.exe" (
    start "" "C:\Program Files\Microsoft VS Code\Code.exe" "E:\ianae-final"
    echo [OK] VSCode abierto
) else (
    echo [WARNING] VSCode no encontrado en rutas comunes
    echo Puedes abrirlo manualmente en: E:\ianae-final
)

timeout /t 3 /nobreak >nul

REM ============================================================
REM   PASO 4: ABRIR CLAUDE CODE - ARQUITECTO MAESTRO
REM ============================================================

echo.
echo [6/8] Abriendo Claude Code - Arquitecto Maestro...
echo.

REM Crear script temporal para arquitecto
echo @echo off > "%TEMP%\open_arquitecto.bat"
echo cd /d E:\ianae-final >> "%TEMP%\open_arquitecto.bat"
echo echo. >> "%TEMP%\open_arquitecto.bat"
echo echo ======================================= >> "%TEMP%\open_arquitecto.bat"
echo echo   ARQUITECTO MAESTRO - IANAE Orchestra >> "%TEMP%\open_arquitecto.bat"
echo echo ======================================= >> "%TEMP%\open_arquitecto.bat"
echo echo. >> "%TEMP%\open_arquitecto.bat"
echo echo LEE EL PROMPT: >> "%TEMP%\open_arquitecto.bat"
echo echo   orchestra/daemon/prompts/arquitecto_maestro.md >> "%TEMP%\open_arquitecto.bat"
echo echo. >> "%TEMP%\open_arquitecto.bat"
echo echo COMANDOS UTILES: >> "%TEMP%\open_arquitecto.bat"
echo echo   curl http://localhost:25500/api/v1/docs?limit=20 >> "%TEMP%\open_arquitecto.bat"
echo echo   curl http://localhost:25500/api/v1/comunicacion >> "%TEMP%\open_arquitecto.bat"
echo echo   curl http://localhost:25501/api/metrics >> "%TEMP%\open_arquitecto.bat"
echo echo. >> "%TEMP%\open_arquitecto.bat"
echo pause >> "%TEMP%\open_arquitecto.bat"

start "ARQUITECTO MAESTRO" cmd /k "%TEMP%\open_arquitecto.bat"

echo [INFO] Ventana abierta: ARQUITECTO MAESTRO
echo        Abre Claude Code y lee: orchestra/daemon/prompts/arquitecto_maestro.md
timeout /t 3 /nobreak >nul

REM ============================================================
REM   PASO 5: ABRIR CLAUDE CODE - 4 WORKERS
REM ============================================================

echo.
echo [7/8] Abriendo Claude Code - 4 Workers...
echo.

REM Worker-Core
echo @echo off > "%TEMP%\open_worker_core.bat"
echo cd /d E:\ianae-final >> "%TEMP%\open_worker_core.bat"
echo echo. >> "%TEMP%\open_worker_core.bat"
echo echo ======================================= >> "%TEMP%\open_worker_core.bat"
echo echo   WORKER-CORE - Nucleo IANAE >> "%TEMP%\open_worker_core.bat"
echo echo ======================================= >> "%TEMP%\open_worker_core.bat"
echo echo. >> "%TEMP%\open_worker_core.bat"
echo echo LEE EL PROMPT: >> "%TEMP%\open_worker_core.bat"
echo echo   orchestra/daemon/prompts/worker_core.md >> "%TEMP%\open_worker_core.bat"
echo echo. >> "%TEMP%\open_worker_core.bat"
echo echo SCOPE: src/core/nucleo.py, emergente.py >> "%TEMP%\open_worker_core.bat"
echo echo. >> "%TEMP%\open_worker_core.bat"
echo pause >> "%TEMP%\open_worker_core.bat"

start "WORKER-CORE" cmd /k "%TEMP%\open_worker_core.bat"
timeout /t 2 /nobreak >nul

REM Worker-Infra
echo @echo off > "%TEMP%\open_worker_infra.bat"
echo cd /d E:\ianae-final >> "%TEMP%\open_worker_infra.bat"
echo echo. >> "%TEMP%\open_worker_infra.bat"
echo echo ======================================= >> "%TEMP%\open_worker_infra.bat"
echo echo   WORKER-INFRA - Tests/Docker/CI >> "%TEMP%\open_worker_infra.bat"
echo echo ======================================= >> "%TEMP%\open_worker_infra.bat"
echo echo. >> "%TEMP%\open_worker_infra.bat"
echo echo LEE EL PROMPT: >> "%TEMP%\open_worker_infra.bat"
echo echo   orchestra/daemon/prompts/worker_infra.md >> "%TEMP%\open_worker_infra.bat"
echo echo. >> "%TEMP%\open_worker_infra.bat"
echo echo SCOPE: tests/, docker/, pyproject.toml >> "%TEMP%\open_worker_infra.bat"
echo echo. >> "%TEMP%\open_worker_infra.bat"
echo pause >> "%TEMP%\open_worker_infra.bat"

start "WORKER-INFRA" cmd /k "%TEMP%\open_worker_infra.bat"
timeout /t 2 /nobreak >nul

REM Worker-NLP
echo @echo off > "%TEMP%\open_worker_nlp.bat"
echo cd /d E:\ianae-final >> "%TEMP%\open_worker_nlp.bat"
echo echo. >> "%TEMP%\open_worker_nlp.bat"
echo echo ======================================= >> "%TEMP%\open_worker_nlp.bat"
echo echo   WORKER-NLP - Procesamiento Lenguaje >> "%TEMP%\open_worker_nlp.bat"
echo echo ======================================= >> "%TEMP%\open_worker_nlp.bat"
echo echo. >> "%TEMP%\open_worker_nlp.bat"
echo echo LEE EL PROMPT: >> "%TEMP%\open_worker_nlp.bat"
echo echo   orchestra/daemon/prompts/worker_nlp.md >> "%TEMP%\open_worker_nlp.bat"
echo echo. >> "%TEMP%\open_worker_nlp.bat"
echo echo SCOPE: src/nlp/, integrations/ >> "%TEMP%\open_worker_nlp.bat"
echo echo DEPENDENCIA: Espera Core Fase 2 >> "%TEMP%\open_worker_nlp.bat"
echo echo. >> "%TEMP%\open_worker_nlp.bat"
echo pause >> "%TEMP%\open_worker_nlp.bat"

start "WORKER-NLP" cmd /k "%TEMP%\open_worker_nlp.bat"
timeout /t 2 /nobreak >nul

REM Worker-UI
echo @echo off > "%TEMP%\open_worker_ui.bat"
echo cd /d E:\ianae-final >> "%TEMP%\open_worker_ui.bat"
echo echo. >> "%TEMP%\open_worker_ui.bat"
echo echo ======================================= >> "%TEMP%\open_worker_ui.bat"
echo echo   WORKER-UI - Dashboard/API REST >> "%TEMP%\open_worker_ui.bat"
echo echo ======================================= >> "%TEMP%\open_worker_ui.bat"
echo echo. >> "%TEMP%\open_worker_ui.bat"
echo echo LEE EL PROMPT: >> "%TEMP%\open_worker_ui.bat"
echo echo   orchestra/daemon/prompts/worker_ui.md >> "%TEMP%\open_worker_ui.bat"
echo echo. >> "%TEMP%\open_worker_ui.bat"
echo echo SCOPE: src/ui/, api/ >> "%TEMP%\open_worker_ui.bat"
echo echo DEPENDENCIA: Espera Core API >> "%TEMP%\open_worker_ui.bat"
echo echo. >> "%TEMP%\open_worker_ui.bat"
echo pause >> "%TEMP%\open_worker_ui.bat"

start "WORKER-UI" cmd /k "%TEMP%\open_worker_ui.bat"
timeout /t 2 /nobreak >nul

echo [OK] 4 workers abiertos

REM ============================================================
REM   PASO 6: RESUMEN FINAL
REM ============================================================

echo.
echo [8/8] Sistema completamente iniciado
echo.
echo ============================================================
echo   SISTEMA IANAE-ORCHESTRA ACTIVO
echo ============================================================
echo.
echo SERVICIOS:
echo   [OK] docs-service   - http://localhost:25500
echo   [OK] dashboard      - http://localhost:25501
echo   [OK] daemon         - Polling cada 60s
echo   [OK] 4 watchdogs    - Polling cada 30s
echo.
echo DESARROLLO:
echo   [OK] VSCode         - E:\ianae-final
echo   [OK] 5 ventanas Claude Code:
echo        - ARQUITECTO MAESTRO (coordinador)
echo        - WORKER-CORE (nucleo.py)
echo        - WORKER-INFRA (tests/docker)
echo        - WORKER-NLP (procesamiento texto)
echo        - WORKER-UI (dashboard/api)
echo.
echo PROXIMOS PASOS:
echo   1. En cada ventana de worker, abre Claude Code
echo   2. Lee el prompt correspondiente (ya mostrado)
echo   3. Workers y arquitecto trabajaran autonomamente
echo   4. Monitorea en: http://localhost:25501
echo.
echo ARQUITECTO MAESTRO:
echo   - Coordina a los 4 workers
echo   - Decide prioridades y dependencias
echo   - Resuelve bloqueos automaticamente
echo   - Revisa progreso cada 5 minutos
echo.
echo Dashboard: http://localhost:25501
echo.
echo Para detener: Cierra las ventanas de cmd
echo ============================================================
echo.
pause
