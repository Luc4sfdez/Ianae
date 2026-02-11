# Guía del Arquitecto Maestro - IANAE Orchestra

**Versión:** 2.0 (Sistema Coordinado)
**Fecha:** 2026-02-10
**Mejora:** Arquitecto Maestro + Coordinación entre Workers

---

## ¿Qué es el Arquitecto Maestro?

El **Arquitecto Maestro** es una sesión dedicada de Claude Code que coordina activamente a los 4 workers (core, infra, nlp, ui) durante el desarrollo autónomo de IANAE.

### Diferencia con el Sistema Anterior

**Sistema Anterior (v1.0):**
```
Worker → Reporte → Daemon detecta (60s) → API decide → Nueva orden
```
- ❌ Reactivo (polling cada 60s)
- ❌ Sin coordinación entre workers
- ❌ Sin vista global

**Sistema Nuevo (v2.0):**
```
                ┌─────────────────┐
                │   ARQUITECTO    │
                │    MAESTRO      │
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │Worker  │      │Worker  │      │Worker  │
    │ Core   │      │ Infra  │      │  NLP   │
    └────────┘      └────────┘      └────────┘
```
- ✅ Proactivo (revisa cada 5min)
- ✅ Coordina dependencias
- ✅ Vista global del progreso
- ✅ Resuelve conflictos
- ✅ Optimiza trabajo paralelo

---

## Arranque del Sistema Completo

### Opción 1: Script Automático (Recomendado)

**Ejecuta:**
```cmd
E:\ianae-final\orchestra\INICIAR_TODO.bat
```

**Esto abre automáticamente:**
1. ✅ docs-service (25500)
2. ✅ dashboard (25501)
3. ✅ daemon arquitecto
4. ✅ 4 watchdogs (core, infra, nlp, ui)
5. ✅ VSCode en E:\ianae-final
6. ✅ 5 ventanas para Claude Code:
   - ARQUITECTO MAESTRO
   - WORKER-CORE
   - WORKER-INFRA
   - WORKER-NLP
   - WORKER-UI

### Opción 2: Manual

Si prefieres arrancar paso a paso, ver `orchestra/start_multi_worker.bat` y abrir las sesiones Claude Code manualmente.

---

## Flujo de Trabajo del Arquitecto Maestro

### Ciclo cada 5 minutos

```
1. LEER estado global
   ├─ Últimos 30 documentos
   ├─ Canal de comunicación
   └─ Órdenes pendientes por worker

2. ANALIZAR situación
   ├─ ¿Qué workers completaron tareas?
   ├─ ¿Hay bloqueos?
   ├─ ¿Dependencias cumplidas?
   └─ ¿Qué puede trabajar en paralelo?

3. DECIDIR siguiente paso
   ├─ Priorizar tareas críticas
   ├─ Coordinar trabajo paralelo
   ├─ Resolver dependencias
   └─ Asignar órdenes

4. PUBLICAR coordinación
   ├─ Órdenes específicas por worker
   ├─ Contexto de decisión
   └─ Prioridades claras

5. ESPERAR 5 minutos → Repetir
```

---

## Protocolo de Comunicación

### Workers → Arquitecto

**Mensaje de Progreso:**

```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "PROGRESO: Worker-Core completó Fase 1",
    "content": "# PROGRESO\n\n**Orden:** #5\n**Estado:** COMPLETADO\n**Tests:** Todos pasan\n**Siguiente propuesto:** Fase 2 - Índice espacial\n**Consulta:** ¿Continuar o esperar validación?",
    "category": "comunicacion",
    "author": "worker-core",
    "tags": ["comunicacion", "progreso", "worker-core"],
    "priority": "media"
  }'
```

**Mensaje de Bloqueo:**

```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "BLOQUEO: Worker-NLP esperando Core Fase 2",
    "content": "# BLOQUEO\n\n**Razón:** Necesito índice espacial de nucleo.py\n**Estado actual:** Investigación completa\n**Propuesta:** ¿Diseñar arquitectura mientras espero?",
    "category": "comunicacion",
    "author": "worker-nlp",
    "tags": ["comunicacion", "bloqueo", "worker-nlp"],
    "priority": "alta"
  }'
```

### Arquitecto → Workers

**Coordinación:**

```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "COORDINACION: Continuar desarrollo paralelo",
    "content": "# COORDINACION\n\n## Worker-Core\nContinuar Fase 2 (KDTree). No esperar validación.\n\n## Worker-Infra\nPublicar reporte #18+#23 y arrancar Bloque 4.\n\n## Worker-NLP\nDiseñar arquitectura pipeline. Implementación cuando Core Fase 2 termine.\n\n## Justificación\nCore y Infra no tienen conflictos de archivos.",
    "category": "coordinacion",
    "author": "arquitecto-maestro",
    "tags": ["coordinacion", "worker-core", "worker-infra", "worker-nlp"],
    "priority": "alta"
  }'
```

