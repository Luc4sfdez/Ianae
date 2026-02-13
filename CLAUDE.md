# IANAE — Prompt de Recuperacion de Contexto

## Que es IANAE

IANAE (Inteligencia Adaptativa No Algoritmica Emergente) es un organismo digital en Python. No es un chatbot ni una red neuronal — es un sistema basado en conceptos difusos, relaciones probabilisticas y comportamiento emergente que vive ciclos de vida autonomos: elige curiosidades, explora, reflexiona, suena, evoluciona y se auto-modifica.

## Estado actual: 13 fases completadas

- **876 tests** (1 fallo pre-existente en `test_evolucion.py::test_intervalo_respeta_limites`, no critico)
- **~19,500 lineas** de codigo en `src/`, **~9,400** en `tests/`
- **Branch**: `master` (es la principal, se pushea con `git push origin master`)
- Docs detallados de cada fase en `docs/fases.md`

## Arquitectura del proyecto

```
src/
├── core/
│   ├── nucleo.py              # Grafo de conceptos difusos (ConceptosLucas), propagacion matricial
│   ├── organismo.py           # Clase IANAE — unifica todo, ciclo_completo()
│   ├── consciencia.py         # Pulso, energia, coherencia, corrientes, narrativa
│   ├── vida_autonoma.py       # Ciclo: curiosidad->exploracion->reflexion->integracion->diario
│   ├── pensamiento_profundo.py
│   ├── pensamiento_simbolico.py  # Genesis de conceptos
│   ├── memoria_viva.py        # Episodica + semantica con consolidacion
│   ├── pulso_streaming.py     # Bus SSE con buffer circular
│   ├── suenos.py              # Sandbox de hipotesis
│   ├── evolucion.py           # Mutacion + seleccion natural cada 10 ciclos
│   ├── persistencia.py        # SQLite para vectores numpy
│   ├── conocimiento_externo.py # Fase 13: fuentes externas (Wiki, RSS, Web, Archivos) + filtro digestion
│   ├── insights.py            # Comunidades, puentes, analisis predictivo
│   └── aprendizaje_refuerzo.py
├── api/
│   ├── main.py                # FastAPI, 25+ endpoints, puerto 24000
│   ├── dashboard.py           # dashboard_html() — HTML+JS+CSS inline, dashboard de vida
│   ├── models.py              # Pydantic models
│   └── auth.py                # API key (opcional si IANAE_API_KEYS esta seteado) + rate limit
├── nlp/                       # Pipeline NLP (extractor + pipeline)
└── ui/app/                    # Dashboard Orchestra separado (puerto 25501, NO es el de vida)

tests/                         # 876 tests (core/, api/, nlp/, sdk/, ui/)
docker/                        # Dockerfile multi-stage
orchestra/                     # Daemon + workers
docs/
├── fases.md                   # Historial detallado de las 13 fases
└── estado_actual.md           # Estado febrero 2026
```

## Endpoints clave del API (puerto 24000)

| Metodo | Ruta | Auth | Que hace |
|--------|------|------|----------|
| GET | `/` | No | Dashboard HTML en vivo |
| GET | `/api/v1/organismo` | Si* | Estado completo (conceptos, relaciones, ciclo, generacion, memoria_viva) |
| GET | `/api/v1/consciencia` | Si* | Pulso, energia, corrientes, sesgos, narrativa |
| POST | `/api/v1/vida/ciclo` | No | Dispara ciclo_completo() |
| GET | `/api/v1/vida/diario` | Si* | Ultimas N entradas del diario |
| GET | `/api/v1/stream` | No | SSE eventos en vivo (EventSource) |
| POST | `/api/v1/chat` | Si* | Hablar con IANAE |
| GET | `/api/v1/concepts` | Si* | Listar conceptos |
| GET | `/api/v1/conocimiento` | Si* | Estado del conocimiento externo |
| POST | `/api/v1/conocimiento/configurar` | Si* | Configurar conocimiento externo |
| POST | `/api/v1/conocimiento/explorar` | Si* | Explorar concepto en fuentes externas |
| GET | `/api/v1/conocimiento/fuentes` | Si* | Listar fuentes y su estado |
| POST | `/api/v1/conocimiento/rss` | Si* | Agregar feed RSS |

*Auth solo si `IANAE_API_KEYS` env var esta configurado. Sin ella, todo es abierto.

**Env var para conocimiento externo:** `IANAE_CONOCIMIENTO_EXTERNO=true` habilita el forrajeo. Deshabilitado por defecto.

## Como levantar el servidor en Windows

```bash
python -c "import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace'); import uvicorn; uvicorn.run('src.api.main:app',host='0.0.0.0',port=24000)"
```

El wrapper de stdout es necesario porque `nucleo.py:1144` hace `print("🚀...")` y la consola Windows cp1252 no soporta emojis. En Docker/Linux no hace falta.

## Patrones del codigo

- `get_organismo()` en `main.py` hace lazy init: `crear_universo_lucas()` -> `IANAE.desde_componentes()`
- `ciclo_completo()` ejecuta: percepcion -> feedback suenos -> ciclo consciente -> sueno -> evolucion (cada 10) -> streaming
- Tests: `python -m pytest tests/ -q` desde `E:\ianae-final`
- El dashboard de `src/ui/app/` es para Orchestra (servicio separado) — NO es el dashboard de vida
- El dashboard de vida es `src/api/dashboard.py` servido en `GET /` del mismo FastAPI

## Fases completadas

1. Nucleo difuso + grafo de conceptos
2. API REST + SDK Python
3. Insights automaticos (comunidades, puentes, predictivo)
4. Ciclo autonomo de vida (curiosidad -> exploracion -> reflexion -> integracion)
5. Consciencia (pulso, energia, coherencia, narrativa)
6. Imaginacion y dialogo (sandbox de hipotesis, chat)
7. Nacimiento como organismo unificado (clase IANAE)
8. Evolucion + percepcion del entorno
9. Pensamiento profundo y simbolico
10. Memoria viva (episodica + semantica con consolidacion)
11. Streaming SSE (bus de eventos en tiempo real)
12. Dashboard en vivo con modo auto
13. Conocimiento externo (Wikipedia, RSS, Web, Archivos + filtro digestion)

## Reglas importantes

- No tocar `src/core/` a menos que se pida — es el nucleo estable con 876 tests
- Branch `master` pushea a `origin/master` (no a main)
- Los archivos en `data/` y `tmp_*` son runtime, no van al repo
- Siempre correr tests despues de cambios: `python -m pytest tests/ -q`
