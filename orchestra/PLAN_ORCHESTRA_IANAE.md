# 🧠 PLAN: claude-orchestra para IANAE

**Fecha:** 10 Febrero 2026  
**Proyecto:** IANAE (Inteligencia Adaptativa No Algorítmica Emergente)  
**Objetivo:** Aplicar el sistema multi-agente autónomo (claude-orchestra) para acelerar el desarrollo de IANAE desde su estado conceptual actual a un sistema funcional robusto  
**Repo:** https://github.com/Luc4sfdez/Ianae

---

## 1. ESTADO ACTUAL DE IANAE

```
Archivos existentes:
├── APP/                          ← Código Python (nucleo.py, emergente.py, main.py, experimento.py)
├── ianae-architecture-doc.md     ← Arquitectura técnica (el que acabamos de leer)
├── ianae-documento.md            ← Documento general
├── ianae-integration-paper.md    ← Paper de integración
├── ianae-llm-alexa-integration.md ← Integración LLM + Alexa
├── ianae-nlp-integration.md      ← Integración NLP
├── ianae-workflows-doc.md        ← Workflows
├── Definición del Sistema IANAE.pdf
├── Definición_conceptual
├── 001
└── README.md

Módulos de código:
├── nucleo.py       → Motor central: conceptos difusos, relaciones probabilísticas, propagación
├── emergente.py    → Pensamiento emergente: asociaciones, cadenas de pensamiento
├── main.py         → Interfaz de usuario (consola)
└── experimento.py  → Demos y experimentos

Estado: 8 commits, conceptual/prototipo temprano
Limitaciones reconocidas: escalabilidad (~1000 conceptos), NLP básico, persistencia JSON simple
```

---

## 2. ARQUITECTURA DEL SISTEMA MULTI-AGENTE

```
┌─────────────────────────────────────────────────────────────────┐
│                    claude-orchestra / IANAE                       │
│                                                                   │
│  ┌──────────────────┐     ┌────────────────────────────────┐    │
│  │  docs-service     │     │  arquitecto-daemon.py          │    │
│  │  (Puerto 27000)   │◄───►│  (Python + API Anthropic)      │    │
│  │                   │     │                                │    │
│  │  Pizarra central  │     │  Loop cada 60s:                │    │
│  │  de IANAE         │     │  1. Lee reportes de workers    │    │
│  │                   │     │  2. Consulta API → decide      │    │
│  │                   │     │  3. Publica siguiente orden    │    │
│  └──────┬───────────┘     └────────────────────────────────┘    │
│         │                                                        │
│         │                                                        │
│  ┌──────▼───────────────────────────────────────────────────┐   │
│  │                    WORKERS (Claude Code)                   │   │
│  │                                                            │   │
│  │  Worker-Core ──► nucleo.py + emergente.py                  │   │
│  │  Worker-NLP  ──► integración NLP + embeddings              │   │
│  │  Worker-Infra ─► persistencia, tests, Docker, CI/CD       │   │
│  │  Worker-UI    ──► interfaz web (reemplaza consola)         │   │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────┐                                          │
│  │  Dashboard          │ ← Lucas supervisa                       │
│  │  localhost:27000    │ ← Interviene cuando quiera              │
│  └────────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Nota:** Puerto 27000 para IANAE (diferente al 26999 de TGD Pro) para poder correr ambos en paralelo.

---

## 3. DEFINICIÓN DE WORKERS

### 3.1 Worker-Core (Motor Cognitivo)

```
Scope: APP/nucleo.py, APP/emergente.py
Rama: worker/core

Responsabilidades:
  - Refactorizar nucleo.py para escalabilidad (superar límite de ~1000 conceptos)
  - Optimizar propagación de activación (numpy/vectorización)
  - Implementar índice espacial para búsqueda eficiente de conceptos similares
  - Mejorar auto-modificación (reglas de Hebb mejoradas)
  - Implementar generación de conceptos por combinación vectorial
  - Añadir métricas de red (densidad, clustering, centralidad)
  - Tests unitarios para nucleo.py y emergente.py