---

## Responsabilidades del Arquitecto

### 1. Monitoreo Global

**Cada 5 minutos consultar:**

```bash
# Últimos documentos
curl http://localhost:25500/api/v1/docs?limit=30

# Canal de comunicación
curl http://localhost:25500/api/v1/docs | grep "comunicacion"

# Órdenes pendientes
curl http://localhost:25500/api/v1/worker/worker-core/pendientes
curl http://localhost:25500/api/v1/worker/worker-infra/pendientes
curl http://localhost:25500/api/v1/worker/worker-nlp/pendientes
curl http://localhost:25500/api/v1/worker/worker-ui/pendientes

# Métricas
curl http://localhost:25501/api/metrics
```

**Analizar:**
- ¿Cuántos workers activos? (objetivo: 2-3)
- ¿Reportes pendientes de publicar?
- ¿Dependencias bloqueando progreso?
- ¿Conflictos de archivos?

### 2. Decisiones Arquitectónicas

**Matriz de Prioridad:**

| Worker | Prioridad | Justificación |
|--------|-----------|---------------|
| Core   | CRÍTICA   | Base de todo, sin Core no hay nada |
| Infra  | CRÍTICA   | Valida Core con tests |
| UI     | MEDIA     | Mejora UX pero no bloquea |
| NLP    | BAJA      | Futuro, espera Core Fase 2 |

**Trabajo Paralelo Permitido:**

✅ Core + Infra → Archivos diferentes, validación mutua
✅ Core + UI básico → UI puede preparar estructura
❌ NLP + cualquiera → NLP bloqueado hasta Core Fase 2
❌ 2 workers en mismo archivo → Serializar

### 3. Resolución de Dependencias

**Dependencias Críticas (Roadmap Fase A):**

```
A.1 Core Fase 1 → INDEPENDIENTE (puede arrancar)
A.1 Core Fase 2 → Depende Fase 1 ✓
A.1 Core Fase 3-5 → Secuencial

A.2 Infra Bloque 1-2 → PARALELO con Core ✓
A.2 Infra Bloque 4 → Depende Bloque 2

A.3 NLP Fase 1 → Investigación independiente
A.3 NLP Fase 2-4 → BLOQUEADO hasta Core Fase 2 ✓

A.4 UI todas → BLOQUEADO hasta Core tener API ✓
```

**Tu trabajo:**
- Hacer cumplir estas dependencias
- Desbloquear cuando se cumpla prerequisito
- Dar trabajo alternativo si bloqueado

### 4. Coordinación de Reportes

**Si worker completó pero no publicó:**

```markdown
COORDINACION: Worker-Infra publicar reporte

Worker-Infra completó #18+#23 localmente pero reporte no está en docs-service.

ACCION REQUERIDA:
Publicar orchestra/reporte_worker_infra_sesion2.md como documento.

BLOQUEO ACTUAL:
Sin reporte publicado, sistema no puede generar siguiente fase.

PRIORIDAD: CRÍTICA
```

---

## Escenarios de Coordinación

### Escenario 1: Trabajo Paralelo Exitoso

```
T0: Core trabajando Fase 1, Infra trabajando tests
T5: Core completa Fase 1 → Publica progreso
T5: Infra completa tests → Publica progreso
T10: Arquitecto detecta ambos
T10: Arquitecto decide:
     - Core → Fase 2 (KDTree)
     - Infra → Docker + CI/CD
T15: Ambos arrancan nuevas tareas (paralelo)
```

### Escenario 2: Dependencia Bloqueada

```
T0: NLP quiere arrancar implementación
T5: NLP publica: "BLOQUEO: Necesito Core Fase 2"
T10: Arquitecto detecta bloqueo
T10: Arquitecto verifica: Core aún en Fase 1
T10: Arquitecto responde:
     "COORDINACION: NLP diseñar arquitectura mientras espera"
T15: NLP continúa trabajo teórico sin bloquearse
```

### Escenario 3: Conflicto de Archivos

```
T0: Core y Infra quieren modificar nucleo.py
T5: Ambos publican progreso
T10: Arquitecto detecta conflicto potencial
T10: Arquitecto decide:
     - Core modifica nucleo.py (prioridad)
     - Infra trabaja en tests/benchmarks (paralelo OK)
T15: No hay conflicto git
```

