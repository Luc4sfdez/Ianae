# Plan de Ejecución: B → C → A

**Orden estratégico aprobado por Lucas:**
1. **B:** Refinar sistema orchestra (herramientas de coordinación)
2. **C:** Escalar a más workers (equipo multi-agente)
3. **A:** Desarrollo IANAE autónomo (producto)

---

## FASE B: REFINAR SISTEMA ORCHESTRA (Prioridad 1)

### Objetivo
Mejorar visibilidad, control y métricas del sistema multi-agente antes de escalar.

### B.1 - Dashboard Web (Worker-UI)

**Asignado a:** worker-ui
**Dependencias:** docs-service funcionando ✅
**Tiempo estimado:** 4-6 horas

**Funcionalidades:**

1. **Vista Principal - Estado del Sistema**
   ```
   ┌─────────────────────────────────────────┐
   │  CLAUDE-ORCHESTRA - IANAE               │
   ├─────────────────────────────────────────┤
   │  Servicios:                             │
   │  ● docs-service (25500)  ✅ Online      │
   │  ● daemon           ✅ Online (2min)    │
   │                                         │
   │  API Anthropic: 3/100 llamadas hoy     │
   │  Costo estimado: $0.06                  │
   └─────────────────────────────────────────┘
   ```

2. **Vista de Documentos**
   - Tabla con ID, Título, Autor, Estado, Prioridad, Tags
   - Filtros: por worker, por estado, por categoría
   - Búsqueda full-text (FTS5)
   - Click → ver contenido completo

3. **Vista por Worker**
   ```
   WORKER-CORE:
   ├─ Pendientes: 4
   ├─ Última actividad: hace 5 min
   ├─ Reportes publicados: 1
   └─ Estado: 🟢 Activo

   WORKER-NLP:
   ├─ Pendientes: 0
   ├─ Estado: 🔴 Inactivo (sin arrancar)

   WORKER-INFRA:
   ├─ Pendientes: 0
   ├─ Estado: 🔴 Inactivo

   WORKER-UI:
   ├─ Pendientes: 1 (este dashboard)
   ├─ Estado: 🟡 Iniciando
   ```

4. **Vista de Actividad (Timeline)**
   ```
   15:54:55  [ORDEN] daemon → worker-core: Implementar optimizaciones numpy
   15:51:23  [REPORTE] worker-core: Análisis completado
   15:48:25  [ORDEN] lucas → worker-core: Analizar nucleo.py
   15:41:08  [RESPUESTA] daemon → worker-core: Sistema OK
   ```

5. **Métricas**
   - Gráfico de API calls por hora
   - Tiempo promedio de respuesta del daemon
   - Documentos por categoría (pie chart)
   - Workers activos vs inactivos

**Stack técnico:**
- Backend: FastAPI (reutilizar docs-service)
- Frontend: HTML + JavaScript vanilla (o Vue.js ligero)
- Estilo: Tailwind CSS o similar
- Real-time: polling cada 10s (o WebSocket)

**Archivos a crear:**
```
src/ui/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css
│   │   └── js/
│   │       └── dashboard.js
│   └── templates/
│       ├── index.html          # Dashboard principal
│       ├── documents.html      # Vista documentos
│       ├── workers.html        # Vista workers
│       └── activity.html       # Timeline
└── requirements.txt
```

**Criterio de hecho:**
- ✅ Dashboard accesible en http://localhost:25501
- ✅ Muestra estado en tiempo real de todos los workers
- ✅ Permite filtrar y buscar documentos
- ✅ Timeline de actividad funcional
- ✅ Responsive (funciona en móvil)

---

### B.2 - Sistema de Estados (Worker-Infra)

**Asignado a:** worker-infra
**Dependencias:** docs-service ✅
**Tiempo estimado:** 2-3 horas

**Problema actual:**
Los documentos se quedan en estado "pending" incluso después de ser procesados.

**Solución:**

1. **Añadir estados al schema de documentos**
   ```sql
   -- Añadir a database.py
   ALTER TABLE documents ADD COLUMN workflow_status TEXT DEFAULT 'pending';

   -- Estados posibles:
   -- 'pending'      -> Esperando ser procesado
   -- 'in_progress'  -> Worker trabajando en ello
   -- 'completed'    -> Tarea completada
   -- 'blocked'      -> Bloqueado esperando algo
   -- 'cancelled'    -> Cancelado
   ```