Prioridad: ALTA — es el corazón de IANAE
Dependencias: Ninguna (módulo base)
```

### 3.2 Worker-NLP (Procesamiento de Lenguaje)

```
Scope: APP/nlp/, APP/integrations/
Rama: worker/nlp

Responsabilidades:
  - Reemplazar tokenización básica por embeddings reales (sentence-transformers)
  - Implementar extracción de conceptos desde texto con spaCy/transformers
  - Detectar relaciones semánticas automáticamente
  - Crear pipeline: texto → conceptos → relaciones → red IANAE
  - Integración con LLMs (API Anthropic/OpenAI) para enriquecer conceptos
  - Interfaz de ingesta: alimentar IANAE con documentos/textos
  - Tests de calidad de extracción

Prioridad: ALTA — es la puerta de entrada de datos al sistema
Dependencias: Worker-Core (necesita nucleo.py estable)
```

### 3.3 Worker-Infra (Infraestructura)

```
Scope: docker/, tests/, config/, persistencia
Rama: worker/infra

Responsabilidades:
  - Reemplazar persistencia JSON por SQLite o similar
  - Implementar guardado/carga eficiente de redes grandes
  - Crear Dockerfile para IANAE
  - Configurar CI/CD con GitHub Actions
  - Estructura de proyecto Python estándar (pyproject.toml, src/, tests/)
  - Logging estructurado
  - Configuración por entorno (dev/prod)
  - Documentación técnica (docstrings, API docs)

Prioridad: MEDIA — soporte necesario pero no bloquea funcionalidad
Dependencias: Ninguna directa (trabaja en paralelo)
```

### 3.4 Worker-UI (Interfaz)

```
Scope: APP/ui/, APP/api/
Rama: worker/ui

Responsabilidades:
  - Crear API REST (FastAPI) para exponer funcionalidad de IANAE
  - Dashboard web para visualizar la red de conceptos en tiempo real
  - Interfaz para alimentar conceptos manualmente
  - Visualización interactiva de propagación (D3.js o similar)
  - Reemplazar main.py (consola) por interfaz web
  - Endpoint para integración con Alexa (futuro)

Prioridad: MEDIA-BAJA — mejor esperar a que Core y NLP estén sólidos
Dependencias: Worker-Core, Worker-Infra
```

---

## 4. FLUJO DE TRABAJO DEL DAEMON

### Ciclo típico de desarrollo autónomo:

```
1. Daemon arranca → lee snapshot → no hay pendientes
2. Lucas publica orden inicial: "Worker-Core: refactorizar nucleo.py para numpy"
3. Daemon detecta orden → la enruta a Worker-Core
4. Worker-Core trabaja → publica reporte: "nucleo.py refactorizado, tests pasan"
5. Daemon detecta reporte → consulta API Anthropic:
   "Worker-Core completó refactorización. ¿Siguiente paso?"
