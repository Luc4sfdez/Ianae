# Roadmap Completo - Fase A: Desarrollo IANAE Autónomo

**Versión:** 1.0
**Fecha:** 2026-02-10
**Estado:** COMPLETADA
**Tiempo Estimado Total:** 15-20 horas de trabajo worker

---

## Objetivo de Fase A

**Workers desarrollan IANAE sin intervención constante de Lucas.**

Sistema completo de:
- ✅ Núcleo optimizado (numpy, 3-10x más rápido)
- ✅ Tests completos (cobertura >80%)
- ✅ Infraestructura profesional (Docker, CI/CD)
- ✅ Dashboard avanzado (visualización red)
- ✅ Integración NLP (texto → conceptos)

---

## Mapa General de Fase A

```
┌─────────────────────────────────────────────────────────────┐
│                       FASE A                                │
│             Desarrollo IANAE Autónomo                       │
├────────────┬────────────┬────────────┬─────────────────────┤
│   A.1      │    A.2     │    A.3     │        A.4          │
│ Numpy Opt  │   Infra    │    NLP     │    Dashboard        │
│ (core)     │  (infra)   │   (nlp)    │      (ui)           │
│            │            │            │                      │
│ 6-8h       │   6-8h     │   8-12h    │      4-5h           │
│ CRÍTICO    │  CRÍTICO   │  FUTURO    │     MEJORA          │
└────────────┴────────────┴────────────┴─────────────────────┘

Trabajo en Paralelo:
- A.1 (core) + A.2 (infra) → Simultáneo ✓
- A.3 (nlp) → Después de A.1 Fase 2
- A.4 (ui) → Después de A.1 completo
```

---

## A.1: Optimizaciones Numpy (Worker-Core)

### Estado Actual
- ✅ Documento #5 publicado (plan Fase 1)
- ⏸️ Esperando worker-core arranque

### Plan Completo (5 Fases)

#### Fase 1: Operaciones Vectoriales Básicas (2h)
**Documento:** #5

**Tareas:**
1. Reemplazar loops por operaciones numpy vectorizadas
2. Usar broadcasting donde sea posible
3. Implementar cálculos batch para múltiples conceptos
4. Crear benchmarks antes/después

**Criterio:** Mejora ≥30% en operaciones críticas

#### Fase 2: Índice Espacial (1.5h)
**A publicar después de Fase 1**

**Tareas:**
1. Implementar scipy.spatial.KDTree
2. Optimizar búsquedas de vecinos cercanos
3. Integrar con sistema de propagación
4. Benchmarks de búsqueda

**Criterio:** Búsqueda de similares 10x más rápida

#### Fase 3: Propagación Vectorizada (2h)
**A publicar después de Fase 2**

**Tareas:**
1. Convertir propagación iterativa a matricial
2. Usar sparse matrices si necesario
3. Implementar propagación batch
4. Validar con tests existentes

**Criterio:** Propagación 5x más rápida

#### Fase 4: Auto-Modificación Optimizada (1.5h)
**A publicar después de Fase 3**

**Tareas:**
1. Vectorizar fortalecimiento de conexiones
2. Optimizar debilitamiento batch
3. Creación eficiente de nuevas conexiones
4. Tests de auto-modificación

**Criterio:** Modificación 3x más rápida

#### Fase 5: Integración y Validación (1h)
**A publicar después de Fase 4**

**Tareas:**
1. Integrar todas las optimizaciones
2. Suite completa de benchmarks
3. Validar sin breaking changes
4. Documentar mejoras

**Criterio:**
- Mejora global ≥3x vs original
- Todos los tests pasan
- API pública sin cambios

### Órdenes a Publicar

**Ya publicadas:**
- #5: Fase 1 (operaciones vectoriales)

**Pendientes (publicar cuando worker complete fase anterior):**
- Fase 2: Índice espacial
- Fase 3: Propagación vectorizada
- Fase 4: Auto-modificación
- Fase 5: Integración final

