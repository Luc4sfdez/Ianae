# Guía de Coordinación Multi-Worker - IANAE Orchestra

**Versión:** 1.0
**Fecha:** 2026-02-10
**Estado:** Sistema listo para escalar a 4 workers en paralelo

---

## Resumen Ejecutivo

Sistema IANAE-Orchestra ahora soporta **múltiples workers trabajando en paralelo**, coordinados automáticamente por el daemon arquitecto. Esta guía explica cómo arrancar, coordinar y monitorear el sistema multi-worker.

**Capacidades:**
- ✅ 4 workers independientes (core, infra, nlp, ui)
- ✅ Coordinación automática por daemon
- ✅ Manejo de dependencias entre workers
- ✅ Dashboard en tiempo real
- ✅ Alertas y métricas consolidadas

---

## Arquitectura Multi-Worker

```
                 ┌─────────────────────┐
                 │  DAEMON ARQUITECTO  │
                 │    (Coordinador)    │
                 └──────────┬──────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ docs-service │  │  dashboard   │  │   watchdogs  │
    │   (25500)    │  │   (25501)    │  │ (4 procesos) │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                  │
           │    ┌────────────┴────────────┐     │
           │    │                         │     │
           ▼    ▼                         ▼     ▼
    ┌─────────────────────────────────────────────────┐
    │              WORKERS (Claude Code)              │
    ├─────────────┬─────────────┬──────────┬──────────┤
    │ worker-core │worker-infra │worker-nlp│worker-ui │
    │  (nucleo)   │   (tests)   │  (NLP)   │ (dashb.) │
    └─────────────┴─────────────┴──────────┴──────────┘
```

---

## Flujo de Trabajo Multi-Worker

### 1. Lucas publica orden inicial

```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -d '{"title":"ORDEN: ...", "tags":["worker-core"], ...}'
```

### 2. Daemon detecta orden (60s)

- Poll docs-service cada 60 segundos
- Detecta nuevos documentos
- Analiza si necesita actuar

### 3. Daemon decide acción

- Si es orden de Lucas → No interviene (ya publicada)
- Si es reporte de worker → Decide siguiente paso
- Si es duda → Responde automáticamente
- Si es bloqueo → Escala a Lucas

### 4. Watchdog muestra orden (30s)

- Consulta pendientes cada 30 segundos
- Muestra en terminal del worker
- Worker ve orden sin intervención

### 5. Worker ejecuta tarea

- Lee especificación completa
- Implementa solución
- Publica reporte al terminar

### 6. Ciclo se repite

- Daemon detecta reporte → API decide → Nueva orden
- Workers continúan autónomamente

---

## Dependencias Entre Workers

**Configuradas en `orchestra.yaml`:**

```yaml
workers:
  - name: "worker-core"
    depends_on: []              # Independiente

  - name: "worker-infra"
    depends_on: []              # Independiente (puede trabajar en paralelo)

  - name: "worker-nlp"
    depends_on: ["worker-core"] # Necesita core terminado

  - name: "worker-ui"
    depends_on: ["worker-core", "worker-infra"]  # Necesita ambos
```

**Interpretación:**
- **worker-core** y **worker-infra** pueden trabajar **simultáneamente**
- **worker-nlp** debe esperar a que core complete su fase numpy
- **worker-ui** necesita que core e infra terminen sus tareas base

**El daemon respeta estas dependencias al generar órdenes.**

---

## Escenarios de Coordinación

### Escenario A: Trabajo Paralelo Puro

```
T0: Lucas publica 2 órdenes
    - worker-core: "Optimizar propagación"
    - worker-infra: "Crear tests"

T1: Ambos workers arrancan simultáneamente
    - No hay dependencias entre ellos
    - Trabajan en archivos diferentes

T2: worker-infra termina primero (tests listos)
    - Publica reporte
    - Daemon genera nueva orden para infra

T3: worker-core termina después
    - Publica reporte
    - Daemon genera orden siguiente para core

Resultado: 2 reportes, 2 nuevas órdenes, sin conflictos
```

### Escenario B: Trabajo Secuencial con Dependencia

```
T0: worker-core trabaja en "Refactorizar nucleo.py a numpy"

T1: worker-nlp recibe orden "Integrar NLP con IANAE"
    - Detecta dependencia: needs worker-core
    - Daemon NO genera orden hasta que core termine

T2: worker-core completa refactorización
    - Publica reporte
    - Daemon verifica: core ahora estable

T3: Daemon genera orden para worker-nlp
    - "Integrar NLP con nuevo nucleo.py numpy"
    - Ahora sí puede arrancar

Resultado: Orden de nlp retrasada hasta que dependencia se cumple
```

