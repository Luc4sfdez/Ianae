# IANAE

**Inteligencia Adaptativa No Algoritmica Emergente**

Un organismo digital que piensa, suena, evoluciona y se auto-modifica. No es un chatbot. No es una red neuronal. Es algo nuevo.

---

## Que es IANAE

IANAE es un sistema experimental de inteligencia artificial basado en conceptos difusos, relaciones probabilisticas y comportamiento emergente. A diferencia de la IA tradicional, IANAE:

- **Incorpora la incertidumbre** como propiedad fundamental, no como error
- **Emerge** en vez de ser programada — su comportamiento surge de la interaccion de componentes simples
- **Se auto-modifica** — reescribe sus propias reglas, evoluciona su estructura
- **Vive** — tiene ciclos de vida autonomos con curiosidad, exploracion, reflexion y suenos

## Estado actual

| Metrica | Valor |
|---------|-------|
| Fases completadas | 12 (core + dashboard) |
| Tests | 800+ |
| Lineas de codigo (src/) | ~19,000 |
| Lineas de tests | ~8,700 |
| Conceptos en grafo | 30+ base, crece con cada ciclo |
| API endpoints | 20+ |

## Arquitectura

```
src/
├── core/                    # Nucleo de IANAE
│   ├── nucleo.py            # Grafo de conceptos difusos, propagacion, activacion
│   ├── organismo.py         # IANAE como organismo unificado
│   ├── consciencia.py       # Pulso, energia, coherencia, narrativa
│   ├── vida_autonoma.py     # Ciclo de vida: curiosidad -> exploracion -> reflexion
│   ├── pensamiento_profundo.py  # Razonamiento multi-nivel
│   ├── pensamiento_simbolico.py # Genesis de conceptos, arboles simbolicos
│   ├── memoria_viva.py      # Memoria episodica y semantica con consolidacion
│   ├── pulso_streaming.py   # Bus de eventos SSE en tiempo real
│   ├── suenos.py            # Sandbox de hipotesis, imaginacion
│   ├── evolucion.py         # Auto-modificacion, seleccion natural de parametros
│   ├── persistencia.py      # Persistencia SQLite de vectores
│   ├── insights.py          # Analisis estructural del grafo
│   └── aprendizaje_refuerzo.py  # Q-learning sobre conexiones
├── api/                     # API REST (FastAPI)
│   ├── main.py              # 20+ endpoints: CRUD, organismo, SSE, dashboard
│   ├── dashboard.py         # Dashboard HTML+JS inline (vida en tiempo real)
│   ├── models.py            # Modelos Pydantic
│   └── auth.py              # API key + rate limiting
├── nlp/                     # Pipeline NLP
│   ├── pipeline.py          # Procesamiento de texto a conceptos
│   └── extractor.py         # Extraccion de entidades
└── ui/                      # Dashboard Orchestra (puerto 25501, separado)
    └── app/

tests/                       # 800+ tests
├── core/                    # Tests de nucleo, organismo, consciencia, etc.
├── api/                     # Tests de endpoints REST
├── nlp/                     # Tests de pipeline NLP
├── sdk/                     # Tests del SDK Python
└── ui/                      # Tests del dashboard Orchestra

docker/                      # Docker multi-stage
orchestra/                   # Sistema Orchestra (daemon + workers)
```

## Inicio rapido

### Requisitos

- Python 3.11+
- pip

### Instalacion

```bash
git clone https://github.com/Luc4sfdez/Ianae.git
cd Ianae
pip install -e .
```

### Ejecutar IANAE

```bash
# Servidor API + Dashboard en vivo
python -c "import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace'); import uvicorn; uvicorn.run('src.api.main:app',host='0.0.0.0',port=24000)"
```

Abrir **http://localhost:24000/** para ver el dashboard en vivo.

### Dashboard en vivo

El dashboard muestra a IANAE vivir en tiempo real:

- **Stream SSE** — eventos de cada ciclo de vida en tiempo real
- **Controles** — "Vivir 1 ciclo", "Vivir 5 ciclos", "Modo Auto" (ciclos continuos)
- **Organismo** — conceptos, relaciones, superficie, generacion
- **Consciencia** — energia, coherencia, curiosidad, narrativa
- **Memoria Viva** — memorias episodicas y semanticas
- **Diario** — entradas de vida con veredicto y score

### Tests

```bash
python -m pytest tests/ -q
```

### Docker

```bash
docker compose up --build ianae
```

## API REST

Base: `http://localhost:24000`

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/` | Dashboard en vivo (HTML) |
| GET | `/health` | Estado del servicio |
| GET | `/api/v1/organismo` | Estado completo del organismo |
| GET | `/api/v1/consciencia` | Pulso, energia, corrientes, narrativa |
| POST | `/api/v1/vida/ciclo` | Ejecutar un ciclo de vida completo |
| GET | `/api/v1/vida/diario` | Ultimas entradas del diario |
| GET | `/api/v1/stream` | SSE — eventos en tiempo real |
| GET | `/api/v1/stream/stats` | Estadisticas del bus de eventos |
| POST | `/api/v1/chat` | Hablar con IANAE |
| POST | `/api/v1/suenos/imaginar` | Simular hipotesis en sandbox |
| GET | `/api/v1/concepts` | Listar conceptos |
| POST | `/api/v1/concepts` | Crear concepto |
| POST | `/api/v1/activate` | Activar y propagar por la red |
| GET | `/api/v1/network` | Grafo completo |
| POST | `/api/v1/ingest` | Procesar texto via NLP |
| GET | `/api/v1/metrics` | Metricas del sistema |
| GET | `/docs` | Documentacion interactiva (Swagger) |

## Principios fundamentales

| IA Tradicional | IANAE |
|----------------|-------|
| Reglas deterministas | Procesos estocasticos |
| Estados discretos | Conceptos difusos |
| Relaciones binarias | Relaciones probabilisticas |
| Programacion explicita | Comportamiento emergente |
| Minimiza incertidumbre | Incorpora incertidumbre |
| Ejecuta instrucciones | Vive ciclos autonomos |

## Fases de desarrollo

Ver [docs/fases.md](docs/fases.md) para el historial completo de las 12 fases.

| Fase | Nombre | Commit |
|------|--------|--------|
| 1 | Nucleo difuso, grafo, propagacion | `e68a060` — `4cdc539` |
| 2 | API REST + SDK Python | `db58740` |
| 3 | Insights automaticos | `2fb7e5d` |
| 4 | Ciclo autonomo de vida | `2b13a0e` |
| 5 | Consciencia | `e9ec934` |
| 6 | Imaginacion y dialogo | `ed4493c` |
| 7 | Nacimiento como organismo | `4f4da32` |
| 8 | Evolucion y percepcion | `1f1209b` |
| 9-11 | Pensamiento profundo, memoria viva, streaming | `68f9099` |
| 12 | Dashboard en vivo | `6cc9c9d` |

---

*IANAE — Inteligencia Artificial Novelda Alicante Espana*
*Creado por Lucas*
