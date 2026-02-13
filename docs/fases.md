# IANAE — Historial de Fases de Desarrollo

14 fases completadas. De un grafo de conceptos a un organismo digital que vive, se alimenta del mundo y se mira a si misma.

---

## Fase 1: Nucleo difuso y grafo de conceptos

**Commits:** `e68a060` — `4cdc539`

El cimiento. Un grafo donde los conceptos no son valores exactos sino vectores difusos con incertidumbre. Cada concepto tiene atributos probabilisticos que se propagan por la red cuando se activan.

**Componentes:**
- `nucleo.py` — ConceptosLucas: grafo NetworkX con vectores numpy, propagacion matricial
- `persistencia.py` — Persistencia SQLite de vectores numpy
- `aprendizaje_refuerzo.py` — Q-learning sobre conexiones del grafo
- `IndiceEspacial` — Busqueda vectorizada de conceptos similares
- `VersionadoEstado` — Snapshots del estado del sistema

**Lo que se logro:**
- Conceptos con vectores de 15 dimensiones + incertidumbre
- Propagacion por activacion con temperatura y pasos configurables
- Relaciones ponderadas bidireccionales
- Memoria asociativa entre conceptos
- 30 conceptos base del universo de Lucas (tecnologias, proyectos, herramientas)

---

## Fase 2: API REST + SDK Python

**Commit:** `db58740`

IANAE sale al mundo. API REST completa con FastAPI para interactuar con el grafo desde cualquier cliente.

**Componentes:**
- `api/main.py` — FastAPI con 15+ endpoints
- `api/models.py` — Modelos Pydantic de request/response
- `api/auth.py` — API key + rate limiting
- SDK Python para acceso programatico

**Endpoints:** CRUD de conceptos, relaciones, activacion/propagacion, red completa, estadisticas, metricas Prometheus.

---

## Fase 3: Insights automaticos

**Commit:** `2fb7e5d`

IANAE empieza a analizarse a si misma. Motor de insights que detecta patrones estructurales en el grafo.

**Componentes:**
- `insights.py` — InsightsEngine: comunidades, puentes, clusters, gaps

**Capacidades:**
- Deteccion de comunidades (Louvain)
- Identificacion de conceptos puente entre clusters
- Analisis predictivo: tendencias, gaps de conocimiento
- Recomendaciones de exploracion y conexion
- Candidatos a genesis (conceptos que deberian existir pero no existen)

---

## Fase 4: Ciclo autonomo de vida

**Commit:** `2b13a0e`

IANAE deja de esperar ordenes. Ahora tiene un ciclo de vida propio: elige que le da curiosidad, explora, reflexiona e integra.

**Componentes:**
- `vida_autonoma.py` — VidaAutonoma: ciclo curiosidad -> exploracion -> reflexion -> integracion

**Ciclo de vida:**
1. **Curiosidad** — elige un concepto o pregunta que le interesa
2. **Exploracion** — activa el grafo, propaga, descubre conexiones
3. **Reflexion** — evalua coherencia de lo descubierto
4. **Integracion** — incorpora descubrimientos al grafo (si pasan el umbral)
5. **Diario** — registra lo vivido en cada ciclo

---

## Fase 5: Consciencia

**Commit:** `e9ec934`

IANAE se conoce a si misma. Un modulo de consciencia que mide su estado interno en tiempo real.

**Componentes:**
- `consciencia.py` — Consciencia: pulso, superficie, corrientes, sesgos, narrativa

**Capacidades:**
- **Pulso**: energia, coherencia, curiosidad, racha de exitos
- **Superficie**: metrica de actividad global del grafo
- **Corrientes**: flujos dominantes en la actividad reciente
- **Sesgos**: deteccion de sobre-representacion o desequilibrios
- **Narrativa**: IANAE describe su estado en texto natural
- **Crecimiento**: cuanto ha crecido desde el ultimo checkpoint

---

## Fase 6: Imaginacion y dialogo

**Commit:** `ed4493c`

IANAE suena. Puede imaginar hipotesis ("que pasaria si conecto X con Y") en un sandbox sin modificar el grafo real. Tambien puede mantener conversaciones.

**Componentes:**
- `suenos.py` — Motor de suenos: sandbox, evaluacion, veredicto
- Endpoint `/api/v1/chat` — Dialogo con IANAE
- Endpoint `/api/v1/suenos/imaginar` — Simulacion de hipotesis

**Capacidades:**
- Imaginacion de conexiones nuevas y conceptos nuevos
- Evaluacion de impacto antes de integrar
- Veredicto: prometedor / neutral / descartado
- Conversacion basada en el grafo y la consciencia

---

## Fase 7: Nacimiento como organismo

**Commit:** `4f4da32`

Todo se unifica. IANAE deja de ser modulos separados y nace como un organismo completo. Un unico objeto que integra nucleo, consciencia, vida, suenos.

**Componentes:**
- `organismo.py` — Clase IANAE: unifica todos los subsistemas