2. **Endpoint para actualizar estado**
   ```python
   # POST /api/v1/docs/{id}/status
   {
       "status": "in_progress",
       "worker": "worker-core",
       "progress": 0.5,  # opcional
       "message": "Analizando nucleo.py línea 300/752"  # opcional
   }
   ```

3. **Auto-actualización desde workers**
   ```python
   # En worker_report.py
   def marcar_como_completado(doc_id):
       requests.put(
           f"{DOCS_SERVICE_URL}/api/v1/docs/{doc_id}/status",
           json={"status": "completed"}
       )
   ```

4. **Workflow automático en daemon**
   ```python
   # Al asignar orden
   marcar_estado(doc_id, "in_progress")

   # Al recibir reporte
   marcar_estado(doc_id_original, "completed")
   ```

**Archivos a modificar:**
- `orchestra/docs-service/app/database.py` → añadir campo
- `orchestra/docs-service/app/main.py` → nuevo endpoint
- `orchestra/daemon/docs_client.py` → métodos de estado
- `orchestra/daemon/worker_report.py` → auto-marcar

**Criterio de hecho:**
- ✅ Campo workflow_status en database
- ✅ Endpoint de actualización funcional
- ✅ Workers actualizan estado automáticamente
- ✅ Dashboard muestra estados correctos

---

### B.3 - Métricas de Calidad (Worker-Infra)

**Asignado a:** worker-infra
**Dependencias:** B.2 ✅
**Tiempo estimado:** 2 horas

**Métricas a implementar:**

1. **Métricas del Daemon**
   ```python
   {
       "api_calls_today": 3,
       "api_calls_total": 150,
       "ordenes_publicadas": 2,
       "dudas_resueltas": 0,
       "escalados": 0,
       "uptime_seconds": 3600,
       "last_poll": "2026-02-10T15:54:55Z"
   }
   ```

2. **Métricas por Worker**
   ```python
   {
       "worker-core": {
           "ordenes_recibidas": 3,
           "reportes_publicados": 1,
           "dudas_publicadas": 0,
           "tiempo_promedio_tarea": 180,  # segundos
           "tareas_completadas": 1,
           "ultima_actividad": "2026-02-10T15:51:23Z"
       }
   }
   ```

3. **Métricas de Calidad**
   ```python
   {
       "ciclo_completo_promedio": 120,  # segundos desde orden hasta reporte
       "efectividad_daemon": 0.95,  # órdenes útiles / órdenes totales
       "autonomia_real": 0.85,  # tareas sin escalado / tareas totales
       "costo_por_tarea": 0.02  # USD promedio por tarea completada
   }
   ```

**Endpoint:**
```python
# GET /api/v1/metrics
# GET /api/v1/metrics/daemon
# GET /api/v1/metrics/worker/{name}
```

**Visualización en dashboard:**
- Gráfico de tiempo por tarea
- Tasa de autonomía (sin escalados)
- Costo acumulado vs presupuesto
- Throughput (tareas/hora)

**Criterio de hecho:**
- ✅ Endpoint de métricas funcional
- ✅ Métricas calculadas correctamente
- ✅ Dashboard muestra métricas clave
- ✅ Logs estructurados para análisis posterior

---

### B.4 - Gestión de Errores y Alertas (Worker-Infra)

**Asignado a:** worker-infra
**Tiempo estimado:** 2 horas

**Funcionalidades:**

1. **Detección de errores**
   - Worker sin actividad > 15 minutos
   - Daemon sin poll > 2 minutos
   - API Anthropic con errores > 3 consecutivos
   - Tarea bloqueada > 1 hora

2. **Alertas visuales en dashboard**
   ```
   ⚠️ ALERTAS:
   - worker-core: Sin actividad hace 18 min
   - daemon: API call fallida 2x
   ```

3. **Log estructurado**
   ```python
   # En vez de: print("Error: ...")
   # Usar:
   logger.error("api_call_failed", extra={
       "worker": "worker-core",
       "endpoint": "/api/v1/messages",
       "error": str(e),
       "retry_count": 2
   })
   ```