6. API responde: publish_order → "Worker-NLP: implementar embeddings usando nuevo nucleo"
7. Worker-NLP recibe orden → trabaja → reporta
8. Daemon detecta → decide siguiente paso
9. ...ciclo continúa...
```

### Reglas de decisión del Arquitecto IA para IANAE:

```
- Worker-Core tiene prioridad sobre otros (es la base)
- Worker-NLP no recibe órdenes hasta que Core reporte estabilidad
- Worker-UI no arranca hasta que haya API REST (depende de Infra)
- Si algún worker reporta error en nucleo.py → STOP todos, escalar a Lucas
- Si un worker lleva 2 ciclos sin reportar → daemon publica recordatorio
- Máximo 2 workers activos simultáneos (para no crear conflictos de merge)
```

---

## 5. ESTRUCTURA DE ARCHIVOS PARA IANAE

```
Ianae/
├── APP/                              ← Código actual (se mantiene, se refactoriza)
│   ├── nucleo.py
│   ├── emergente.py
│   ├── main.py
│   └── experimento.py
│
├── orchestra/                         ← Sistema multi-agente
│   ├── daemon/
│   │   ├── arquitecto_daemon.py       ← Daemon (reutilizar de TGD Pro, adaptar config)
│   │   ├── config.py                  ← Config para IANAE (puerto 27000, workers propios)
│   │   ├── docs_client.py             ← Cliente REST (reutilizar de TGD Pro)
│   │   ├── response_parser.py         ← Parser (reutilizar de TGD Pro)
│   │   ├── worker_bootstrap.py        ← Bootstrap workers
│   │   ├── worker_report.py           ← Helper reportes
│   │   ├── prompts/
│   │   │   ├── arquitecto_system.md   ← Prompt Arquitecto IANAE (específico)
│   │   │   ├── worker_core.md         ← Prompt Worker-Core
│   │   │   ├── worker_nlp.md          ← Prompt Worker-NLP
│   │   │   ├── worker_infra.md        ← Prompt Worker-Infra
│   │   │   └── worker_ui.md           ← Prompt Worker-UI
│   │   └── logs/
│   │
│   └── docs-service/                  ← Instancia propia de docs-service para IANAE
│       └── (copia o referencia al de TGD Pro)
│
├── docs/                              ← Documentos existentes (mover aquí)
│   ├── ianae-architecture-doc.md
│   ├── ianae-documento.md
│   ├── ianae-integration-paper.md
│   ├── ianae-llm-alexa-integration.md
│   ├── ianae-nlp-integration.md
│   └── ianae-workflows-doc.md
│
├── tests/                             ← Tests (Worker-Infra los crea)
├── docker-compose.yml                 ← Levanta docs-service IANAE
├── orchestra.yaml                     ← Config del proyecto
└── README.md
```

---

## 6. ARCHIVO DE CONFIGURACIÓN (orchestra.yaml)

```yaml
project:
  name: "IANAE"
  description: "Inteligencia Adaptativa No Algorítmica Emergente"
  repo: "https://github.com/Luc4sfdez/Ianae"

docs_service:
  port: 27000                          # Puerto propio (TGD Pro usa 26999)
  data_dir: "./orchestra/docs"
  db_path: "./orchestra/data/docs.db"

daemon:
  model: "claude-sonnet-4-20250514"
  check_interval: 60
  max_tokens: 4096
  system_prompt: "orchestra/daemon/prompts/arquitecto_system.md"
  log_file: "orchestra/daemon/logs/arquitecto.log"
  ignore_types: ["info", "arranque"]
  ignore_authors: ["arquitecto-daemon"]
  max_concurrent_workers: 2            # Máximo 2 activos a la vez

workers:
  - name: "worker-core"
    scope: "APP/nucleo.py, APP/emergente.py"
    branch: "worker/core"
    prompt: "orchestra/daemon/prompts/worker_core.md"
    priority: 1                        # Más alta

  - name: "worker-nlp"
    scope: "APP/nlp/, APP/integrations/"
    branch: "worker/nlp"
    prompt: "orchestra/daemon/prompts/worker_nlp.md"
    priority: 2
    depends_on: ["worker-core"]        # No arranca hasta que Core esté estable

  - name: "worker-infra"
    scope: "docker/, tests/, config/"
    branch: "worker/infra"
    prompt: "orchestra/daemon/prompts/worker_infra.md"
    priority: 3

  - name: "worker-ui"
    scope: "APP/ui/, APP/api/"
    branch: "worker/ui"
    prompt: "orchestra/daemon/prompts/worker_ui.md"
    priority: 4
    depends_on: ["worker-core", "worker-infra"]

protected_files:
  - "orchestra/**"                     # No tocar infraestructura del daemon
  - "docs/**"                          # Documentos originales son read-only