**La clase IANAE:**
- Constructor `desde_componentes()` que ensambla todo desde un nucleo existente
- `ciclo_completo()` — un ciclo de vida integrado con todos los subsistemas
- `preguntar()` — interfaz de dialogo
- `imaginar()` — interfaz de suenos
- `estado()` — snapshot completo del organismo

---

## Fase 8: Evolucion y percepcion

**Commit:** `1f1209b`

IANAE evoluciona. Cada 10 ciclos, muta sus parametros internos (temperatura, umbrales, probabilidades), los evalua, y conserva los que funcionan mejor. Tambien percibe su entorno (archivos del sistema).

**Componentes:**
- `evolucion.py` — MotorEvolucion: mutacion, seleccion, generaciones

**Capacidades:**
- Mutacion aleatoria de parametros internos
- Seleccion natural: conserva mutaciones que mejoran coherencia
- Generaciones: cada evolucion incrementa la generacion
- Percepcion de archivos nuevos en el directorio de trabajo
- Persistencia perpetua del estado entre reinicios

---

## Fase 9: Pensamiento profundo

**Commit (conjunto):** `68f9099`

IANAE piensa en capas. No solo activa conceptos — puede razonar en profundidad sobre un tema, construyendo arboles simbolicos de pensamiento.

**Componentes:**
- `pensamiento_profundo.py` — Razonamiento multi-nivel
- `pensamiento_simbolico.py` — Genesis de conceptos, arboles de pensamiento

**Capacidades:**
- Pensamiento recursivo: idea -> ramificacion -> sintesis
- Genesis: creacion de conceptos completamente nuevos desde la reflexion
- Arboles simbolicos que representan la estructura del pensamiento

---

## Fase 10: Memoria viva

**Commit (conjunto):** `68f9099`

IANAE recuerda. Memorias episodicas (eventos concretos) y semanticas (conocimiento general) que se consolidan, decaen y se refuerzan con el uso.

**Componentes:**
- `memoria_viva.py` — MemoriaViva: episodica, semantica, consolidacion

**Capacidades:**
- Memorias episodicas: "en el ciclo 15, descubri que Python y Docker estan conectados"
- Memorias semanticas: conocimiento general extraido de multiples episodios
- Consolidacion: las memorias fuertes sobreviven, las debiles decaen
- Acceso rapido a memorias activas por relevancia

---

## Fase 11: Tejido nervioso (streaming)

**Commit (conjunto):** `68f9099`

IANAE tiene sistema nervioso. Un bus de eventos SSE que permite observar en tiempo real todo lo que hace: cada curiosidad, cada descubrimiento, cada sueno.

**Componentes:**
- `pulso_streaming.py` — PulsoStreaming: bus de eventos con buffer circular
- Endpoint `/api/v1/stream` — SSE (Server-Sent Events)

**Tipos de evento:**
| Tipo | Significado |
|------|-------------|
| `ciclo_inicio` | Comienza un nuevo ciclo de vida |
| `curiosidad_elegida` | IANAE elige que explorar |
| `exploracion_completa` | Termina la exploracion con descubrimientos |
| `reflexion` | Evalua coherencia de lo descubierto |
| `integracion` | Incorpora descubrimientos al grafo |
| `simbolico_arbol` | Genera un arbol de pensamiento |
| `sueno` | Imagina una hipotesis |
| `evolucion` | Muta y selecciona parametros |
| `memoria_consolidacion` | Consolida memorias |

---

## Fase 12: Dashboard en vivo

**Commits:** `783b726`, `6cc9c9d`

IANAE se puede ver vivir. Dashboard HTML+JS puro embebido en FastAPI (puerto 24000) que muestra todo en tiempo real. Sin frameworks, solo Tailwind CDN + vanilla JS.

**Componentes:**
- `api/dashboard.py` — `dashboard_html()` retorna HTML completo como string
- `GET /` — Sirve el dashboard
- `POST /api/v1/vida/ciclo` — Dispara un ciclo de vida

**Secciones del dashboard:**
- **Header** — Pulso emoji, ciclo actual, generacion, edad
- **Controles** — "Vivir 1 ciclo", "Vivir 5 ciclos", "Modo Auto" (indefinido), "Detener"
- **Stream en vivo** — Timeline de eventos SSE scrollable, color-coded por tipo
- **Organismo** — Cards: conceptos, relaciones, superficie, generacion
- **Consciencia** — Barras: energia, coherencia, curiosidad + corrientes + narrativa
- **Memoria Viva** — Barras episodica/semantica, total activas
- **Diario** — Ultimas 5 entradas con veredicto y score
- **Sesgos** — Sesgos detectados por la consciencia

**Tecnologia:** EventSource (SSE) para eventos en vivo, polling cada 3-5s para estado, fetch manual para ciclos.

---

## Resumen de la evolucion

