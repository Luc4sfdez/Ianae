# Roadmap - Fase B: IANAE Productivo

**Version:** 1.0
**Fecha:** 2026-02-12
**Estado:** En Preparacion
**Prerequisito:** Fase A completada (289+ tests, Docker, CI/CD, NLP basico, Dashboard)

---

## Objetivo de Fase B

**IANAE pasa de prototipo funcional a sistema productivo.**

- Aprendizaje continuo desde input real
- NLP con modelos ML reales (spaCy/transformers)
- API REST publica para integracion externa
- Benchmarks formales y optimizacion de rendimiento
- Hardening para produccion (logging, monitoring, error recovery)

---

## Mapa General de Fase B

```
+-------------------------------------------------------------+
|                        FASE B                                |
|                  IANAE Productivo                             |
+-------------+-------------+-------------+-------------------+
|    B.1      |     B.2     |     B.3     |       B.4         |
| NLP Real    | API REST    | Aprendizaje | Produccion        |
| (nlp)       | (api)       | Continuo    | (hardening)       |
|             |             | (core)      |                   |
| 8-10h       |  6-8h       |  8-10h      |   4-6h            |
| CRITICO     |  CRITICO    |  ALTO       |  MEDIO            |
+-------------+-------------+-------------+-------------------+

Dependencias:
- B.1 (NLP) -> INDEPENDIENTE (puede empezar ya)
- B.2 (API) -> INDEPENDIENTE (puede empezar ya)
- B.3 (Aprendizaje) -> Depende de B.1 (necesita input NLP real)
- B.4 (Produccion) -> Depende de B.1 + B.2
```

---

## B.1: NLP con Modelos Reales

### Objetivo
Reemplazar el modo "basico" (regex+frecuencia) por modelos ML reales para extraccion de conceptos y embeddings de alta calidad.

### Fase 1: spaCy Integration (3h)

**Tareas:**
1. Instalar spaCy con modelo `es_core_news_md` (espanol)
2. Implementar modo "spacy" en `ExtractorConceptos`
   - Extraccion de entidades nombradas (NER)
   - Extraccion de sustantivos y verbos relevantes
   - POS tagging para filtrar stopwords inteligentemente
3. Tests comparativos: modo basico vs spacy
4. Actualizar pipeline para auto-detectar spaCy

**Criterio:** Conceptos extraidos tienen mayor precision que regex

### Fase 2: Sentence Transformers (3h)

**Tareas:**
1. Integrar `sentence-transformers` con modelo multilingual
   - `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
2. Reemplazar embeddings hash-based por embeddings reales
3. Cache de embeddings en disco (SQLite o pickle)
4. Benchmarks: calidad de similitud coseno vs hash-based

**Criterio:** Similitud semantica real entre conceptos

### Fase 3: Pipeline Avanzado (2-4h)

**Tareas:**
1. Chunking inteligente de textos largos
2. Resolucion de correferencias (spaCy)
3. Extraccion de relaciones por dependencias gramaticales
4. Batch processing optimizado con GPU si disponible
5. Metricas de calidad del pipeline (precision, recall estimado)

**Criterio:** Pipeline procesa documentos completos, no solo frases

### Archivos a modificar
- `src/nlp/extractor.py` — modos spacy y transformers
- `src/nlp/pipeline.py` — cache disco, chunking
- `requirements.txt` — spacy, sentence-transformers
- `tests/nlp/` — tests comparativos

---

## B.2: API REST Publica

### Objetivo
Exponer IANAE como servicio independiente con API REST documentada, separando la logica de negocio del dashboard.

### Fase 1: API Core (3h)

**Tareas:**
1. Crear `src/api/main.py` — FastAPI app dedicada
2. Endpoints CRUD:
   - `POST /api/v1/concepts` — crear concepto
   - `GET /api/v1/concepts` — listar conceptos
   - `GET /api/v1/concepts/{name}` — detalle de concepto
   - `DELETE /api/v1/concepts/{name}` — eliminar concepto
   - `POST /api/v1/activate` — activar concepto y propagar
   - `GET /api/v1/network` — grafo completo
   - `POST /api/v1/ingest` — procesar texto via NLP
3. Pydantic models para request/response
4. Documentacion OpenAPI automatica

**Criterio:** API funcional con Swagger UI en `/docs`

### Fase 2: Autenticacion y Rate Limiting (2h)

**Tareas:**
1. API keys basicas (header `X-API-Key`)
2. Rate limiting por IP y por key
3. CORS configurado para dominios permitidos
4. Logging de requests

**Criterio:** API protegida contra abuso

### Fase 3: SDK Python (2h)

**Tareas:**
1. Crear `src/sdk/ianae_client.py` — cliente Python
2. Wrapper sobre requests con retry y error handling
3. Metodos: `client.activate("Python")`, `client.ingest("texto...")`
4. Publicable en PyPI (preparar setup)

**Criterio:** `pip install ianae-sdk` funciona

### Archivos nuevos
- `src/api/main.py`
- `src/api/models.py`
- `src/api/auth.py`
- `src/sdk/ianae_client.py`
- `tests/api/test_api.py`
- `tests/sdk/test_client.py`

---

## B.3: Aprendizaje Continuo

### Objetivo
IANAE aprende y evoluciona continuamente desde input real, sin reinicializacion manual.

### Fase 1: Ingesta Continua (3h)

**Tareas:**
1. Watcher de directorio: monitorea carpeta para nuevos .txt/.md
2. Auto-ingesta: cada archivo nuevo pasa por pipeline NLP
3. Conceptos nuevos se inyectan automaticamente en la red
4. Deduplicacion: no repetir conceptos ya existentes
5. Log de ingesta con metricas

**Criterio:** IANAE crece automaticamente con input

### Fase 2: Consolidacion Periodica (3h)

**Tareas:**
1. Ciclo de consolidacion cada N minutos:
   - Ejecutar ciclo_vital()
   - Consolidar memoria asociativa
   - Decaer conceptos sin activacion reciente
   - Genesis de conceptos emergentes (si hay candidatos)
2. Snapshot automatico antes de cada consolidacion
3. Metricas de crecimiento (conceptos/dia, relaciones nuevas)

**Criterio:** Red se auto-organiza con el tiempo

### Fase 3: Feedback Loop (2-4h)

**Tareas:**
1. El usuario puede marcar conceptos como "relevante" / "ruido"
2. Feedback ajusta pesos del aprendizaje por refuerzo
3. Conceptos marcados como ruido decaen mas rapido
4. Conceptos relevantes se fortalecen
5. Metricas de precision percibida

**Criterio:** La red mejora con feedback del usuario

### Archivos a modificar
- `src/core/nucleo.py` — metodo consolidar()
- `src/core/aprendizaje_refuerzo.py` — feedback externo
- Nuevo: `src/core/ingesta_continua.py`
- Nuevo: `src/core/consolidador.py`

---

## B.4: Hardening para Produccion

### Objetivo
Preparar IANAE para correr de forma estable y monitorizada.

### Fase 1: Logging Estructurado (2h)

**Tareas:**
1. Reemplazar `print()` por `logging` en todos los modulos
2. Formato JSON para logs (parseable por herramientas)
3. Niveles: DEBUG para desarrollo, INFO para produccion
4. Rotacion de logs por tamano

**Criterio:** Cero print() en produccion

### Fase 2: Error Recovery (2h)

**Tareas:**
1. Graceful shutdown con guardado de estado
2. Auto-recovery: cargar ultimo snapshot al iniciar
3. Health check endpoint con diagnosticos
4. Alertas por email/webhook si sistema se degrada

**Criterio:** Sistema se recupera solo de crashes

### Fase 3: Monitoring (2h)

**Tareas:**
1. Endpoint `/metrics` compatible con Prometheus
2. Metricas: conceptos activos, latencia de activacion, uso de memoria
3. Dashboard de Grafana (opcional, config incluida)
4. Alertas por umbrales

**Criterio:** Visibilidad total del estado del sistema

### Archivos a modificar
- Todos los modulos en `src/` — logging
- `src/api/main.py` — health, metrics
- Nuevo: `src/core/recovery.py`
- `docker-compose.yml` — volumen persistente, restart policy

---

## Cronograma Estimado

### Semana 1: Fundacion NLP + API
```
Dia 1-2: B.1 Fase 1 (spaCy integration)
         B.2 Fase 1 (API core endpoints)

