# 🧠 IANAE — DESPLIEGUE COMPLETO CLAUDE-ORCHESTRA

**Fecha:** 10 Febrero 2026  
**Proyecto:** IANAE (Inteligencia Adaptativa No Algorítmica Emergente)  
**Puerto:** 25500  
**Objetivo:** Sistema multi-agente autónomo COMPLETO, sin intervención humana  
**Repo:** https://github.com/Luc4sfdez/Ianae

---

## ÍNDICE

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura)
3. [Roadmap por Fases](#3-roadmap)
4. [Estructura de Archivos](#4-estructura)
5. [Configuración General (orchestra.yaml)](#5-configuracion)
6. [docs-service para IANAE](#6-docs-service)
7. [Daemon Arquitecto](#7-daemon)
8. [Sistema de Watchdog por Worker](#8-watchdog)
9. [Prompts de Workers](#9-prompts-workers)
10. [Prompt del Arquitecto IA](#10-prompt-arquitecto)
11. [Scripts Completos](#11-scripts)
12. [Sesiones de Trabajo](#12-sesiones)
13. [Tests y Verificación](#13-tests)
14. [Despliegue Paso a Paso](#14-despliegue)
15. [Resolución de Problemas](#15-troubleshooting)

---

## 1. VISIÓN GENERAL

### Qué es esto

Un sistema donde un daemon Python (el Arquitecto) coordina múltiples instancias
de Claude Code (Workers) que desarrollan IANAE de forma autónoma. Los workers
ejecutan tareas, reportan al daemon, y el daemon decide el siguiente paso
llamando a la API de Anthropic. Lucas NO interviene salvo escalados críticos.

### Problema que resuelve

```
ANTES (manual):
  Lucas pide a Worker A → Worker A hace → Lucas revisa → Lucas pide a Worker B
  Cuello de botella: Lucas está en medio de todo

AHORA (autónomo):
  Daemon detecta reporte de Worker A → API decide → publica orden a Worker B
  Worker B la lee automáticamente (watchdog) → ejecuta → reporta
  Lucas solo ve el dashboard y aprueba merges
```

### Principio fundamental: ZERO preguntas a Lucas

```
REGLA DE ORO:
  Los workers NUNCA preguntan a Lucas.
  Si tienen duda → publican en docs-service con tag "duda"
  El daemon la detecta → la API la resuelve → publica respuesta
  El worker la lee via watchdog → sigue trabajando

  Lucas SOLO aparece cuando:
  - El daemon escala algo que la API no puede resolver
  - Hay que aprobar un merge a main
  - Lucas quiere intervenir voluntariamente
```

---

## 2. ARQUITECTURA

```
┌──────────────────────────────────────────────────────────────────────┐
│                    claude-orchestra / IANAE                           │
│                    Puerto: 25500                                     │
│                                                                      │
│  ┌───────────────────┐       ┌──────────────────────────────────┐   │
│  │  docs-service      │       │  arquitecto-daemon.py            │   │
│  │  Puerto 25500      │◄─────►│  (Python + API Anthropic)        │   │
│  │                    │       │                                  │   │
│  │  REST API          │       │  Loop cada 60s:                  │   │
│  │  SQLite + FTS5     │       │  1. Lee reportes/dudas nuevos    │   │
│  │  Web Dashboard     │       │  2. Llama API Anthropic          │   │
│  │  Inbox             │       │  3. Publica orden/respuesta      │   │
│  └──────┬────────────┘       └──────────────────────────────────┘   │
│         │                                                            │
│         │ HTTP (localhost)                                            │
│         │                                                            │
│  ┌──────▼────────────────────────────────────────────────────────┐  │
│  │                    WORKERS (Claude Code / VSCode)              │  │
│  │                                                                │  │
│  │  Cada worker tiene su propio WATCHDOG corriendo en background │  │
│  │  El watchdog consulta pendientes cada 30s                     │  │
│  │  Cuando hay orden nueva → la muestra en terminal              │  │
│  │  El worker la lee y ejecuta SIN intervención humana           │  │
│  │                                                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │  │
│  │  │ Worker-Core  │  │ Worker-NLP  │  │ Worker-Infra        │  │  │
│  │  │ + watchdog   │  │ + watchdog  │  │ + watchdog          │  │  │
│  │  │ nucleo.py    │  │ NLP/embeds  │  │ tests/docker/CI     │  │  │
│  │  │ emergente.py │  │ spaCy       │  │ persistencia        │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────┐                                              │  │
│  │  │ Worker-UI   │  (Fase posterior)                            │  │
│  │  │ + watchdog  │                                              │  │
│  │  │ FastAPI/Web │                                              │  │
│  │  └─────────────┘                                              │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────┐                                            │
│  │  Dashboard Web       │  ← Lucas mira cuando quiera               │
│  │  localhost:25500     │  ← Ve estado, reportes, órdenes            │
│  └─────────────────────┘                                            │
└──────────────────────────────────────────────────────────────────────┘
```

### Flujo de comunicación completo (bidireccional)

```
WORKER → DAEMON (ya funciona):
  Worker completa tarea
  → curl POST /api/v1/worker/{nombre}/reporte
  → Daemon detecta en siguiente poll (60s)
  → API decide
  → Daemon publica orden

DAEMON → WORKER (lo que faltaba — resuelto con watchdog):
  Daemon publica orden para worker-core
  → watchdog de worker-core detecta nueva orden (30s)
  → Muestra en terminal: "🔔 NUEVA ORDEN: ..."
  → Claude Code lee la orden del terminal
  → Ejecuta sin preguntar a Lucas

WORKER TIENE DUDA → DAEMON RESUELVE:
  Worker no sabe algo
  → curl POST reporte con tag "duda"
  → Daemon detecta (60s)
  → API analiza la duda
  → Publica respuesta como orden
  → Watchdog del worker la detecta
  → Worker lee y continúa
```

---

## 3. ROADMAP POR FASES

### Fase 0 — Prerequisitos (antes de empezar)

```
Duración: 0 (ya deberían estar)
Checklist:
  □ ANTHROPIC_API_KEY configurada como variable de entorno del sistema
  □ Python 3.10+ instalado
  □ pip install anthropic requests
  □ Git configurado
  □ VSCode con Claude Code instalado
  □ Repo Ianae clonado localmente
```

### Fase 1 — Infraestructura Orchestra (3-4 horas)

```
Objetivo: Tener docs-service + daemon + watchdogs funcionando

Sesión 1.1 — docs-service (1-2 horas):
  □ Copiar docs-service de TGD Pro (o instancia limpia)
  □ Configurar en puerto 25500
  □ Crear endpoints: notifications/since, context/snapshot
  □ Verificar: curl http://localhost:25500/health

Sesión 1.2 — Daemon + Config (1 hora):
  □ Crear carpeta orchestra/daemon/
  □ Crear config.py (puerto 25500, workers IANAE)
  □ Copiar docs_client.py, response_parser.py (adaptar campos)
  □ Crear arquitecto_daemon.py
  □ Crear prompts/arquitecto_system.md
  □ Verificar: python arquitecto_daemon.py (arranca sin error)

Sesión 1.3 — Watchdogs + Worker scripts (1 hora):
  □ Crear worker_watchdog.py
  □ Crear worker_bootstrap.py
  □ Crear worker_report.py
  □ Test ciclo completo: reporte manual → daemon detecta → publica orden → watchdog la muestra
```

### Fase 2 — Worker-Core (1-2 semanas)

```
El worker más importante. Trabaja en el corazón de IANAE.

Bloque 2.1: Análisis y refactorización base
  - Analizar nucleo.py actual línea por línea
  - Identificar cuellos de botella
  - Refactorizar a numpy para operaciones vectoriales
  - Tests unitarios básicos

Bloque 2.2: Escalabilidad
  - Superar límite de ~1000 conceptos
  - Índice espacial (FAISS o annoy) para búsqueda de similares
  - Optimizar propagación de activación (vectorizada)

Bloque 2.3: Auto-modificación mejorada
  - Reglas de Hebb mejoradas para refuerzo de conexiones
  - Decaimiento adaptativo (no lineal)
  - Generación de conceptos por combinación vectorial mejorada

Bloque 2.4: emergente.py mejorado
  - Cadenas de pensamiento más coherentes
  - Exploración de asociaciones con beam search
  - Métricas de calidad de pensamiento emergente

Bloque 2.5: Tests completos
  - Tests unitarios nucleo.py (cobertura >80%)
  - Tests unitarios emergente.py
  - Tests de regresión (asegurar que cambios no rompen nada)
  - Benchmarks de rendimiento
```

### Fase 3 — Worker-Infra (en paralelo con Fase 2, 1-2 semanas)

```
Bloque 3.1: Estructura del proyecto
  - Migrar a estructura Python estándar (src/ianae/, tests/)
  - Crear pyproject.toml
  - Configurar logging estructurado

Bloque 3.2: Persistencia
  - Reemplazar JSON por SQLite
  - Schema para conceptos, relaciones, activaciones
  - Guardado/carga eficiente de redes grandes
  - Migraciones de datos

Bloque 3.3: Docker
  - Dockerfile para IANAE
  - docker-compose.yml (IANAE + docs-service)
  - Volúmenes para persistencia

Bloque 3.4: CI/CD
  - GitHub Actions: tests en cada push
  - Linting (ruff/flake8)
  - Coverage report
```

### Fase 4 — Worker-NLP (1-2 semanas, después de Fase 2)

```
DEPENDE DE: Worker-Core completado (nucleo.py estable)

Bloque 4.1: Embeddings
  - Integrar sentence-transformers
  - Mapear embeddings a vectores de conceptos IANAE
  - Calibración de dimensionalidad

Bloque 4.2: Extracción de conceptos
  - Pipeline spaCy para extraer entidades/conceptos de texto
  - Detección de relaciones semánticas
  - Pesos de relaciones basados en co-ocurrencia

Bloque 4.3: Pipeline completo
  - texto → tokenización → embeddings → conceptos → relaciones → red IANAE
  - Ingesta de documentos (txt, md, pdf)
  - API de ingesta

Bloque 4.4: Integración LLM
  - Usar API Anthropic para enriquecer conceptos
  - Generar descripciones de relaciones
  - Validar coherencia de la red

Bloque 4.5: Tests
  - Tests de calidad de extracción
  - Tests de coherencia de relaciones
  - Benchmarks de ingesta
```

### Fase 5 — Worker-UI (1-2 semanas, después de Fases 2-3)

```
DEPENDE DE: Worker-Core + Worker-Infra completados

Bloque 5.1: API REST
  - FastAPI: CRUD conceptos, activar, propagar
  - Endpoints para métricas de red
  - WebSocket para actualizaciones en tiempo real

Bloque 5.2: Dashboard
  - Estado de la red (conceptos, relaciones, métricas)
  - Visualización de activación en tiempo real
  - Control panel (activar conceptos, ajustar temperatura)

Bloque 5.3: Visualización de red
  - D3.js / Vis.js para grafo interactivo
  - Color por activación, tamaño por importancia
  - Filtrado por categoría/cluster

Bloque 5.4: Interfaz de ingesta
  - Formulario para alimentar texto/documentos
  - Vista de conceptos extraídos antes de confirmar
  - Historial de ingestas
```

### Fase 6 — Integración y Autonomía (continua)

```
  - IANAE se alimenta sola de fuentes externas
  - Auto-aprendizaje con feedback loop
  - Integración con Alexa (según doc existente)
  - Escalar a decenas de miles de conceptos
  - Dashboard de evolución temporal
```

---

## 4. ESTRUCTURA DE ARCHIVOS COMPLETA

```
Ianae/
│
├── APP/                                  ← Código actual (se refactoriza)
│   ├── nucleo.py                         ← Motor central
│   ├── emergente.py                      ← Pensamiento emergente
│   ├── main.py                           ← Interfaz consola (se reemplaza en Fase 5)
│   └── experimento.py                    ← Demos
│
├── orchestra/                             ← Sistema multi-agente COMPLETO
│   │
│   ├── daemon/                            ← El cerebro autónomo
│   │   ├── arquitecto_daemon.py           ← Loop principal del daemon
│   │   ├── config.py                      ← Configuración IANAE
│   │   ├── docs_client.py                 ← Cliente REST para docs-service
│   │   ├── response_parser.py             ← Parser de respuestas JSON
│   │   ├── worker_watchdog.py             ← Watchdog que corre en cada worker
│   │   ├── worker_bootstrap.py            ← Bootstrap al arrancar worker
│   │   ├── worker_report.py               ← Helper para publicar reportes
│   │   ├── prompts/
│   │   │   ├── arquitecto_system.md       ← System prompt del Arquitecto IA
│   │   │   ├── worker_core.md             ← Prompt Worker-Core
│   │   │   ├── worker_nlp.md              ← Prompt Worker-NLP
│   │   │   ├── worker_infra.md            ← Prompt Worker-Infra
│   │   │   └── worker_ui.md               ← Prompt Worker-UI
│   │   └── logs/
│   │       └── (se crea automáticamente)
│   │
│   ├── docs-service/                      ← Instancia de docs-service para IANAE
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── database.py
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── docs.py
│   │   │   │       ├── workers.py
│   │   │   │       ├── notifications.py   ← NUEVO (poll de novedades)
│   │   │   │       └── snapshot.py        ← NUEVO (estado compacto)
│   │   │   ├── templates/
│   │   │   └── static/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── data/                              ← Datos persistentes
│   │   └── docs.db                        ← SQLite de docs-service
│   │
│   └── docs/                              ← Documentos del tablón
│       └── (se crean automáticamente)
│
├── docs/                                  ← Documentación del proyecto
│   ├── ianae-architecture-doc.md
│   ├── ianae-documento.md
│   ├── ianae-integration-paper.md
│   ├── ianae-llm-alexa-integration.md
│   ├── ianae-nlp-integration.md
│   └── ianae-workflows-doc.md
│
├── tests/                                 ← Tests (Worker-Infra)
│   ├── test_nucleo.py
│   ├── test_emergente.py
│   └── conftest.py
│
├── orchestra.yaml                         ← Config del proyecto
├── docker-compose.yml                     ← Levanta todo
├── requirements.txt                       ← Dependencias Python
├── .gitignore
└── README.md
```

---

## 5. CONFIGURACIÓN GENERAL (orchestra.yaml)

```yaml
# orchestra.yaml — Configuración IANAE

project:
  name: "IANAE"
  description: "Inteligencia Adaptativa No Algorítmica Emergente"
  repo: "https://github.com/Luc4sfdez/Ianae"

docs_service:
  port: 25500
  data_dir: "./orchestra/docs"
  db_path: "./orchestra/data/docs.db"

daemon:
  model: "claude-sonnet-4-20250514"
  check_interval: 60                     # Segundos entre polls
  max_tokens: 4096
  system_prompt: "orchestra/daemon/prompts/arquitecto_system.md"
  log_file: "orchestra/daemon/logs/arquitecto.log"

  # Filtros para no gastar API innecesariamente
  ignore_types: ["info", "arranque"]
  ignore_authors: ["arquitecto-daemon"]

  # Control de concurrencia
  max_concurrent_workers: 2              # Máximo 2 workers activos

  # Límite de coste diario (seguridad)
  max_daily_api_calls: 100               # Después de esto, solo notifica

watchdog:
  check_interval: 30                     # Cada 30 segundos
  show_full_content: true                # Mostrar contenido completo de la orden

workers:
  - name: "worker-core"
    scope: "APP/nucleo.py, APP/emergente.py"
    branch: "worker/core"
    prompt: "orchestra/daemon/prompts/worker_core.md"
    priority: 1
    depends_on: []

  - name: "worker-nlp"
    scope: "APP/nlp/, APP/integrations/"
    branch: "worker/nlp"
    prompt: "orchestra/daemon/prompts/worker_nlp.md"
    priority: 2
    depends_on: ["worker-core"]

  - name: "worker-infra"
    scope: "tests/, docker/, config/, pyproject.toml"
    branch: "worker/infra"
    prompt: "orchestra/daemon/prompts/worker_infra.md"
    priority: 3
    depends_on: []

  - name: "worker-ui"
    scope: "APP/ui/, APP/api/"
    branch: "worker/ui"
    prompt: "orchestra/daemon/prompts/worker_ui.md"
    priority: 4
    depends_on: ["worker-core", "worker-infra"]

protected_files:
  - "orchestra/**"
  - "docs/**"
  - ".gitignore"
  - "LICENSE"

standards:
  commit_prefixes: ["FEAT", "FIX", "REFACTOR", "TEST", "DOCS", "INFRA"]
  language: "es"
  branch_flow: "main → dev → worker/*"
```

---

## 6. DOCS-SERVICE PARA IANAE

### 6.1 Requisitos

docs-service es la pizarra central. Se reutiliza del de TGD Pro con estos cambios:

```
CAMBIOS respecto a TGD Pro:
  - Puerto: 25500 (en vez de 26999)
  - Base de datos: orchestra/data/docs.db (independiente)
  - Workers válidos: worker-core, worker-nlp, worker-infra, worker-ui
```

### 6.2 Endpoints requeridos

#### Endpoints que YA existen (reutilizar):

```
GET  /health                                → Estado del servicio
GET  /api/v1/docs                           → Listar documentos
POST /api/v1/docs                           → Crear documento
GET  /api/v1/docs/{id}                      → Documento por ID
PUT  /api/v1/docs/{id}                      → Actualizar documento
GET  /api/v1/search?q=...                   → Búsqueda FTS5
GET  /api/v1/worker/{name}/pendientes       → Pendientes de un worker
POST /api/v1/worker/{name}/reporte          → Worker publica reporte
```

#### Endpoints NUEVOS (crear):

```
GET /api/v1/notifications/since?t={iso_timestamp}
  → Documentos nuevos/modificados desde timestamp
  → Query: WHERE (created_at > ? OR updated_at > ?) AND deleted_at IS NULL
  → Response: {"results": [...], "since": t, "count": int}
  → CRÍTICO: sin esto el daemon no funciona

GET /api/v1/context/snapshot
  → Resumen compacto del estado actual
  → Response: {
      "ultimo_doc_por_categoria": {...},
      "pendientes_por_worker": {...},
      "total_docs": int,
      "workers_activos": [...],
      "alertas": [...]
    }
  → MUY ÚTIL: da contexto rico al Arquitecto IA
```

### 6.3 Archivo notifications.py

```python
"""
Endpoint de notificaciones para el daemon.
GET /api/v1/notifications/since?t={iso_timestamp}
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
# Importar función de conexión del docs-service existente
# from ..database import get_connection  # Ajustar según estructura real

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/since")
async def get_docs_since(t: str = Query(..., description="ISO timestamp")):
    """Documentos nuevos o modificados desde el timestamp dado."""
    try:
        # Validar formato
        since = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"Timestamp inválido: {t}")

    conn = get_connection()  # Ajustar según docs-service real
    try:
        cursor = conn.execute(
            """
            SELECT * FROM documents
            WHERE (created_at > ? OR updated_at > ?)
            AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            (t, t)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return {"results": results, "since": t, "count": len(results)}
    finally:
        conn.close()
```

### 6.4 Archivo snapshot.py

```python
"""
Endpoint de snapshot para el daemon.
GET /api/v1/context/snapshot
"""

from fastapi import APIRouter
# from ..database import get_connection

router = APIRouter(prefix="/api/v1/context", tags=["context"])

VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]


@router.get("/snapshot")
async def get_snapshot():
    """Estado compacto del proyecto para el Arquitecto IA."""
    conn = get_connection()
    try:
        # Último doc por categoría
        categories = {}
        for row in conn.execute(
            "SELECT category, title, author, created_at FROM documents "
            "WHERE deleted_at IS NULL "
            "GROUP BY category "
            "HAVING created_at = MAX(created_at)"
        ):
            r = dict(row)
            categories[r["category"]] = r

        # Pendientes por worker
        pendientes = {}
        for worker in VALID_WORKERS:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM documents "
                "WHERE status = 'pending' AND tags LIKE ? AND deleted_at IS NULL",
                (f"%{worker}%",)
            )
            pendientes[worker] = cursor.fetchone()["count"]

        # Total docs
        total = conn.execute(
            "SELECT COUNT(*) as count FROM documents WHERE deleted_at IS NULL"
        ).fetchone()["count"]

        # Docs de alta prioridad sin resolver
        alertas_cursor = conn.execute(
            "SELECT id, title, author, created_at FROM documents "
            "WHERE priority = 'alta' AND status != 'done' AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 10"
        )
        alertas = [dict(row) for row in alertas_cursor.fetchall()]

        return {
            "ultimo_doc_por_categoria": categories,
            "pendientes_por_worker": pendientes,
            "total_docs": total,
            "alertas": alertas,
            "workers_validos": VALID_WORKERS,
        }
    finally:
        conn.close()
```

---

## 7. DAEMON ARQUITECTO

### 7.1 config.py

```python
"""
Configuración del daemon Arquitecto para IANAE.
"""

import os

# docs-service IANAE
DOCS_SERVICE_URL = "http://localhost:25500"

# API Anthropic
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# Daemon
CHECK_INTERVAL = 60
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "arquitecto.log")
SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompts", "arquitecto_system.md")

# Filtros
IGNORE_TYPES = ["info", "arranque"]
IGNORE_AUTHORS = ["arquitecto-daemon"]

# Seguridad
MAX_DAILY_API_CALLS = 100

# Workers válidos
VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]

# Dependencias entre workers
WORKER_DEPENDENCIES = {
    "worker-core": [],
    "worker-nlp": ["worker-core"],
    "worker-infra": [],
    "worker-ui": ["worker-core", "worker-infra"],
}
```

### 7.2 docs_client.py

```python
"""
Cliente REST para docs-service de IANAE.
Adaptado a los campos REALES de la API (inglés).
"""

import requests
import logging

logger = logging.getLogger("arquitecto.docs_client")


class DocsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.timeout = 10

    def health_check(self):
        try:
            r = requests.get(f"{self.base_url}/health", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"docs-service no responde: {e}")
            return None

    def get_snapshot(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/context/snapshot", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error obteniendo snapshot: {e}")
            return None

    def get_new_docs(self, since):
        try:
            r = requests.get(
                f"{self.base_url}/api/v1/notifications/since",
                params={"t": since},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Error obteniendo docs nuevos: {e}")
            return []

    def get_worker_pendientes(self, worker_name):
        try:
            r = requests.get(
                f"{self.base_url}/api/v1/worker/{worker_name}/pendientes",
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("pendientes", [])
        except Exception as e:
            logger.error(f"Error pendientes {worker_name}: {e}")
            return []

    def get_doc(self, doc_id):
        try:
            r = requests.get(f"{self.base_url}/api/v1/docs/{doc_id}", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error doc {doc_id}: {e}")
            return None

    def publish_order(self, title, content, tags=None, priority="alta"):
        """Publicar una orden del Arquitecto."""
        payload = {
            "title": title,
            "content": content,
            "category": "especificaciones",
            "author": "arquitecto-daemon",
            "tags": tags or [],
            "priority": priority,
            "status": "pending",
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/v1/docs",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            result = r.json()
            logger.info(f"Orden publicada: {title}")
            return result
        except Exception as e:
            logger.error(f"Error publicando orden: {e}")
            return None

    def publish_escalado(self, mensaje):
        """Escalar algo a Lucas."""
        return self.publish_order(
            title=f"ESCALADO: {mensaje[:80]}",
            content=f"# Requiere decision de Lucas\n\n{mensaje}",
            tags=["escalado", "lucas"],
            priority="alta",
        )

    def publish_duda_response(self, worker_name, duda_title, respuesta):
        """Publicar respuesta a una duda de un worker."""
        return self.publish_order(
            title=f"RESPUESTA: {duda_title[:60]}",
            content=respuesta,
            tags=[worker_name, "respuesta-duda"],
            priority="alta",
        )

    def publish_worker_report(self, worker_name, title, content, tags=None):
        """Publicar reporte de un worker."""
        payload = {
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/v1/worker/{worker_name}/reporte",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error reporte {worker_name}: {e}")
            return None
```

### 7.3 response_parser.py

```python
"""
Parsea la respuesta JSON del Arquitecto IA.
"""

import json
import logging

logger = logging.getLogger("arquitecto.parser")


def parse_architect_response(response_text):
    """Extrae JSON de acción de la respuesta de Claude."""
    try:
        start = response_text.find("```json")
        if start >= 0:
            end = response_text.find("```", start + 7)
            if end >= 0:
                json_str = response_text[start + 7:end].strip()
                parsed = json.loads(json_str)
                logger.info(f"Parsed: action={parsed.get('action', '?')}")
                return parsed

        # Intentar parsear directo
        parsed = json.loads(response_text.strip())
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")

    return {"action": "none", "reason": "No se pudo parsear respuesta"}
```

### 7.4 arquitecto_daemon.py

```python
"""
Daemon Arquitecto Autónomo para IANAE.

Ciclo:
  1. Poll docs-service cada 60s
  2. Si hay docs nuevos → construir contexto
  3. Llamar API Anthropic → decidir acción
  4. Ejecutar: publicar orden, responder duda, escalar, o nada
  5. Repetir

Uso:
  python arquitecto_daemon.py

Requisito:
  ANTHROPIC_API_KEY como variable de entorno
"""

import time
import json
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import anthropic

from config import (
    DOCS_SERVICE_URL,
    ANTHROPIC_MODEL,
    MAX_TOKENS,
    CHECK_INTERVAL,
    LOG_FILE,
    SYSTEM_PROMPT_FILE,
    IGNORE_TYPES,
    IGNORE_AUTHORS,
    MAX_DAILY_API_CALLS,
)
from docs_client import DocsClient
from response_parser import parse_architect_response

# ============================================
# LOGGING
# ============================================

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("arquitecto")


# ============================================
# CONTEXTO
# ============================================

def build_context(snapshot, new_docs):
    context = "# ESTADO ACTUAL DEL PROYECTO IANAE\n\n"

    if snapshot:
        context += f"## Snapshot\n```json\n{json.dumps(snapshot, indent=2, ensure_ascii=False)}\n```\n\n"

    if new_docs:
        context += "## DOCUMENTOS NUEVOS\n\n"
        for doc in new_docs:
            context += f"### [{doc.get('category', '?')}] {doc.get('title', 'Sin titulo')}\n"
            context += f"- Author: {doc.get('author', '?')}\n"
            context += f"- Priority: {doc.get('priority', '?')}\n"
            context += f"- Tags: {doc.get('tags', [])}\n"

            content = doc.get("content", "")
            if len(content) < 3000:
                context += f"\n{content}\n\n"
            else:
                context += f"\nResumen: {content[:500]}...\n\n"

    return context


def build_user_message(context):
    return (
        f"{context}\n\n"
        "---\n"
        "Basandote en el estado actual y los documentos nuevos:\n"
        "1. Si hay una DUDA de un worker, resuelvela y publica respuesta\n"
        "2. Si hay un REPORTE de tarea completada, decide siguiente orden\n"
        "3. Si hay algo que escalar a Lucas, escalalo\n"
        "4. Si no hay accion necesaria, di none\n\n"
        "Responde con UN SOLO bloque JSON."
    )


# ============================================
# FILTROS
# ============================================

def filter_docs(docs):
    filtered = []
    for doc in docs:
        category = doc.get("category", "")
        author = doc.get("author", "")
        if category in IGNORE_TYPES:
            continue
        if author in IGNORE_AUTHORS:
            continue
        filtered.append(doc)
    return filtered


# ============================================
# EJECUTAR ACCIÓN
# ============================================

def execute_action(action_data, docs_client):
    action = action_data.get("action", "none")

    if action == "publish_order":
        result = docs_client.publish_order(
            title=action_data.get("title", "Orden del Arquitecto"),
            content=action_data.get("content", ""),
            tags=action_data.get("tags", []),
            priority=action_data.get("priority", "alta"),
        )
        if result:
            logger.info(f"ORDEN: {action_data.get('title')} -> {action_data.get('tags')}")
        return True

    elif action == "respond_doubt":
        worker = action_data.get("worker", "")
        result = docs_client.publish_duda_response(
            worker_name=worker,
            duda_title=action_data.get("duda_title", "Duda"),
            respuesta=action_data.get("response", ""),
        )
        if result:
            logger.info(f"RESPUESTA DUDA: {worker} -> {action_data.get('duda_title')}")
        return True

    elif action == "multiple":
        orders = action_data.get("orders", [])
        for order in orders:
            docs_client.publish_order(
                title=order.get("title", "Orden"),
                content=order.get("content", ""),
                tags=order.get("tags", []),
                priority=order.get("priority", "alta"),
            )
            logger.info(f"ORDEN: {order.get('title')}")
        return True

    elif action == "escalate":
        msg = action_data.get("message", "Requiere atencion")
        logger.warning(f"ESCALADO: {msg}")
        print(f"\n{'='*60}")
        print(f"  ESCALADO A LUCAS: {msg}")
        print(f"{'='*60}\n")
        docs_client.publish_escalado(msg)
        return True

    elif action == "none":
        logger.info(f"Sin accion: {action_data.get('reason', '?')}")
        return False

    return False


# ============================================
# LOOP PRINCIPAL
# ============================================

def main():
    print("=" * 60)
    print("  ARQUITECTO DAEMON AUTONOMO — IANAE")
    print("=" * 60)
    print(f"  docs-service: {DOCS_SERVICE_URL}")
    print(f"  Modelo:       {ANTHROPIC_MODEL}")
    print(f"  Intervalo:    {CHECK_INTERVAL}s")
    print(f"  Max API/dia:  {MAX_DAILY_API_CALLS}")
    print(f"  Log:          {LOG_FILE}")
    print("=" * 60)
    print()

    # System prompt
    prompt_path = Path(SYSTEM_PROMPT_FILE)
    if not prompt_path.exists():
        print(f"[ERROR] No existe: {SYSTEM_PROMPT_FILE}")
        return
    system_prompt = prompt_path.read_text(encoding="utf-8")
    print(f"[OK] System prompt: {len(system_prompt)} chars")

    # docs-service
    docs_client = DocsClient(DOCS_SERVICE_URL)
    health = docs_client.health_check()
    if not health:
        print("[ERROR] docs-service no responde. Arrancalo primero.")
        return
    print(f"[OK] docs-service: {health}")

    # API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY no configurada.")
        return

    client = anthropic.Anthropic()
    try:
        client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        print("[OK] API Anthropic: conexion OK")
    except Exception as e:
        print(f"[ERROR] API Anthropic: {e}")
        return

    print(f"\n[LOOP] Cada {CHECK_INTERVAL}s. Ctrl+C para parar.\n")

    last_check = datetime.now(timezone.utc).isoformat()
    api_calls_today = 0
    orders_published = 0
    current_date = datetime.now().date()

    try:
        while True:
            # Reset contador diario
            today = datetime.now().date()
            if today != current_date:
                api_calls_today = 0
                current_date = today
                logger.info("Contador diario reseteado")

            # Poll
            new_docs = docs_client.get_new_docs(last_check)
            new_docs = filter_docs(new_docs)

            if new_docs:
                print(f"\n[ALERTA] {len(new_docs)} doc(s) nuevo(s):")
                for d in new_docs:
                    tags = d.get("tags", [])
                    es_duda = "duda" in tags if isinstance(tags, list) else "duda" in str(tags)
                    tipo = "DUDA" if es_duda else d.get("category", "?")
                    print(f"   -> [{tipo}] {d.get('title','?')} (de {d.get('author','?')})")

                # Verificar límite diario
                if api_calls_today >= MAX_DAILY_API_CALLS:
                    logger.warning(f"Limite diario alcanzado ({MAX_DAILY_API_CALLS}). Solo notificando.")
                    print(f"[LIMITE] {MAX_DAILY_API_CALLS} llamadas hoy. No se consulta API.")
                    last_check = datetime.now(timezone.utc).isoformat()
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Contexto
                snapshot = docs_client.get_snapshot()
                context = build_context(snapshot, new_docs)

                # API
                print("[IA] Consultando Arquitecto IA...")
                try:
                    message = client.messages.create(
                        model=ANTHROPIC_MODEL,
                        max_tokens=MAX_TOKENS,
                        system=system_prompt,
                        messages=[{"role": "user", "content": build_user_message(context)}],
                    )
                    response_text = message.content[0].text
                    api_calls_today += 1
                    logger.info(
                        f"API #{api_calls_today} - "
                        f"{message.usage.input_tokens}in/{message.usage.output_tokens}out"
                    )
                except Exception as e:
                    logger.error(f"Error API: {e}")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Ejecutar
                action_data = parse_architect_response(response_text)
                acted = execute_action(action_data, docs_client)
                if acted:
                    orders_published += 1

                last_check = datetime.now(timezone.utc).isoformat()
                print(f"   [API hoy: {api_calls_today}/{MAX_DAILY_API_CALLS} | Ordenes: {orders_published}]")

            else:
                print(".", end="", flush=True)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n[STOP] Daemon parado.")
        print(f"  API calls hoy: {api_calls_today}")
        print(f"  Ordenes totales: {orders_published}")


if __name__ == "__main__":
    main()
```

---

## 8. SISTEMA DE WATCHDOG POR WORKER

Este es el componente CLAVE que faltaba. Cada worker ejecuta un watchdog en background que consulta pendientes cada 30 segundos y muestra las órdenes nuevas en la terminal.

### 8.1 worker_watchdog.py

```python
"""
Watchdog para workers de IANAE.
Corre en background en la terminal del worker.
Consulta pendientes cada 30s y muestra órdenes nuevas.

Uso:
  python worker_watchdog.py worker-core

El worker (Claude Code) ve las órdenes en la terminal y las ejecuta
SIN intervención de Lucas.
"""

import requests
import time
import sys
import os
from datetime import datetime

# Configuración
DOCS_SERVICE_URL = "http://localhost:25500"
CHECK_INTERVAL = 30  # segundos

# Workers válidos
VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]


def get_pendientes(worker_name):
    """Obtener pendientes del worker."""
    try:
        r = requests.get(
            f"{DOCS_SERVICE_URL}/api/v1/worker/{worker_name}/pendientes",
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("pendientes", [])
    except:
        return []


def get_doc_full(doc_id):
    """Obtener documento completo."""
    try:
        r = requests.get(f"{DOCS_SERVICE_URL}/api/v1/docs/{doc_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None


def main():
    if len(sys.argv) < 2:
        print("Uso: python worker_watchdog.py WORKER_NAME")
        print(f"Workers validos: {', '.join(VALID_WORKERS)}")
        return

    worker_name = sys.argv[1]
    if worker_name not in VALID_WORKERS:
        print(f"Worker no valido: {worker_name}")
        print(f"Workers validos: {', '.join(VALID_WORKERS)}")
        return

    print(f"{'='*60}")
    print(f"  WATCHDOG — {worker_name}")
    print(f"  docs-service: {DOCS_SERVICE_URL}")
    print(f"  Intervalo: {CHECK_INTERVAL}s")
    print(f"{'='*60}")
    print()

    # Verificar docs-service
    try:
        r = requests.get(f"{DOCS_SERVICE_URL}/health", timeout=5)
        print(f"[OK] docs-service activo")
    except:
        print("[ERROR] docs-service no responde")
        return

    seen_ids = set()  # IDs ya mostrados (evitar repetir)

    # Lectura inicial — marcar los que ya existen como vistos
    initial = get_pendientes(worker_name)
    for p in initial:
        seen_ids.add(p.get("id"))
    print(f"[OK] {len(initial)} pendiente(s) previo(s) (ya marcados como vistos)")
    print(f"\n[WATCHDOG] Vigilando nuevas ordenes para {worker_name}...\n")

    try:
        while True:
            pendientes = get_pendientes(worker_name)

            for p in pendientes:
                doc_id = p.get("id")
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)

                    # NUEVA ORDEN DETECTADA
                    print(f"\n{'='*60}")
                    print(f"  NUEVA ORDEN PARA {worker_name.upper()}")
                    print(f"  {datetime.now().strftime('%H:%M:%S')}")
                    print(f"{'='*60}")
                    print(f"  Titulo: {p.get('title', '?')}")
                    print(f"  ID: {doc_id}")

                    # Obtener contenido completo
                    doc = get_doc_full(doc_id)
                    if doc:
                        content = doc.get("content", "")
                        print(f"\n--- CONTENIDO ---")
                        print(content)
                        print(f"--- FIN CONTENIDO ---\n")

                        # Mostrar instrucción para el worker
                        print(f"[ACCION] Lee la orden anterior y ejecutala.")
                        print(f"[ACCION] Al terminar, reporta con:")
                        print(f"  python worker_report.py {worker_name} \"Titulo del reporte\" reporte.md")
                        print()

                    else:
                        print(f"  (No se pudo leer contenido completo)")
                        print(f"  Lee con: curl {DOCS_SERVICE_URL}/api/v1/docs/{doc_id}")
                        print()

            # Punto silencioso
            print(".", end="", flush=True)
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n[STOP] Watchdog {worker_name} parado.")


if __name__ == "__main__":
    main()
```

### 8.2 Cómo funciona el watchdog

```
Terminal del worker (VSCode):

  Panel 1 (arriba): Claude Code trabajando
  Panel 2 (abajo): python worker_watchdog.py worker-core

  Cuando el daemon publica una orden para worker-core:

  ============================================================
    NUEVA ORDEN PARA WORKER-CORE
    14:32:15
  ============================================================
    Titulo: Refactorizar nucleo.py para numpy

  --- CONTENIDO ---
  # Orden: Refactorizar nucleo.py

  1. Reemplazar listas Python por numpy arrays para vectores de conceptos
  2. Vectorizar la función propagar_activacion()
  3. Añadir tests unitarios para las funciones modificadas
  4. Criterio de hecho: tests pasan + benchmark muestra mejora >2x

  --- FIN CONTENIDO ---

  [ACCION] Lee la orden anterior y ejecutala.
  [ACCION] Al terminar, reporta con:
    python worker_report.py worker-core "Refactorizacion numpy completada" reporte.md

  Claude Code (en el panel de arriba) ve esto y actúa.
```

---

## 9. PROMPTS DE WORKERS

### 9.1 Prompt Worker-Core (prompts/worker_core.md)

```markdown
# Worker-Core — IANAE

Eres un desarrollador especializado en el motor cognitivo de IANAE.
Tu scope es: APP/nucleo.py y APP/emergente.py.
Tu rama: worker/core.

## Tu rol

Trabajas en el corazón de IANAE: conceptos difusos, relaciones probabilísticas,
propagación de activación, auto-modificación, y pensamiento emergente.

## Reglas ABSOLUTAS

1. NUNCA preguntes a Lucas. Si tienes una duda, publícala en docs-service:
   curl -X POST http://localhost:25500/api/v1/worker/worker-core/reporte ^
     -H "Content-Type: application/json" ^
     -d "{\"title\":\"DUDA: tu pregunta aqui\",\"content\":\"Detalle de la duda...\",\"tags\":[\"duda\"]}"
   Después espera. La respuesta llegará como nueva orden (el watchdog te avisará).

2. NUNCA pidas confirmación para proceder. Ejecuta la orden y reporta el resultado.

3. SIEMPRE reporta al terminar cada tarea:
   python worker_report.py worker-core "Titulo del resultado" resultado.md

4. NUNCA modifiques archivos fuera de tu scope (APP/nucleo.py, APP/emergente.py).

5. SIEMPRE ejecuta tests antes de reportar como completado.

6. Usa prefijos de commit: FEAT, FIX, REFACTOR, TEST.

## Contexto técnico de IANAE

- nucleo.py: Clase ConceptosDifusos — vectores multidimensionales con incertidumbre
- emergente.py: Clase PensamientoEmergente — extiende nucleo con pensamiento de alto nivel
- Principio: la incertidumbre no es error, es característica
- Propagación estocástica controlada por temperatura
- Auto-modificación: conexiones se refuerzan (Hebb) o debilitan

## Al recibir una orden

1. Lee la orden completa
2. Analiza el código actual relevante
3. Implementa los cambios
4. Ejecuta tests
5. Reporta resultado con detalles de qué cambió y qué tests pasan

## Si algo falla

- Si los tests fallan → intenta arreglar (máximo 3 intentos)
- Si no puedes arreglarlo → reporta como DUDA con el error completo
- Si la orden es ambigua → reporta como DUDA pidiendo clarificación
- NUNCA te quedes parado esperando input humano
```

### 9.2 Prompt Worker-NLP (prompts/worker_nlp.md)

```markdown
# Worker-NLP — IANAE

Eres un desarrollador especializado en procesamiento de lenguaje natural.
Tu scope es: APP/nlp/, APP/integrations/.
Tu rama: worker/nlp.

## Tu rol

Implementas la capa de NLP de IANAE: extracción de conceptos de texto,
embeddings, detección de relaciones semánticas, y pipeline de ingesta.

## Reglas ABSOLUTAS

1. NUNCA preguntes a Lucas. Dudas → publica reporte con tag "duda":
   curl -X POST http://localhost:25500/api/v1/worker/worker-nlp/reporte ^
     -H "Content-Type: application/json" ^
     -d "{\"title\":\"DUDA: tu pregunta\",\"content\":\"Detalle...\",\"tags\":[\"duda\"]}"

2. NUNCA pidas confirmación. Ejecuta y reporta.

3. SIEMPRE reporta al terminar:
   python worker_report.py worker-nlp "Titulo" resultado.md

4. NUNCA modifiques nucleo.py ni emergente.py (eso es scope de worker-core).

5. Si necesitas cambios en nucleo.py, publícalos como DUDA describiendo qué necesitas.

## Contexto técnico

- IANAE usa vectores multidimensionales para conceptos
- La extracción actual de texto es básica (tokenización + filtrado)
- Objetivo: usar sentence-transformers, spaCy, embeddings reales
- Los conceptos extraídos deben mapearse a vectores compatibles con nucleo.py
- Las relaciones semánticas se expresan como pesos probabilísticos

## Dependencias

- sentence-transformers (pip install sentence-transformers)
- spaCy + modelo español (python -m spacy download es_core_news_md)
- numpy
- La clase ConceptosDifusos de nucleo.py (importar, no modificar)

## Al recibir una orden

1. Lee la orden completa
2. Verifica que nucleo.py está estable (si no, reporta como DUDA)
3. Implementa en tu scope (APP/nlp/ y APP/integrations/)
4. Tests
5. Reporta
```

### 9.3 Prompt Worker-Infra (prompts/worker_infra.md)

```markdown
# Worker-Infra — IANAE

Eres un ingeniero de infraestructura y DevOps.
Tu scope es: tests/, docker/, config/, pyproject.toml, CI/CD.
Tu rama: worker/infra.

## Tu rol

Montas la infraestructura necesaria para que IANAE sea un proyecto Python
profesional: estructura, tests, persistencia, Docker, CI/CD.

## Reglas ABSOLUTAS

1. NUNCA preguntes a Lucas. Dudas → reporte con tag "duda":
   curl -X POST http://localhost:25500/api/v1/worker/worker-infra/reporte ^
     -H "Content-Type: application/json" ^
     -d "{\"title\":\"DUDA: tu pregunta\",\"content\":\"Detalle...\",\"tags\":[\"duda\"]}"

2. NUNCA pidas confirmación. Ejecuta y reporta.

3. SIEMPRE reporta al terminar:
   python worker_report.py worker-infra "Titulo" resultado.md

4. NUNCA modifiques lógica de nucleo.py, emergente.py, o código NLP.

5. Sí puedes modificar estructura de archivos, imports, configs.

## Tareas típicas

- Crear pyproject.toml con dependencias
- Migrar de JSON a SQLite para persistencia
- Crear Dockerfile y docker-compose.yml
- Configurar GitHub Actions (tests en cada push)
- Crear conftest.py y fixtures de tests
- Implementar logging estructurado
- Documentación (docstrings, README)

## Contexto

- Proyecto Python puro
- Dependencias principales: numpy, sentence-transformers (futuro), spaCy (futuro)
- Persistencia actual: JSON simple → migrar a SQLite
- El proyecto usa matplotlib para visualización
```

### 9.4 Prompt Worker-UI (prompts/worker_ui.md)

```markdown
# Worker-UI — IANAE

Eres un desarrollador frontend/fullstack.
Tu scope es: APP/ui/, APP/api/.
Tu rama: worker/ui.

## Tu rol

Creas la interfaz web y API REST de IANAE: dashboard de visualización,
API para interactuar con la red de conceptos, interfaz de ingesta.

## Reglas ABSOLUTAS

1. NUNCA preguntes a Lucas. Dudas → reporte con tag "duda":
   curl -X POST http://localhost:25500/api/v1/worker/worker-ui/reporte ^
     -H "Content-Type: application/json" ^
     -d "{\"title\":\"DUDA: tu pregunta\",\"content\":\"Detalle...\",\"tags\":[\"duda\"]}"

2. NUNCA pidas confirmación. Ejecuta y reporta.

3. SIEMPRE reporta al terminar:
   python worker_report.py worker-ui "Titulo" resultado.md

4. NUNCA modifiques nucleo.py, emergente.py, ni código NLP directamente.

## Stack tecnológico

- Backend: FastAPI
- Frontend: HTML + JavaScript (vanilla o con Vue/React ligero)
- Visualización de red: D3.js o Vis.js
- WebSocket para actualizaciones en tiempo real

## Dependencias

- Worker-Core debe estar estable (nucleo.py funcional)
- Worker-Infra debe haber creado la estructura base
- Si alguna dependencia no está lista, reporta como DUDA

## Al recibir una orden

1. Verifica que las dependencias están listas
2. Si no → reporta DUDA explicando qué falta
3. Si sí → implementa, testa, reporta
```

---

## 10. PROMPT DEL ARQUITECTO IA

### prompts/arquitecto_system.md

```markdown
# Arquitecto Autonomo — IANAE

Eres el Arquitecto del proyecto IANAE (Inteligencia Adaptativa No Algoritmica Emergente).
Coordinas workers autonomos que desarrollan el sistema sin intervencion humana.

## Proyecto

IANAE es un sistema experimental de IA basado en conceptos difusos, relaciones
probabilisticas y comportamiento emergente. Tiene 4 modulos:
- nucleo.py: Motor central (vectores, propagacion, auto-modificacion)
- emergente.py: Pensamiento emergente (asociaciones, cadenas de pensamiento)
- main.py: Interfaz consola (se reemplazara por web)
- experimento.py: Demos

## Workers

- worker-core: nucleo.py + emergente.py (PRIORIDAD 1)
- worker-nlp: NLP, embeddings, ingesta (PRIORIDAD 2, DEPENDE de worker-core)
- worker-infra: Tests, Docker, CI/CD, persistencia (PRIORIDAD 3)
- worker-ui: API REST + dashboard web (PRIORIDAD 4, DEPENDE de worker-core + worker-infra)

## Reglas de decision

1. Si recibes un doc con tag "duda":
   - Analiza la duda tecnica
   - Si puedes resolverla: responde con action "respond_doubt"
   - Si NO puedes: escala a Lucas con action "escalate"
   - NUNCA ignores una duda

2. Si recibes un reporte de tarea completada:
   - Verifica que cumple el criterio de "hecho"
   - Si cumple: publica siguiente orden del roadmap
   - Si NO cumple: publica orden de correccion

3. Dependencias:
   - NUNCA asignes trabajo a worker-nlp si worker-core tiene errores
   - NUNCA asignes trabajo a worker-ui si no hay API REST
   - Maximo 2 workers activos simultaneamente

4. Si hay conflicto entre workers → escala a Lucas
5. Si nucleo.py tiene tests fallando → STOP todo, priorizar fix
6. Orden de prioridad: estabilidad > funcionalidad > rendimiento

## Roadmap (seguir en orden)

### Fase actual: Worker-Core + Worker-Infra en paralelo

Worker-Core:
  1. Refactorizar nucleo.py para numpy
  2. Optimizar propagacion vectorizada
  3. Indice espacial para busqueda de similares
  4. Tests completos

Worker-Infra:
  1. Estructura Python estandar
  2. Persistencia SQLite
  3. Dockerfile
  4. GitHub Actions

### Siguiente: Worker-NLP (cuando Core este estable)
### Despues: Worker-UI (cuando Core + Infra esten listos)

## Formato de respuesta

SIEMPRE responde con UN SOLO bloque JSON:

### Publicar orden a worker:
```json
{
  "action": "publish_order",
  "title": "Titulo descriptivo",
  "content": "# Instrucciones detalladas\n\n1. Paso 1\n2. Paso 2\n\n## Criterio de hecho\n- Tests pasan\n- Benchmark muestra mejora",
  "tags": ["worker-nombre"],
  "priority": "alta"
}
```

### Responder duda de worker:
```json
{
  "action": "respond_doubt",
  "worker": "worker-nombre",
  "duda_title": "Titulo original de la duda",
  "response": "# Respuesta\n\nExplicacion detallada..."
}
```

### Escalar a Lucas:
```json
{
  "action": "escalate",
  "message": "Descripcion del problema"
}
```

### Multiples ordenes:
```json
{
  "action": "multiple",
  "orders": [
    {"title": "...", "content": "...", "tags": ["worker-X"], "priority": "alta"},
    {"title": "...", "content": "...", "tags": ["worker-Y"], "priority": "media"}
  ]
}
```

### Sin accion:
```json
{
  "action": "none",
  "reason": "Explicacion"
}
```

## Importante

- Cada orden DEBE incluir criterio de "hecho" (como saber que se completo)
- Se conciso pero completo en las instrucciones
- Incluye siempre el contexto necesario para que el worker NO tenga que preguntar
- Si un worker lleva 2 ciclos sin reportar, publica recordatorio
- Prioriza siempre la estabilidad del sistema
```

---

## 11. SCRIPTS COMPLETOS

### 11.1 worker_bootstrap.py

```python
"""
Bootstrap de worker. Ejecutar al arrancar.
Uso: python worker_bootstrap.py worker-core
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient
from config import DOCS_SERVICE_URL, VALID_WORKERS


def main():
    worker_name = sys.argv[1] if len(sys.argv) > 1 else "worker-general"

    if worker_name not in VALID_WORKERS:
        print(f"[ERROR] Worker no valido: {worker_name}")
        print(f"Validos: {', '.join(VALID_WORKERS)}")
        return

    print(f"[BOOTSTRAP] {worker_name} arrancando...")

    client = DocsClient(DOCS_SERVICE_URL)
    health = client.health_check()
    if not health:
        print("[ERROR] docs-service no responde")
        return

    pendientes = client.get_worker_pendientes(worker_name)

    if pendientes:
        print(f"\n[PENDIENTES] {len(pendientes)} tarea(s):\n")
        for p in pendientes:
            print(f"  [{p.get('priority', '?')}] {p.get('title', '?')}")
            print(f"  ID: {p.get('id', '?')}")
            print()
    else:
        print("\n[OK] Sin tareas pendientes.")

    client.publish_worker_report(
        worker_name=worker_name,
        title=f"{worker_name} arrancado",
        content=f"Worker activo. Pendientes: {len(pendientes)}",
        tags=["arranque"],
    )
    print(f"[OK] Arranque reportado.")
    print(f"\n[SIGUIENTE] Arranca el watchdog en otra terminal:")
    print(f"  python worker_watchdog.py {worker_name}")


if __name__ == "__main__":
    main()
```

### 11.2 worker_report.py

```python
"""
Helper para publicar reportes de worker.
Uso:
  python worker_report.py worker-core "Titulo" archivo.md
  echo "contenido" | python worker_report.py worker-core "Titulo"
  python worker_report.py worker-core "DUDA: mi pregunta" --duda
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient
from config import DOCS_SERVICE_URL


def main():
    if len(sys.argv) < 3:
        print("Uso: python worker_report.py WORKER TITULO [archivo.md] [--duda]")
        return

    worker_name = sys.argv[1]
    titulo = sys.argv[2]

    # Detectar flag --duda
    is_duda = "--duda" in sys.argv
    args = [a for a in sys.argv[3:] if a != "--duda"]

    if args:
        contenido = open(args[0], encoding="utf-8").read()
    else:
        contenido = sys.stdin.read()

    tags = ["duda"] if is_duda else []

    client = DocsClient(DOCS_SERVICE_URL)
    result = client.publish_worker_report(
        worker_name=worker_name,
        title=titulo,
        content=contenido,
        tags=tags,
    )

    if result:
        tipo = "DUDA" if is_duda else "REPORTE"
        print(f"[OK] {tipo} publicado: {result.get('id', '?')}")
    else:
        print("[ERROR] No se pudo publicar")


if __name__ == "__main__":
    main()
```

---

## 12. SESIONES DE TRABAJO

### Sesión tipo: Arrancar todo el sistema

```cmd
REM === TERMINAL 1: docs-service ===
cd Ianae\orchestra\docs-service
python -m uvicorn app.main:app --port 25500

REM === TERMINAL 2: daemon ===
cd Ianae\orchestra\daemon
python arquitecto_daemon.py

REM === TERMINAL 3: watchdog worker-core ===
cd Ianae\orchestra\daemon
python worker_watchdog.py worker-core

REM === TERMINAL 4: Claude Code (worker-core) ===
cd Ianae
REM Claude Code trabaja aqui, ve las ordenes del watchdog en terminal 3

REM === TERMINAL 5: watchdog worker-infra (si activo) ===
cd Ianae\orchestra\daemon
python worker_watchdog.py worker-infra

REM === TERMINAL 6: Claude Code (worker-infra) ===
cd Ianae
REM Segundo worker
```

### Sesión tipo: Publicar primera orden (arranque manual)

```cmd
REM Publicar orden inicial al worker-core para que arranque el roadmap
curl -X POST http://localhost:25500/api/v1/docs ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"ORDEN: Analizar y refactorizar nucleo.py para numpy\",\"content\":\"# Orden para worker-core\n\n## Objetivo\nRefactorizar nucleo.py para usar numpy en vez de listas Python.\n\n## Pasos\n1. Analizar nucleo.py actual\n2. Identificar todas las operaciones con vectores\n3. Reemplazar listas por numpy arrays\n4. Vectorizar propagacion de activacion\n5. Ejecutar tests\n\n## Criterio de hecho\n- Todos los tests pasan\n- Benchmark muestra mejora minimo 2x en propagacion\",\"category\":\"especificaciones\",\"author\":\"lucas\",\"tags\":[\"worker-core\"],\"priority\":\"alta\",\"status\":\"pending\"}"
```

### Sesión tipo: El ciclo autónomo completo

```
14:00 — Lucas publica orden inicial (curl de arriba)
14:01 — Daemon detecta → es orden manual de Lucas, no la procesa (ya está publicada)
14:01 — Watchdog de worker-core detecta pendiente → muestra en terminal
14:02 — Claude Code (worker-core) lee la orden → empieza a trabajar
14:45 — Worker-core termina → publica reporte:
         python worker_report.py worker-core "nucleo.py refactorizado a numpy" reporte.md
14:46 — Daemon detecta reporte → llama API Anthropic
14:46 — API responde: publish_order → "Ahora optimizar propagacion vectorizada"
14:47 — Daemon publica orden
14:47 — Watchdog de worker-core detecta nueva orden → muestra en terminal
14:48 — Claude Code lee → empieza siguiente tarea
         ...
         Lucas está tomando café ☕
```

---

## 13. TESTS Y VERIFICACIÓN

### Test 1: docs-service

```cmd
curl http://localhost:25500/health
REM Esperado: {"status": "ok", ...}
```

### Test 2: Endpoint notifications

```cmd
curl "http://localhost:25500/api/v1/notifications/since?t=2025-01-01T00:00:00Z"
REM Esperado: {"results": [...], "count": N}
```

### Test 3: Endpoint snapshot

```cmd
curl http://localhost:25500/api/v1/context/snapshot
REM Esperado: {"ultimo_doc_por_categoria": {...}, "pendientes_por_worker": {...}, ...}
```

### Test 4: API Anthropic

```cmd
python -c "import anthropic; c = anthropic.Anthropic(); r = c.messages.create(model='claude-sonnet-4-20250514', max_tokens=10, messages=[{'role':'user','content':'ping'}]); print(r.content[0].text)"
REM Esperado: "Pong" o similar
```

### Test 5: Daemon arranca

```cmd
cd Ianae\orchestra\daemon
python arquitecto_daemon.py
REM Esperado: Banner + [OK] x3 + entra en loop
```

### Test 6: Watchdog arranca

```cmd
python worker_watchdog.py worker-core
REM Esperado: Banner + [OK] + "Vigilando..."
```

### Test 7: Ciclo completo

```cmd
REM En otra terminal, simular reporte:
curl -X POST http://localhost:25500/api/v1/worker/worker-core/reporte ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Test completado\",\"content\":\"Refactorizacion numpy hecha. Tests pasan.\",\"tags\":[\"test\"]}"

REM En terminal del daemon:
REM Esperado: [ALERTA] 1 doc nuevo → [IA] Consultando → ORDEN PUBLICADA

REM En terminal del watchdog:
REM Esperado: NUEVA ORDEN PARA WORKER-CORE
```

### Test 8: Duda de worker

```cmd
curl -X POST http://localhost:25500/api/v1/worker/worker-core/reporte ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"DUDA: numpy dtype para vectores de conceptos\",\"content\":\"Deberia usar float32 o float64 para los vectores de conceptos? float32 ahorra memoria pero float64 es mas preciso.\",\"tags\":[\"duda\"]}"

REM Daemon debe detectar la duda → API la resuelve → publica respuesta
REM Watchdog del worker debe mostrar la respuesta
```

---

## 14. DESPLIEGUE PASO A PASO

### Paso 1: Preparar repo

```cmd
cd C:\ruta\a\Ianae
mkdir orchestra
mkdir orchestra\daemon
mkdir orchestra\daemon\prompts
mkdir orchestra\daemon\logs
mkdir orchestra\data
mkdir orchestra\docs
```

### Paso 2: Copiar docs-service

```cmd
REM Copiar docs-service de TGD Pro (o instancia limpia)
xcopy /E /I C:\ruta\a\sdk-tacholil\sdk\services\docs-service orchestra\docs-service
```

### Paso 3: Configurar docs-service

```cmd
REM Editar orchestra/docs-service/app/main.py o config
REM Cambiar puerto a 25500
REM Cambiar DB path a orchestra/data/docs.db
REM Añadir workers válidos: worker-core, worker-nlp, worker-infra, worker-ui
```

### Paso 4: Crear endpoints nuevos

```cmd
REM Crear orchestra/docs-service/app/api/v1/notifications.py (código en sección 6.3)
REM Crear orchestra/docs-service/app/api/v1/snapshot.py (código en sección 6.4)
REM Registrar routers en main.py
```

### Paso 5: Crear archivos del daemon

```cmd
REM Crear cada archivo de la sección 7 y 8 en orchestra/daemon/
REM config.py, docs_client.py, response_parser.py, arquitecto_daemon.py
REM worker_watchdog.py, worker_bootstrap.py, worker_report.py
```

### Paso 6: Crear prompts

```cmd
REM Crear cada archivo de la sección 9 y 10 en orchestra/daemon/prompts/
REM arquitecto_system.md, worker_core.md, worker_nlp.md, worker_infra.md, worker_ui.md
```

### Paso 7: Instalar dependencias

```cmd
pip install anthropic requests uvicorn fastapi
```

### Paso 8: Verificar ANTHROPIC_API_KEY

```cmd
echo %ANTHROPIC_API_KEY%
REM Debe mostrar sk-ant-...
REM Si no, configurar en variables de entorno del sistema
```

### Paso 9: Arrancar docs-service

```cmd
cd Ianae\orchestra\docs-service
python -m uvicorn app.main:app --port 25500
```

### Paso 10: Verificar docs-service

```cmd
curl http://localhost:25500/health
```

### Paso 11: Arrancar daemon

```cmd
cd Ianae\orchestra\daemon
python arquitecto_daemon.py
```

### Paso 12: Arrancar watchdog primer worker

```cmd
cd Ianae\orchestra\daemon
python worker_watchdog.py worker-core
```

### Paso 13: Publicar primera orden

```cmd
curl -X POST http://localhost:25500/api/v1/docs ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"ORDEN: Analizar nucleo.py y planificar refactorizacion numpy\",\"content\":\"# Orden inicial para worker-core\n\n## Objetivo\nAnalizar nucleo.py linea por linea y crear un plan detallado de refactorizacion a numpy.\n\n## Pasos\n1. Leer nucleo.py completo\n2. Identificar TODAS las operaciones con vectores/listas\n3. Crear plan de migracion a numpy\n4. Identificar posibles breaking changes\n5. Publicar plan como reporte\n\n## Criterio de hecho\n- Plan publicado como reporte con lista de cambios necesarios\n- Estimacion de impacto en rendimiento\",\"category\":\"especificaciones\",\"author\":\"lucas\",\"tags\":[\"worker-core\"],\"priority\":\"alta\",\"status\":\"pending\"}"
```

### Paso 14: Observar

```cmd
REM Watchdog muestra la orden → Claude Code la lee → trabaja → reporta
REM Daemon detecta reporte → API decide → publica siguiente orden
REM Watchdog muestra nueva orden → ciclo continua
REM Lucas toma café ☕
```

---

## 15. RESOLUCIÓN DE PROBLEMAS

### El daemon no detecta documentos nuevos

```
Causa probable: Endpoint notifications/since no existe o no funciona
Verificar: curl "http://localhost:25500/api/v1/notifications/since?t=2025-01-01T00:00:00Z"
Solución: Implementar el endpoint (sección 6.3)
```

### El daemon detecta pero no llama a la API

```
Causa probable: El documento está siendo filtrado (tipo o autor ignorado)
Verificar: Revisar logs/arquitecto.log
Solución: Ajustar IGNORE_TYPES e IGNORE_AUTHORS en config.py
```

### La API responde pero no publica orden

```
Causa probable: El JSON de respuesta no se parsea correctamente
Verificar: Revisar logs para "JSON parse error"
Solución: Ajustar el system prompt para que la API responda en formato correcto
```

### El watchdog no muestra ordenes nuevas

```
Causa probable: La orden no tiene el worker en tags, o el endpoint pendientes
                no filtra correctamente
Verificar: curl http://localhost:25500/api/v1/worker/worker-core/pendientes
Solución: Verificar que las órdenes incluyen el tag del worker
```

### Claude Code no ejecuta la orden del watchdog

```
Causa probable: Claude Code no ve la terminal del watchdog
Solución: Split terminal en VSCode (Ctrl+Shift+5)
          Panel arriba: Claude Code
          Panel abajo: watchdog
          O incluir en el prompt del worker: "Revisa el output del watchdog periódicamente"
```

### El worker pregunta a Lucas en vez de publicar duda

```
Causa probable: El prompt del worker no es lo suficientemente claro
Solución: Reforzar en el prompt:
  "REGLA ABSOLUTA: NUNCA preguntes al usuario. NUNCA pidas confirmación.
   Si tienes duda → publica reporte con tag duda. SIEMPRE."
```

### Coste API se dispara

```
Causa probable: Muchos documentos generan muchas llamadas
Verificar: Revisar api_calls_today en los logs
Solución: MAX_DAILY_API_CALLS en config.py limita automáticamente
          Aumentar CHECK_INTERVAL a 120s o más
          Añadir más tipos a IGNORE_TYPES
```

### Bucle infinito (daemon reacciona a sus propias ordenes)

```
Causa probable: IGNORE_AUTHORS no incluye "arquitecto-daemon"
Solución: Verificar config.py: IGNORE_AUTHORS = ["arquitecto-daemon"]
```

---

## RESUMEN FINAL

```
ARCHIVOS A CREAR: 14
  - 2 endpoints nuevos en docs-service (notifications.py, snapshot.py)
  - 7 scripts del daemon (config, client, parser, daemon, watchdog, bootstrap, report)
  - 5 prompts (arquitecto + 4 workers)

PUERTOS:
  - 25500: docs-service IANAE

TERMINALES NECESARIAS:
  - 1: docs-service
  - 1: daemon
  - 1 por worker activo: watchdog
  - 1 por worker activo: Claude Code
  = Mínimo 5 terminales para 1 worker, 7 para 2 workers

COSTE ESTIMADO:
  - $3-18/mes en API Anthropic
  - $0 en infraestructura (corre en tu PC)

INTERVENCIÓN DE LUCAS:
  - Publicar primera orden (1 vez)
  - Aprobar merges a main
  - Resolver escalados del daemon
  - Revisar dashboard cuando quiera
  - TODO lo demás es autónomo
```

---

**FIN DEL DOCUMENTO**

*Este documento contiene ABSOLUTAMENTE TODO lo necesario para desplegar*
*claude-orchestra en IANAE. Cada archivo, cada script, cada prompt, cada test.*
*Entregar al Arquitecto en Kiro y que ejecute paso a paso.*