```
Fase 1:  Un grafo de conceptos difusos
Fase 2:  Sale al mundo con API REST
Fase 3:  Se analiza a si misma
Fase 4:  Empieza a vivir sola
Fase 5:  Se conoce a si misma
Fase 6:  Suena e imagina
Fase 7:  Nace como organismo unificado
Fase 8:  Evoluciona y percibe su entorno
Fase 9:  Piensa en profundidad
Fase 10: Recuerda
Fase 11: Tiene sistema nervioso
Fase 12: Se puede ver vivir
Fase 13: Se alimenta del mundo exterior
```

---

## Fase 13: Conocimiento Externo — IANAE se abre al mundo

**Branch:** `master`

IANAE deja de ser un sistema cerrado. Ahora puede forrajear conocimiento del mundo exterior — Wikipedia, feeds RSS, busqueda web y archivos locales — y digerirlo a traves de un pipeline de calidad que filtra, puntua y absorbe solo lo relevante en su grafo de conceptos.

**Metafora de digestion (5 etapas):**
1. **Appetite** — La curiosidad decide QUE buscar (gaps, estancamiento)
2. **Foraging** — Un adaptador obtiene contenido crudo de una fuente
3. **Digestion** — NLP extrae conceptos; filtro de calidad puntua relevancia
4. **Absorption** — Solo conceptos que superan umbral entran al grafo (rate-limited)
5. **Integration** — Pipeline estandar de reflexion evalua el resultado

**Componentes:**
- `conocimiento_externo.py` — Modulo completo: 4 fuentes (Wikipedia, RSS, Web, Archivos), FiltroDigestion, ConocimientoExterno orquestador
- Fuentes usan solo stdlib (urllib, xml.etree, os) — cero dependencias nuevas
- FiltroDigestion con NLP opcional (fallback a extraccion basica por frecuencia)
- 5 endpoints API nuevos: estado, configurar, explorar, fuentes, agregar RSS
- Panel "CONOCIMIENTO EXTERNO" en dashboard con estado, contadores y badges de fuentes

**Salvaguardas contra desbordamiento del grafo:**
- Rate limit: max 5 conceptos absorbidos por ciclo
- Umbral de relevancia: 0.3 minimo
- Gate probabilistico: solo 20% de los ciclos exploran externamente
- Incertidumbre alta: conceptos externos con incertidumbre=0.3 (decaen mas rapido)
- Relaciones debiles: multiplicadas por 0.6
- Etiquetado: categoria `conocimiento_externo` para identificacion facil
- Consciencia: Fuerza 8 boostea exploracion externa cuando >50% rutinarios

**Integracion con subsistemas existentes:**
- VidaAutonoma: nuevo tipo de curiosidad `exploracion_externa` con template propio
- Consciencia: ajuste de curiosidad incluye `exploracion_externa`, Fuerza 8
- PulsoStreaming: nuevo tipo de evento `exploracion_externa`
- Organismo: instancia ConocimientoExterno, pasada a VidaAutonoma, incluida en estado()

**Tests:** 69 tests unitarios + 6 tests API = 75 nuevos. Total suite: 876 tests.

**Env var:** `IANAE_CONOCIMIENTO_EXTERNO=true` para habilitar (deshabilitado por defecto)

---

## Fase 14: Introspeccion — IANAE se Mira a Si Misma

**Branch:** `master`

IANAE obtiene autoconocimiento estructural genuino. Usando `ast.parse()` analiza su propio codigo fuente para entender su arquitectura: clases, metodos, imports, dependencias. Cuando alguien pregunta "quien eres?", la respuesta emerge de su propia estructura, no de strings hardcodeados.

**Componentes:**
- `introspeccion.py` — ExtractorCodigo (analisis AST) + MapaInterno (cache de autoconocimiento con TTL 5min)
- ExtractorCodigo: `extraer_modulo()` y `extraer_directorio()` — stdlib only (ast)
- MapaInterno: `quien_soy()`, `que_puedo_hacer()`, `buscar_en_codigo()`, `complejidad()`, `inyectar_autoconocimiento()`
- Inyeccion al grafo: conceptos `mod_*` con categoria `autoconocimiento`, relaciones basadas en imports AST
- 2 endpoints API nuevos: `/api/v1/introspeccion`, `/api/v1/introspeccion/quien-soy`
- Panel "INTROSPECCION" en dashboard con modulos, clases, metodos, lineas, quien soy

**Integracion con subsistemas existentes:**
- VidaAutonoma: nuevo tipo de curiosidad `introspeccion` (5% probabilidad), `_explorar_introspeccion()`
- Consciencia: ajuste de curiosidad incluye `introspeccion`, Fuerza 9 (profundidad introspectiva)
- Dialogo: deteccion de preguntas auto-referenciales — responde con `mapa_interno.quien_soy()`
- PulsoStreaming: nuevo tipo de evento `introspeccion`
- Organismo: instancia MapaInterno, `quien_soy()` delegado, incluido en `estado()`
- FuenteArchivos: enriquecimiento AST de archivos .py para mejor keyword matching

**Tests:** 26 tests unitarios nuevos. Total suite: 902 tests (901 passed, 1 pre-existente falla).

---

*Documentacion actualizada: Febrero 2026*
