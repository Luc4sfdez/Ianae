# Instrucciones de Arranque - Sistema Multi-Worker

**Fecha:** 2026-02-10
**Sistema:** IANAE-Orchestra

---

## Arranque Rápido

### Opción 1: Doble clic (Recomendado)

Simplemente haz **doble clic** en:
```
E:\ianae-final\orchestra\start_multi_worker.bat
```

El script ahora detecta automáticamente la ruta correcta.

### Opción 2: Desde línea de comandos

```cmd
REM Desde cualquier ubicación:
E:\ianae-final\orchestra\start_multi_worker.bat

REM O navega primero:
cd E:\ianae-final
orchestra\start_multi_worker.bat
```

---

## ¿Qué hace el script?

**Abre 5 ventanas automáticamente:**

1. **DAEMON-ARQUITECTO**
   - Coordina todos los workers
   - Detecta nuevas órdenes cada 60s
   - Genera respuestas vía API Anthropic

2. **WATCHDOG-CORE**
   - Monitorea órdenes para worker-core
   - Muestra nuevas tareas cada 30s

3. **WATCHDOG-INFRA**
   - Monitorea órdenes para worker-infra
   - Muestra nuevas tareas cada 30s

4. **WATCHDOG-NLP**
   - Monitorea órdenes para worker-nlp
   - Muestra nuevas tareas cada 30s

5. **WATCHDOG-UI**
   - Monitorea órdenes para worker-ui
   - Muestra nuevas tareas cada 30s

---

## Requisitos Previos

### 1. docs-service debe estar activo

**Verificar:**
```cmd
curl http://localhost:25500/health
```

**Debería responder:**
```json
{"status":"ok","service":"docs-service-ianae","port":25500}
```

**Si NO está activo, arrancarlo:**
```cmd
cd E:\ianae-final\orchestra\docs-service
python -m uvicorn app.main:app --port 25500
```

### 2. dashboard (opcional pero recomendado)

**Verificar:**
```cmd
curl http://localhost:25501/
```

**Si NO está activo, arrancarlo:**
```cmd
cd E:\ianae-final\src\ui
python -m uvicorn app.main:app --port 25501
```

---

## Después de Arrancar

### Paso 1: Verificar ventanas abiertas

Deberías ver 5 ventanas de cmd:
- ✅ DAEMON-ARQUITECTO
- ✅ WATCHDOG-CORE
- ✅ WATCHDOG-INFRA
- ✅ WATCHDOG-NLP
- ✅ WATCHDOG-UI

### Paso 2: Abrir sesiones Claude Code

Abre **4 sesiones de Claude Code** (una por worker):

**Sesión 1 - Worker-Core:**
- Directorio: `E:\ianae-final`
- Leer: `orchestra/daemon/prompts/worker_core.md`
- Responsabilidad: Optimizaciones numpy en nucleo.py

**Sesión 2 - Worker-Infra:**
- Directorio: `E:\ianae-final`
- Leer: `orchestra/daemon/prompts/worker_infra.md`
- Responsabilidad: Tests, Docker, CI/CD

**Sesión 3 - Worker-NLP:**
- Directorio: `E:\ianae-final`
- Leer: `orchestra/daemon/prompts/worker_nlp.md`
- Responsabilidad: Integración NLP, embeddings

**Sesión 4 - Worker-UI:**
- Directorio: `E:\ianae-final`
- Leer: `orchestra/daemon/prompts/worker_ui.md`
- Responsabilidad: Dashboard avanzado, D3.js, WebSocket

### Paso 3: Workers ven órdenes automáticamente

**NO necesitas hacer nada más:**
- Cada watchdog muestra órdenes nuevas cada 30s
- Workers las ven en su terminal
- Workers las ejecutan autónomamente
- Workers publican reportes al terminar
- Daemon detecta reportes y genera siguiente orden

**El ciclo continúa sin intervención humana.**

---

## Monitoreo

### Dashboard Web

**URL:** http://localhost:25501

**Actualización:** Automática cada 10s

**Muestra:**
- Estado de todos los workers
- Documentos recientes
- Métricas de calidad
- Alertas del sistema

### Logs del Daemon

**Ver en tiempo real:**
```cmd
tail -f E:\ianae-final\orchestra\daemon\logs\arquitecto.log
```

**O en Windows:**
```cmd
type E:\ianae-final\orchestra\daemon\logs\arquitecto.log
```

### Consultas API

**Órdenes pendientes:**
```cmd
curl http://localhost:25500/api/v1/worker/worker-core/pendientes
curl http://localhost:25500/api/v1/worker/worker-infra/pendientes
curl http://localhost:25500/api/v1/worker/worker-nlp/pendientes
curl http://localhost:25500/api/v1/worker/worker-ui/pendientes
```

**Métricas:**
```cmd
curl http://localhost:25501/api/metrics
```

**Alertas:**
```cmd
curl http://localhost:25501/api/alerts
```

---

## Detener el Sistema

### Opción 1: Cerrar ventanas individualmente

Presiona `Ctrl+C` en cada ventana:
1. DAEMON-ARQUITECTO
2. WATCHDOG-CORE
3. WATCHDOG-INFRA
4. WATCHDOG-NLP
5. WATCHDOG-UI

### Opción 2: Cerrar todas las ventanas

Cierra las 5 ventanas de cmd que se abrieron.

**Nota:** Los workers de Claude Code pueden seguir ejecutando tareas, pero ya no verán órdenes nuevas hasta que arranques el sistema de nuevo.

---

## Solución de Problemas

### Error: "docs-service no esta activo en puerto 25500"

**Solución:**
```cmd
cd E:\ianae-final\orchestra\docs-service
python -m uvicorn app.main:app --port 25500
```

Luego ejecuta `start_multi_worker.bat` de nuevo.

### Error: "No se pudo encontrar el directorio orchestra"

**Causa:** El script no está en la ubicación correcta.

**Solución:** Verifica que el archivo esté en:
```
E:\ianae-final\orchestra\start_multi_worker.bat
```

### Watchdog no muestra órdenes

**Verificar que hay órdenes pendientes:**
```cmd
curl http://localhost:25500/api/v1/worker/worker-core/pendientes
```

**Si no hay órdenes:** Es normal, significa que el worker no tiene tareas asignadas aún.

### Daemon no arranca

**Verificar API key:**
```cmd
echo %ANTHROPIC_API_KEY%
```

**Debe mostrar:** `sk-ant-...`

**Si está vacía:**
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Órdenes Actuales Publicadas

Actualmente hay **5 órdenes** publicadas:

1. **#5** - worker-core: A.1 Fase 1 (numpy básico)
2. **#18** - worker-infra: A.2 Bloque 1 (tests)
3. **#19** - worker-nlp: A.3 Fase 1 (investigación NLP)
4. **#23** - worker-infra: A.2 Bloque 2 (Docker + CI/CD)
5. **#24** - worker-ui: A.4 Completo (dashboard avanzado)

**Los workers comenzarán a ejecutarlas automáticamente tras arranque.**

---

## Siguiente Paso

**Simplemente ejecuta:**
```cmd
E:\ianae-final\orchestra\start_multi_worker.bat
```

**Y abre 4 sesiones Claude Code.**

**El sistema hará el resto automáticamente.**

---

**¿Preguntas? Revisa:**
- `orchestra/GUIA_MULTI_WORKER.md` - Guía completa de coordinación
- `orchestra/ROADMAP_FASE_A.md` - Plan detallado Fase A
- `orchestra/ESTADO_PROYECTO_COMPLETO.md` - Estado global del proyecto