standards:
  commit_prefixes: ["FEAT", "FIX", "REFACTOR", "TEST", "DOCS", "INFRA"]
  language: "es"
  branch_flow: "main → dev → worker/*"
```

---

## 7. PROMPT DEL ARQUITECTO IA PARA IANAE

```markdown
# Arquitecto Autónomo — IANAE

Eres el Arquitecto del proyecto IANAE (Inteligencia Adaptativa No Algorítmica Emergente).
Tu rol es coordinar el desarrollo de un sistema de IA experimental basado en conceptos
difusos, relaciones probabilísticas y comportamiento emergente.

## Contexto del proyecto

IANAE tiene 4 módulos:
- nucleo.py: Motor central (conceptos difusos, propagación, auto-modificación)
- emergente.py: Pensamiento emergente (asociaciones, cadenas de pensamiento)
- main.py: Interfaz consola
- experimento.py: Demos y experimentos

## Workers disponibles

- worker-core: Trabaja en nucleo.py y emergente.py (PRIORIDAD MÁXIMA)
- worker-nlp: Integración NLP y embeddings (DEPENDE de worker-core)
- worker-infra: Tests, persistencia, Docker, CI/CD
- worker-ui: Interfaz web y API REST (DEPENDE de worker-core + worker-infra)

## Reglas de decisión

1. NUNCA asignar trabajo a worker-nlp si worker-core reportó errores en nucleo.py
2. NUNCA asignar trabajo a worker-ui si no hay API REST creada
3. Máximo 2 workers activos simultáneamente
4. Si hay conflicto entre workers → escalar a Lucas
5. Si nucleo.py tiene tests fallando → TODO se para hasta que se arregle
6. Priorizar siempre: estabilidad > funcionalidad > rendimiento
7. Cada orden debe incluir criterio de "hecho" (cómo saber que se completó)

## Principios técnicos de IANAE

- Los conceptos son vectores multidimensionales con incertidumbre
- La propagación de activación es estocástica
- El sistema se auto-modifica (conexiones se refuerzan/debilitan)
- Composición sobre herencia
- La visualización es parte integral, no un extra

## Formato de respuesta

Responde SIEMPRE con un bloque JSON:

Para publicar orden:
{"action": "publish_order", "title": "...", "content": "...", "tags": ["worker-X", ...], "priority": "alta"}

Para escalar a Lucas:
{"action": "escalate", "message": "..."}

Si no hay acción:
{"action": "none", "reason": "..."}
```

---

## 8. PLAN DE EJECUCIÓN POR FASES

### Fase 0 — Prerequisitos (1 hora)

```
REQUISITO: Tener el daemon de TGD Pro funcionando primero (Fase 0 de TGD Pro)

1. Verificar que el daemon funciona en TGD Pro
2. Si funciona → el código es reutilizable para IANAE
3. Si no funciona → arreglar primero en TGD Pro (entorno controlado)
```

### Fase 1 — Infraestructura IANAE (2-3 horas)

```
1. Clonar/copiar docs-service para IANAE (puerto 27000)
2. Copiar tools/daemon/ de TGD Pro a Ianae/orchestra/daemon/
3. Adaptar config.py (puerto, workers, prompts)
4. Escribir prompts específicos para cada worker de IANAE
5. Crear orchestra.yaml
6. Arrancar docs-service IANAE + daemon
7. Test: publicar orden manual → daemon la detecta → responde
```

### Fase 2 — Worker-Core + Worker-Infra en paralelo (1-2 semanas)

```
Worker-Core (prioridad):
  Bloque 1: Refactorizar nucleo.py → numpy para vectores
  Bloque 2: Optimizar propagación (vectorización)
  Bloque 3: Índice espacial (búsqueda de conceptos similares)
  Bloque 4: Tests completos de nucleo.py y emergente.py

