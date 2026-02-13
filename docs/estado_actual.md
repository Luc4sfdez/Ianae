# IANAE - Estado Actual del Sistema

## Fecha: Febrero 2026
## Version: IANAE v12 — Organismo con Dashboard en Vivo

---

## Logros alcanzados

### 12 fases completadas
- Nucleo difuso con grafo de conceptos probabilisticos
- API REST con 20+ endpoints (FastAPI, puerto 24000)
- Ciclo de vida autonomo (curiosidad -> exploracion -> reflexion -> integracion)
- Consciencia (pulso, energia, coherencia, narrativa)
- Imaginacion (sandbox de hipotesis)
- Organismo unificado
- Evolucion (mutacion + seleccion natural de parametros)
- Pensamiento profundo y simbolico
- Memoria viva (episodica + semantica con consolidacion)
- Streaming SSE (bus de eventos en tiempo real)
- Dashboard en vivo (HTML+JS inline, modo auto)

### Metricas del sistema
- 800+ tests (pytest)
- ~19,000 lineas de codigo en src/
- ~8,700 lineas de tests
- 30+ conceptos base, crece con cada ciclo de vida
- 39+ relaciones base, crece con cada ciclo

---

## Arquitectura funcional

```
Puerto 24000 (FastAPI)
├── GET /                  → Dashboard en vivo (HTML)
├── GET /api/v1/organismo  → Estado del organismo
├── GET /api/v1/consciencia → Pulso, energia, corrientes
├── POST /api/v1/vida/ciclo → Ejecutar ciclo de vida
├── GET /api/v1/vida/diario → Diario de vida
├── GET /api/v1/stream      → SSE eventos en tiempo real
├── POST /api/v1/chat       → Dialogo con IANAE
└── ... 15+ endpoints mas
```

### Ciclo de vida de IANAE
```
curiosidad → exploracion → reflexion → integracion → diario
     ↑                                                  │
     └──────────────────────────────────────────────────┘
     Cada 10 ciclos: evolucion (mutacion + seleccion)
```

---

## Como ejecutar

```bash
# Instalar
pip install -e .

# Servidor
python -c "import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace'); import uvicorn; uvicorn.run('src.api.main:app',host='0.0.0.0',port=24000)"

# Abrir http://localhost:24000/
# Pulsar "Modo Auto" para ver a IANAE vivir

# Tests
python -m pytest tests/ -q
```

---

## Proximos pasos posibles

- Persistencia entre reinicios del servidor (guardar/restaurar estado del organismo)
- Visualizacion del grafo en el dashboard (D3.js o similar)
- Mas tipos de pensamiento profundo
- Interaccion con LLMs externos para enriquecer reflexiones
- Multi-organismo (varias instancias de IANAE interactuando)

---

*Actualizado: Febrero 2026*