---

## Métricas de Éxito del Arquitecto

### Throughput

**Objetivo:** 5-10 tareas/día
**Medición:** Documentos completados en 24h
**Responsabilidad:** Maximizar asignando trabajo paralelo

### Autonomía

**Objetivo:** >80% sin escalado a Lucas
**Medición:** (decisiones_autonomas / decisiones_totales) × 100
**Responsabilidad:** Resolver dudas técnicas sin escalar

### Coordinación

**Objetivo:** 0 conflictos de archivos
**Medición:** Conflictos git en último commit
**Responsabilidad:** Prevenir mediante asignación inteligente

### Tiempo de Respuesta

**Objetivo:** <10min para bloqueos
**Medición:** Tiempo entre "BLOQUEO" y "COORDINACION"
**Responsabilidad:** Revisar cada 5min máximo

---

## Comandos Útiles para el Arquitecto

### Estado Global

```bash
# Ver todo
curl -s http://localhost:25500/api/v1/docs?limit=30 | python -m json.tool

# Solo comunicación
curl -s http://localhost:25500/api/v1/docs | grep -A 10 "comunicacion"

# Métricas sistema
curl -s http://localhost:25501/api/metrics | python -m json.tool

# Dashboard
start http://localhost:25501
```

### Publicar Coordinación

```bash
# Plantilla básica
curl -X POST http://localhost:25500/api/v1/docs \
  -H "Content-Type: application/json" \
  -d @coordinacion.json
```

### Verificar Workers

```bash
# Pendientes por worker
for worker in worker-core worker-infra worker-nlp worker-ui; do
  echo "=== $worker ==="
  curl -s http://localhost:25500/api/v1/worker/$worker/pendientes | python -m json.tool
done
```

---

## Inicio de Sesión del Arquitecto

**Al arrancar por primera vez:**

1. Leer contexto completo:
   ```bash
   cat E:\ianae-final\orchestra\ROADMAP_FASE_A.md
   cat E:\ianae-final\orchestra\ESTADO_PROYECTO_COMPLETO.md
   ```

2. Ver estado actual:
   ```bash
   curl http://localhost:25500/api/v1/docs?limit=30
   ```

3. Identificar estado de cada worker:
   - Core: ¿En qué fase?
   - Infra: ¿Tests listos?
   - NLP: ¿Bloqueado o trabajando?
   - UI: ¿Esperando API?

4. Publicar primera coordinación:
   ```
   COORDINACION: Estado inicial del sistema

   [Resumen de qué tiene cada worker pendiente]
   [Decisión de qué hacer primero]
   [Prioridades claras]
   ```

5. Arrancar ciclo de 5 minutos

---

## Detener el Sistema

**Para pausar todo:**

1. Cierra las ventanas de los 4 watchdogs
2. Cierra ventana del daemon
3. Los servicios (docs-service, dashboard) pueden seguir activos
4. Las sesiones Claude Code pueden seguir abiertas

**Para reanudar:**

```cmd
E:\ianae-final\orchestra\INICIAR_TODO.bat
```

Todo se recupera automáticamente. El arquitecto retoma donde lo dejó.

---

## Troubleshooting

### Problema: Arquitecto no ve mensajes de workers

**Síntoma:** Workers publican pero arquitecto no detecta

**Solución:**
```bash
# Verificar que tag "comunicacion" está presente
curl http://localhost:25500/api/v1/docs | grep "comunicacion"

# Si falta, workers deben usar tag correcto
```

### Problema: Workers no ven coordinación del arquitecto

**Síntoma:** Arquitecto publica pero workers no actúan

**Solución:**
- Workers deben consultar docs cada 2-3 min
- Watchdogs muestran TODAS las órdenes (incluye coordinación)
- Verificar que tags incluyen worker correspondiente

### Problema: Conflictos de archivos

**Síntoma:** 2 workers modifican mismo archivo

**Solución:**
- Arquitecto debe prevenir con mejor asignación
- Si ocurre, serializar: un worker espera al otro
- Core siempre tiene prioridad en nucleo.py

---

## Resumen

**El Arquitecto Maestro es el cerebro del sistema.**

✅ Coordina 4 workers
✅ Decide prioridades
✅ Resuelve dependencias
✅ Optimiza trabajo paralelo
✅ Responde bloqueos en <10min
✅ Mantiene >80% autonomía

**Tu misión como arquitecto: Hacer que el equipo trabaje como una orquesta sincronizada. 🎵**

---

**Sistema IANAE-Orchestra v2.0 con Arquitecto Maestro listo para producción. 🚀**