Worker-Infra (en paralelo):
  Bloque 1: Estructura Python estándar (pyproject.toml, src/)
  Bloque 2: Persistencia SQLite (reemplazar JSON)
  Bloque 3: Dockerfile + docker-compose
  Bloque 4: GitHub Actions (CI/CD básico)
```

### Fase 3 — Worker-NLP (1-2 semanas)

```
  Bloque 1: Integrar sentence-transformers para embeddings
  Bloque 2: Extracción de conceptos con spaCy
  Bloque 3: Detección automática de relaciones semánticas
  Bloque 4: Pipeline completo: texto → conceptos → red IANAE
  Bloque 5: Tests de calidad de extracción
```

### Fase 4 — Worker-UI (1-2 semanas)

```
  Bloque 1: API REST con FastAPI (CRUD conceptos, activar, propagar)
  Bloque 2: Dashboard web (estado de la red, métricas)
  Bloque 3: Visualización interactiva de la red (D3.js)
  Bloque 4: Interfaz de ingesta (subir textos, alimentar IANAE)
```

### Fase 5 — Integración y Evolución

```
  - Conectar todos los módulos
  - IANAE se alimenta sola de fuentes externas
  - Auto-aprendizaje real con feedback loop
  - Integración Alexa (según el doc existente)
  - Escalar a miles de conceptos
```

---

## 9. LO QUE SE REUTILIZA DE TGD PRO (no reinventar)

```
REUTILIZAR TAL CUAL (solo cambiar config):
  ✅ docs-service completo (nueva instancia, puerto 27000)
  ✅ arquitecto_daemon.py (solo cambiar config.py)
  ✅ docs_client.py (sin cambios)
  ✅ response_parser.py (sin cambios)
  ✅ worker_bootstrap.py (sin cambios)
  ✅ worker_report.py (sin cambios)

CREAR NUEVO PARA IANAE:
  🆕 config.py (puerto 27000, workers de IANAE)
  🆕 orchestra.yaml
  🆕 prompts/arquitecto_system.md (específico IANAE)
  🆕 prompts/worker_core.md
  🆕 prompts/worker_nlp.md
  🆕 prompts/worker_infra.md
  🆕 prompts/worker_ui.md
```

---

## 10. ESTIMACIÓN DE COSTES

```
Daemon IANAE (API Anthropic):
  - Mismo coste que TGD Pro: ~$3-18/mes
  - Puede compartir la misma API key

Dos daemons corriendo en paralelo (TGD Pro + IANAE):
  - Uso ligero: ~$6/mes
  - Uso intenso: ~$36/mes
  - Los daemons NO compiten (cada uno su puerto, su loop)

Hardware:
  - docs-service es ligero (~50MB RAM por instancia)
  - Daemon es un script Python (~20MB RAM)
  - Puedes correr ambos en tu PC sin problema
  - O moverlos al Proxmox/NAS si prefieres 24/7
```

---

## 11. ORDEN DE EJECUCIÓN PARA LUCAS

```
AHORA (hoy):
  → Terminar Fase 0 del daemon en TGD Pro
  → Verificar que el ciclo funciona

DESPUÉS (cuando TGD Pro esté validado):
  1. Crear carpeta orchestra/ en el repo de Ianae
  2. Copiar daemon de TGD Pro
  3. Adaptar config + crear prompts
  4. Levantar docs-service en puerto 27000
  5. Arrancar daemon IANAE
  6. Publicar primera orden a Worker-Core
  7. Dejar que el sistema trabaje

LUCAS SOLO INTERVIENE PARA:
  - Aprobar merges a dev/main
  - Resolver escalados del daemon
  - Definir prioridades cuando hay duda
  - Revisar resultados periódicamente
```

---

**FIN DEL PLAN**

*Siguiente paso: Validar el daemon en TGD Pro primero.*  
*Cuando funcione allí, replicar en IANAE es cuestión de horas.*