Dia 3-4: B.1 Fase 2 (sentence-transformers)
         B.2 Fase 2 (auth + rate limiting)

Dia 5:   Integracion y tests
```

### Semana 2: NLP Avanzado + SDK
```
Dia 1-2: B.1 Fase 3 (pipeline avanzado)
         B.2 Fase 3 (SDK Python)

Dia 3-4: B.3 Fase 1 (ingesta continua)

Dia 5:   Integracion y tests
```

### Semana 3: Aprendizaje + Produccion
```
Dia 1-2: B.3 Fase 2 (consolidacion periodica)
         B.4 Fase 1 (logging)

Dia 3-4: B.3 Fase 3 (feedback loop)
         B.4 Fase 2 (error recovery)

Dia 5:   B.4 Fase 3 (monitoring)
         Tests end-to-end finales
```

---

## Metricas de Exito - Fase B

### NLP
- [ ] Extraccion con spaCy: precision >70% en conceptos relevantes
- [ ] Embeddings reales: similitud semantica medible
- [ ] Pipeline procesa documentos de 1000+ palabras

### API
- [ ] API REST con 6+ endpoints documentados
- [ ] Autenticacion y rate limiting funcional
- [ ] SDK Python publicable

### Aprendizaje
- [ ] Ingesta automatica desde directorio
- [ ] Consolidacion periodica sin intervencion
- [ ] Feedback del usuario afecta pesos

### Produccion
- [ ] Cero print() en codigo (todo via logging)
- [ ] Recovery automatico tras crash
- [ ] Metricas exportables

---

## Dependencias Externas

| Paquete | Version | Uso |
|---------|---------|-----|
| spacy | >=3.7 | NLP extraction |
| es_core_news_md | 3.7+ | Modelo espanol |
| sentence-transformers | >=2.2 | Embeddings |
| watchdog | >=3.0 | File watcher |
| prometheus-client | >=0.19 | Metricas |

---

## Desde Fase A

**Lo que ya funciona y se reutiliza:**
- `src/core/nucleo.py` — motor de conceptos (92% coverage)
- `src/core/aprendizaje_refuerzo.py` — Q-learning (97% coverage)
- `src/core/memoria_v2.py` — memoria asociativa (97% coverage)
- `src/nlp/pipeline.py` — pipeline basico con cache
- `src/ui/app/main.py` — dashboard D3.js + WebSocket
- Docker, CI/CD, 360 tests

**Lo que se mejora:**
- NLP: de regex a spaCy + transformers
- API: de endpoints embebidos en dashboard a API standalone
- Aprendizaje: de manual a continuo
- Operaciones: de print() a logging estructurado

---

**Fase B convierte IANAE de demo a producto.**