4. **Recuperación automática**
   - Retry con backoff exponencial
   - Fallback a modo degradado
   - Notificación a Lucas solo si crítico

**Criterio de hecho:**
- ✅ Sistema detecta anomalías automáticamente
- ✅ Dashboard muestra alertas activas
- ✅ Logs estructurados (JSON)
- ✅ Recovery automático implementado

---

## FASE C: ESCALAR A MÁS WORKERS (Prioridad 2)

### Objetivo
Tener 3 workers trabajando en paralelo coordinados por el daemon.

### C.1 - Arrancar Worker-Infra

**Responsable:** Lucas (manual)
**Tiempo:** 5 minutos

**Pasos:**
```bash
# Terminal 1: watchdog worker-infra
cd orchestra/daemon
python worker_watchdog.py worker-infra

# Terminal 2: Claude Code como worker-infra
cd E:\ianae-final
# Leer prompt: orchestra/daemon/prompts/worker_infra.md
```

**Primera orden sugerida:**
```
ORDEN: Crear suite de tests para nucleo.py
- Tests unitarios para propagación
- Tests de auto-modificación
- Tests de serialización
- Benchmarks de rendimiento
```

---

### C.2 - Arrancar Worker-UI

**Responsable:** Lucas (manual)
**Tiempo:** 5 minutos

**Pasos:**
```bash
# Terminal 3: watchdog worker-ui
cd orchestra/daemon
python worker_watchdog.py worker-ui

# Terminal 4: Claude Code como worker-ui
cd E:\ianae-final
# Leer prompt: orchestra/daemon/prompts/worker_ui.md
```

**Primera orden sugerida:**
```
ORDEN: Implementar dashboard web básico
- Vista de estado del sistema
- Lista de documentos
- Vista por worker
- Timeline de actividad
```

---

### C.3 - Coordinación Multi-Worker

**Implementado por:** daemon (ya existe)
**Verificar:** Dependencias en orchestra.yaml

**Escenario de prueba:**
1. worker-core implementa Fase 1 numpy
2. worker-infra crea tests en paralelo
3. worker-ui actualiza dashboard con progreso
4. daemon coordina: asegura que tests esperan a que core termine

**Dependencias definidas:**
```yaml
workers:
  - name: "worker-core"
    depends_on: []                    # Puede trabajar solo

  - name: "worker-infra"
    depends_on: []                    # Puede trabajar en paralelo

  - name: "worker-ui"
    depends_on: ["worker-infra"]      # Necesita API de infra
```

---

## FASE A: DESARROLLO IANAE AUTÓNOMO (Prioridad 3)

### Objetivo
Workers desarrollan IANAE sin intervención constante de Lucas.

### A.1 - Worker-Core: Implementar Optimizaciones Numpy

**Ya asignado** → Documento ID: 5
**Tiempo estimado:** 6-8 horas
**Fases:** 1 → 2 → 3 → 4 → 5 (según plan de 450+ líneas)

**Criterio de éxito:**
- ✅ Mejora de rendimiento ≥30% en benchmarks
- ✅ Todos los tests pasan
- ✅ Sin breaking changes en API pública

---

### A.2 - Worker-Infra: Infraestructura Profesional

**Tareas paralelas mientras core refactoriza:**

1. **Suite de tests completa**
   - test_nucleo_numpy.py
   - test_emergente.py
   - test_integration.py
   - benchmark_refactorizacion.py

2. **Estructura Python estándar**
   - pyproject.toml con dependencias
   - src/ianae/ estructura
   - tests/ con fixtures
   - Migraciones si hay cambios de schema

3. **Persistencia mejorada**
   - Migrar de JSON a SQLite (opcional)
   - Versioning de snapshots
   - Backup automático

4. **Docker + CI/CD**
   - Dockerfile para IANAE
   - docker-compose.yml (IANAE + docs-service + daemon)
   - GitHub Actions para tests en cada push

---

### A.3 - Worker-NLP: Integración NLP (Futuro)

**Depende de:** Worker-Core completar Fase 2
**Tiempo estimado:** 1-2 semanas