---

## A.2: Infraestructura Profesional (Worker-Infra)

### Estado Actual
- ✅ Orden #18 publicada (tests nucleo.py)
- ✅ Orden #23 publicada (Docker + CI/CD)
- ⏸️ Esperando worker-infra arranque

### Plan Completo (4 Bloques)

#### Bloque 1: Suite de Tests (worker-infra)
**Documento:** #18

**Tareas:**
1. Tests unitarios propagación (test_nucleo_propagacion.py)
2. Tests auto-modificación (test_nucleo_modificacion.py)
3. Tests serialización (test_nucleo_serializacion.py)
4. Benchmarks (benchmark_nucleo.py)

**Estructura:**
```
tests/
├── unit/
│   ├── test_nucleo_propagacion.py
│   ├── test_nucleo_modificacion.py
│   ├── test_nucleo_serializacion.py
│   └── test_emergente.py
├── integration/
│   └── test_full_system.py
├── benchmarks/
│   └── benchmark_nucleo.py
└── fixtures/
    └── sample_networks.json
```

**Criterio:** >20 tests, cobertura >80%

#### Bloque 2: Docker + CI/CD (worker-infra)
**Documento:** #23

**Tareas:**
1. Dockerfile para IANAE
2. docker-compose.yml (IANAE + docs-service + dashboard)
3. pyproject.toml completo
4. Reorganizar src/core/ → src/ianae/
5. GitHub Actions workflow
6. README con instrucciones Docker

**Estructura:**
```
docker/
├── Dockerfile
├── docker-compose.yml
└── .dockerignore

.github/
└── workflows/
    └── tests.yml
```

**Criterio:**
- `docker-compose up` funciona
- Tests pasan en contenedor
- GitHub Actions ejecuta tests en cada push

#### Bloque 3: Estructura Python Estándar
**Incluido en #23**

**Tareas:**
1. pyproject.toml con dependencies
2. Reorganizar a src/ianae/
3. requirements.txt + requirements-dev.txt
4. Configuración pytest en pyproject.toml

**Criterio:** `pip install -e .` funciona

#### Bloque 4: Persistencia Mejorada (Futuro)
**A publicar después de Bloque 2**

**Tareas:**
1. Migrar snapshots JSON → SQLite
2. Versioning de snapshots
3. Backup automático
4. API de persistencia

**Criterio:** Snapshots persistidos eficientemente

### Trabajo en Paralelo

**worker-infra puede trabajar SIMULTÁNEAMENTE con worker-core:**
- Core optimiza nucleo.py
- Infra crea tests y Docker en paralelo
- Tests validan optimizaciones de core

---

## A.3: Integración NLP (Worker-NLP)

### Estado Actual
- ✅ Orden #19 publicada (investigación NLP)
- ⏸️ Esperando worker-nlp arranque
- ⏸️ Depende de worker-core Fase 2

### Plan Completo (4 Fases)

#### Fase 1: Investigación y Diseño
**Documento:** #19

**Tareas:**
1. Investigar bibliotecas (spaCy vs transformers)
2. Diseñar pipeline texto → red IANAE
3. Prototipo mínimo
4. Documentación arquitectura

**Criterio:** Plan técnico completo

#### Fase 2: Embeddings (A publicar después)
**Tiempo:** 3-4 horas

**Tareas:**
1. Integrar sentence-transformers
2. Crear servicio de embeddings
3. Cache de embeddings
4. Tests de embeddings

**Criterio:** Textos convertidos a vectores

#### Fase 3: Extracción de Conceptos (A publicar después)
**Tiempo:** 3-4 horas

**Tareas:**
1. Integrar spaCy
2. Extraer entidades y conceptos
3. Calcular relaciones entre conceptos
4. Tests de extracción

**Criterio:** Texto → lista de conceptos

#### Fase 4: Pipeline Completo (A publicar después)
**Tiempo:** 2-3 horas