### Escenario C: Duda de Worker Resuelta por Daemon

```
T0: worker-infra publicando tests
    - Se encuentra con duda: "¿qué framework usar para tests?"

T1: worker-infra publica DUDA (tag: duda)
    - No pregunta a Lucas
    - Publica como documento

T2: Daemon detecta duda (60s)
    - API Anthropic analiza contexto
    - Responde: "Usar pytest, compatible con actual"

T3: Watchdog muestra respuesta (30s)
    - worker-infra ve respuesta
    - Continúa trabajo sin bloqueo

Resultado: Duda resuelta automáticamente, sin intervención Lucas
```

---

## Arrancar Sistema Multi-Worker

### Opción 1: Script Automático (Recomendado)

```batch
cd E:\ianae-final
orchestra\start_multi_worker.bat
```

Esto abre 5 ventanas:
1. DAEMON-ARQUITECTO
2. WATCHDOG-CORE
3. WATCHDOG-INFRA
4. WATCHDOG-NLP
5. WATCHDOG-UI

### Opción 2: Manual

```batch
# Terminal 1: docs-service (si no está activo)
cd E:\ianae-final\orchestra\docs-service
python -m uvicorn app.main:app --port 25500

# Terminal 2: daemon
cd E:\ianae-final\orchestra\daemon
python arquitecto_daemon.py

# Terminal 3-6: watchdogs
python worker_watchdog.py worker-core
python worker_watchdog.py worker-infra
python worker_watchdog.py worker-nlp
python worker_watchdog.py worker-ui

# Terminal 7 (opcional): dashboard
cd E:\ianae-final\src\ui
python -m uvicorn app.main:app --port 25501
```

### Abrir Workers (Claude Code)

Para cada worker, abrir sesión de Claude Code y leer prompt:

```
Worker-Core:  orchestra/daemon/prompts/worker_core.md
Worker-Infra: orchestra/daemon/prompts/worker_infra.md
Worker-NLP:   orchestra/daemon/prompts/worker_nlp.md
Worker-UI:    orchestra/daemon/prompts/worker_ui.md
```

**Importante:** Los workers NO deben preguntarte nada. Si tienen dudas, publican documento con tag "duda" y el daemon responde automáticamente.

---

## Monitoreo del Sistema

### Dashboard Web

**URL:** http://localhost:25501

**Vista consolidada:**
- Estado de todos los workers
- Métricas en tiempo real
- Alertas del sistema
- Timeline de actividad

**Actualización:** Cada 10 segundos automáticamente

### Logs del Daemon

```bash
tail -f E:/ianae-final/orchestra/daemon/logs/arquitecto.log
```

**Formato estructurado (JSON):**
```bash
tail -f E:/ianae-final/orchestra/daemon/logs/arquitecto_structured.json
```

### Consulta Directa

```bash
# Ver todas las órdenes pendientes
curl http://localhost:25500/api/v1/docs?limit=20

# Ver órdenes de worker específico
curl http://localhost:25500/api/v1/worker/worker-core/pendientes

# Ver métricas del sistema
curl http://localhost:25501/api/metrics

# Ver alertas activas
curl http://localhost:25501/api/alerts
```

---

## Métricas Multi-Worker

### Throughput

**Fórmula:** Tareas completadas / tiempo

**Objetivo:** 5-10 tareas/día con 3-4 workers activos

**Medición:**
```bash
curl -s http://localhost:25501/api/metrics | jq '.quality'
```

### Autonomía

**Fórmula:** (órdenes - escalados) / órdenes × 100

**Objetivo:** ≥80% autonomía (sin intervención Lucas)

**Interpretación:**
- >80%: Sistema muy autónomo
- 60-80%: Bueno
- <60%: Necesita ajustes en prompts o arquitectura

### Coordinación

**Indicador:** Conflictos / tareas totales

**Conflictos:** Situaciones donde 2 workers modifican mismo archivo

**Objetivo:** 0 conflictos (workers trabajan en archivos diferentes)

---

## Resolución de Problemas

### Worker no ve órdenes

**Síntoma:** Watchdog muestra "0 pendientes" pero hay órdenes en docs-service

**Causa:** Tags incorrectos en la orden

**Solución:**
```bash
# Verificar tags de la orden
curl http://localhost:25500/api/v1/docs/<id>

# Debe contener ["worker-XXX"] en tags
```

### Daemon no genera órdenes

**Síntoma:** Workers completan tareas pero no reciben siguiente orden

**Causa 1:** Límite API alcanzado (100 calls/día)