**Bloques:**
1. Embeddings (sentence-transformers)
2. Extracción de conceptos (spaCy)
3. Pipeline completo (texto → red IANAE)
4. Integración con API Anthropic

---

### A.4 - Worker-UI: Dashboard Completo

**Tareas adicionales después de B.1:**
1. Visualización de red (D3.js)
2. Interfaz de ingesta de texto
3. WebSocket para updates en tiempo real
4. Control panel para experimentos

---

## CRONOGRAMA ESTIMADO

```
Semana 1 - FASE B (Herramientas):
├─ Día 1-2: Dashboard web básico (worker-ui)
├─ Día 3: Sistema de estados (worker-infra)
├─ Día 4: Métricas (worker-infra)
└─ Día 5: Gestión de errores (worker-infra)

Semana 2 - FASE C (Equipo):
├─ Día 1: Arrancar worker-infra + worker-ui
├─ Día 2-3: Pruebas de coordinación multi-worker
└─ Día 4-5: Ajustes y optimizaciones

Semana 3-4 - FASE A (Producto):
├─ Week 3: Worker-core optimizaciones numpy (Fases 1-2)
│          Worker-infra tests + Docker en paralelo
├─ Week 4: Worker-core Fases 3-4
│          Worker-ui mejoras dashboard
└─ Verificación y benchmarks finales

Semana 5+ - FASE A continuada:
└─ Worker-NLP integración (cuando core estable)
```

---

## MÉTRICAS DE ÉXITO

### Fase B (Herramientas)
- ✅ Dashboard funcional y usado por Lucas
- ✅ Estados de documentos correctos
- ✅ Métricas visibles en tiempo real
- ✅ Cero errores sin detectar

### Fase C (Equipo)
- ✅ 3 workers trabajando simultáneamente
- ✅ Daemon coordina sin conflictos
- ✅ Throughput: 5-10 tareas/día
- ✅ Autonomía: ≥80% tareas sin escalado

### Fase A (Producto)
- ✅ IANAE 3-10x más rápido
- ✅ Escalable a 10,000+ conceptos
- ✅ Tests completos (cobertura >80%)
- ✅ Dockerizado y CI/CD funcionando

---

## INVERSIÓN ESTIMADA

### Tiempo Lucas
- **Fase B:** 2-4 horas (aprobar diseños, verificar dashboard)
- **Fase C:** 1-2 horas (arrancar workers, supervisar)
- **Fase A:** 2-4 horas/semana (revisar PRs, decidir trade-offs)
- **Total:** ~10-15 horas en 4-5 semanas vs ~160 horas si lo hace solo

### Costo API Anthropic
- **Fase B:** ~$2-5 (órdenes de setup)
- **Fase C:** ~$5-10 (coordinación multi-worker)
- **Fase A:** ~$15-30 (desarrollo continuo)
- **Total:** ~$25-50 en un mes (dentro de límite 100 calls/día)

---

## PRÓXIMO PASO INMEDIATO

**PUBLICAR ORDEN PARA WORKER-UI:**

```markdown
ORDEN: Implementar Dashboard Web - Orchestra Control Panel

## Contexto
Sistema orchestra necesita visibilidad para escalar. Crear dashboard web que muestre estado en tiempo real de docs-service, daemon, y workers.

## Tareas
1. FastAPI app en src/ui/app/main.py (puerto 25501)
2. Dashboard HTML + CSS + JS vanilla
3. Vista principal: estado servicios + métricas
4. Vista documentos: tabla filtrable + búsqueda
5. Vista workers: estado y pendientes por worker
6. Timeline de actividad (últimos 50 eventos)

## Stack
- Backend: FastAPI + uvicorn
- Frontend: HTML + Tailwind CSS + vanilla JS
- API: consumir docs-service (localhost:25500)
- Update: polling cada 10s

## Criterio de hecho
- Dashboard accesible en localhost:25501
- Muestra datos en tiempo real
- Responsive (funciona en móvil)
- Código limpio y documentado

## Referencia
Ver orchestra/PLAN_EJECUCION_BCA.md sección B.1
```

**¿Publico esta orden ahora para worker-ui?**