**Tareas:**
1. Pipeline completo: texto → embeddings → conceptos → red IANAE
2. API REST para procesamiento
3. Integración con nucleo.py
4. Tests end-to-end

**Criterio:** Input texto → Output red de conceptos

### Dependencias

**Requiere:**
- worker-core completar Fase 2 (índice espacial)
- Núcleo estable con API de acceso

---

## A.4: Dashboard Avanzado (Worker-UI)

### Estado Actual
- ✅ Orden #24 publicada (dashboard avanzado)
- ⏸️ Esperando worker-ui
- ⏸️ Depende de worker-core tener API

### Plan Completo (4 Fases)

#### Fase 1: Visualización de Red (D3.js)
**Documento:** #24 (parte 1)

**Tareas:**
1. Integrar D3.js v7
2. Componente NetworkVisualization
3. Endpoint GET /api/ianae/network
4. Renderizado básico de red

**Criterio:** Red de conceptos visualizada

#### Fase 2: Interfaz de Ingesta
**Documento:** #24 (parte 2)

**Tareas:**
1. Formulario de input texto
2. Endpoint POST /api/ianae/process-text
3. Integración con NLP (si disponible)
4. Visualización de resultado

**Criterio:** Input texto crea conceptos visualmente

#### Fase 3: WebSocket Tiempo Real
**Documento:** #24 (parte 3)

**Tareas:**
1. WebSocket server en FastAPI
2. Cliente WebSocket en JS
3. Actualización automática de red
4. Sincronización de estado

**Criterio:** Visualización actualiza en tiempo real

#### Fase 4: Control Panel Experimentos
**Documento:** #24 (parte 4)

**Tareas:**
1. Panel de control HTML
2. API /api/ianae/experiment/{name}
3. 4 experimentos básicos
4. Guardar/cargar snapshots

**Criterio:** Panel ejecuta experimentos interactivamente

### Dependencias

**Requiere:**
- worker-core tener API de acceso a red
- Opcional: worker-nlp para procesamiento texto

---

## Cronograma Estimado

### Semana 1: Fundación (A.1 Fase 1-2 + A.2 Bloque 1)
```
Día 1-2: worker-core → Numpy básico (Fase 1)
         worker-infra → Tests básicos (Bloque 1)

Día 3-4: worker-core → Índice espacial (Fase 2)
         worker-infra → Docker + CI/CD (Bloque 2)

Día 5:   Validación e integración
```

### Semana 2: Optimización (A.1 Fase 3-4)
```
Día 1-2: worker-core → Propagación vectorizada (Fase 3)

Día 3-4: worker-core → Auto-modificación (Fase 4)

Día 5:   worker-core → Integración final (Fase 5)
         worker-infra → Validar con tests
```

### Semana 3: Expansión (A.3 + A.4)
```
Día 1-2: worker-nlp → Investigación NLP (Fase 1)
         worker-ui → Visualización D3.js (Fase 1)

Día 3-4: worker-nlp → Embeddings (Fase 2)
         worker-ui → Interfaz ingesta (Fase 2)

Día 5:   worker-nlp → Extracción conceptos (Fase 3)
         worker-ui → WebSocket (Fase 3)
```

### Semana 4: Integración Final
```
Día 1-2: worker-nlp → Pipeline completo (Fase 4)
         worker-ui → Control panel (Fase 4)

Día 3-4: Integración completa
         Tests end-to-end

Día 5:   Documentación y validación final
```

---

## Órdenes Publicadas vs Pendientes

### Publicadas ✅
1. #5: A.1 Fase 1 (numpy básico)
2. #18: A.2 Bloque 1 (tests)
3. #19: A.3 Fase 1 (investigación NLP)
4. #23: A.2 Bloque 2 (Docker)
5. #24: A.4 completo (dashboard)