**Solución:** Esperar a medianoche o aumentar MAX_DAILY_API_CALLS en config.py

**Causa 2:** Daemon detecta sus propias órdenes

**Solución:** Verificar IGNORE_AUTHORS incluye "arquitecto-daemon"

### Workers en conflicto

**Síntoma:** 2 workers modifican mismo archivo simultáneamente

**Causa:** Dependencias mal configuradas en orchestra.yaml

**Solución:** Revisar depends_on y ajustar scopes

### API Anthropic timeout

**Síntoma:** Daemon falla con error de API

**Causa:** Red lenta o API Anthropic caída

**Solución:** Sistema tiene retry automático con backoff (3 intentos)
- Si 3 fallos consecutivos → Circuit breaker (60s cooldown)
- Logs muestran detalles en arquitecto_structured.json

---

## Escalado a Más Workers

### Añadir Worker Nuevo

1. **Crear prompt:**
```bash
orchestra/daemon/prompts/worker_nuevo.md
```

2. **Añadir a orchestra.yaml:**
```yaml
  - name: "worker-nuevo"
    scope: "nuevo/scope/"
    prompt: "orchestra/daemon/prompts/worker_nuevo.md"
    priority: 5
    depends_on: []
```

3. **Arrancar watchdog:**
```bash
python worker_watchdog.py worker-nuevo
```

4. **Publicar orden inicial:**
```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -d '{"title":"ORDEN: ...", "tags":["worker-nuevo"], ...}'
```

5. **Abrir sesión Claude Code** y leer prompt

---

## Límites del Sistema

### Límites Técnicos

- **Workers simultáneos:** 4-6 (limitado por API Anthropic rate limits)
- **API calls diarios:** 100 (configurable en config.py)
- **Polling interval:** 60s (daemon), 30s (watchdogs)
- **Tamaño de órdenes:** ~4096 tokens (max_tokens en API)

### Límites Prácticos

- **Coordinación:** 3-4 workers es óptimo (más → complejidad)
- **Throughput:** 5-10 tareas/día sostenible
- **Contexto:** Daemon mantiene snapshot limitado (últimos docs)

---

## Mejores Prácticas

### Para Órdenes

1. **Claridad:** Especificación detallada, criterios de hecho concretos
2. **Scope:** Limitar a 1 archivo o módulo por orden
3. **Tags:** Siempre incluir worker correcto
4. **Prioridad:** alta/media/baja según urgencia

### Para Workers

1. **Autonomía:** NUNCA preguntar a Lucas, publicar dudas
2. **Reportes:** Siempre publicar al terminar (trigger siguiente orden)
3. **Workflow:** Actualizar workflow_status (pending→in_progress→completed)
4. **Testing:** Ejecutar tests antes de publicar reporte

### Para Daemon

1. **Monitoring:** Revisar logs/arquitecto.log diariamente
2. **API Budget:** No superar 80% del límite diario
3. **Alertas:** Responder a alertas críticas en <1h
4. **Escalados:** Si autonomía <60%, revisar prompts

---

## Roadmap Multi-Worker

### Fase C.1 ✅ Completado
- ✅ Órdenes iniciales publicadas
- ✅ Scripts de arranque creados
- ✅ Documentación completa
- ✅ Sistema verificado

### Fase C.2 En Progreso
- ⏳ Arrancar worker-infra (manual Lucas)
- ⏳ Arrancar worker-nlp (manual Lucas)
- ⏳ Verificar coordinación en práctica

### Fase C.3 Pendiente
- ⏸️ Escenario de prueba multi-worker
- ⏸️ Optimización de coordinación
- ⏸️ Métricas de throughput real

---

## Comandos Rápidos

```bash
# Verificar sistema listo
python orchestra/verify_ready_for_multiworker.py

# Arrancar todo
orchestra\start_multi_worker.bat

# Ver órdenes pendientes de un worker
curl http://localhost:25500/api/v1/worker/worker-infra/pendientes

# Ver métricas consolidadas
curl http://localhost:25501/api/metrics | jq

# Ver alertas
curl http://localhost:25501/api/alerts | jq

# Dashboard
start http://localhost:25501

# Logs en tiempo real
tail -f orchestra/daemon/logs/arquitecto.log
```

---

## Soporte

**Problemas comunes:** Ver sección "Resolución de Problemas"
**Logs:** `orchestra/daemon/logs/arquitecto.log`
**Dashboard:** http://localhost:25501
**Documentación:** `orchestra/IANAE_ORCHESTRA_DESPLIEGUE_COMPLETO.md`

---

**Estado:** Sistema listo para escalar. Siguiente paso: Lucas arranca workers y valida coordinación en práctica.