### Pendientes (a publicar cuando worker complete previa)
- A.1 Fase 2: Índice espacial
- A.1 Fase 3: Propagación vectorizada
- A.1 Fase 4: Auto-modificación
- A.1 Fase 5: Integración final
- A.2 Bloque 4: Persistencia mejorada
- A.3 Fase 2: Embeddings
- A.3 Fase 3: Extracción conceptos
- A.3 Fase 4: Pipeline completo

---

## Métricas de Éxito - Fase A

### Rendimiento
- ✅ IANAE 3-10x más rápido vs original
- ✅ Propagación optimizada (matriz vs iterativa)
- ✅ Búsqueda de vecinos 10x más rápida

### Calidad
- ✅ Tests completos (cobertura >80%)
- ✅ Todos los tests pasan
- ✅ Sin breaking changes en API

### Infraestructura
- ✅ Dockerizado y CI/CD funcionando
- ✅ Tests ejecutan en cada push (GitHub Actions)
- ✅ pyproject.toml instalable con pip

### Funcionalidad
- ✅ Dashboard visualiza red de conceptos
- ✅ Input texto crea conceptos (NLP)
- ✅ WebSocket actualiza en tiempo real
- ✅ Panel de experimentos interactivo

---

## Dependencias Entre Sub-Fases

```
A.1 (core)
    └─ Fase 1 (vectores) → INDEPENDIENTE
        └─ Fase 2 (índice) → Depende de Fase 1
            └─ Fase 3 (propagación) → Depende de Fase 2
                └─ Fase 4 (modificación) → Depende de Fase 3
                    └─ Fase 5 (integración) → Depende de Fase 4

A.2 (infra)
    ├─ Bloque 1 (tests) → INDEPENDIENTE (paralelo con A.1)
    ├─ Bloque 2 (Docker) → INDEPENDIENTE (paralelo con A.1)
    ├─ Bloque 3 (estructura) → Incluido en Bloque 2
    └─ Bloque 4 (persistencia) → Depende de Bloque 2

A.3 (nlp)
    ├─ Fase 1 (investigación) → INDEPENDIENTE
    └─ Fase 2-4 → Depende de A.1 Fase 2 (índice espacial)

A.4 (ui)
    ├─ Fase 1-2 → Depende de A.1 tener API
    └─ Fase 3-4 → Opcional: mejor con A.3
```

---

## Comandos Útiles

### Ver órdenes pendientes por worker
```bash
curl http://localhost:25500/api/v1/worker/worker-core/pendientes
curl http://localhost:25500/api/v1/worker/worker-infra/pendientes
curl http://localhost:25500/api/v1/worker/worker-nlp/pendientes
curl http://localhost:25500/api/v1/worker/worker-ui/pendientes
```

### Verificar progreso
```bash
# Dashboard
start http://localhost:25501

# Métricas
curl http://localhost:25501/api/metrics | jq '.quality'

# Documentos completados
curl http://localhost:25500/api/v1/docs | jq '.docs[] | select(.workflow_status=="completed")'
```

### Ejecutar tests
```bash
# Todos
pytest tests/

# Unitarios
pytest tests/unit/

# Benchmarks
pytest tests/benchmarks/ -v

# Con cobertura
pytest tests/ --cov=src/core --cov-report=html
```

---

## Estado Actual

**Fases Completadas:**
- ✅ Fase B (Herramientas): 100%
- ✅ Fase C (Equipo): 100%
- ✅ Fase A (Producto): 100% — Completada 2026-02-12

**Resumen Final:**
- 289 tests pasando (0 fallos)
- Core: propagacion matricial, indice espacial, memoria asociativa, aprendizaje por refuerzo, integracion simbolica
- Infra: Docker multi-stage, CI/CD GitHub Actions, pyproject.toml v0.5
- NLP: extractor conceptos, pipeline con reduccion dimensional, cache embeddings
- Dashboard: D3.js force graph, WebSocket, 4 tabs, experimentos, snapshots

---

**Fase A completada. Sistema IANAE funcional y testeado.**
