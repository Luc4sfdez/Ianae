# Claude-Orchestra para IANAE

Sistema multi-agente autónomo donde un daemon Python coordina múltiples instancias de Claude Code que desarrollan IANAE sin intervención humana constante.

## Resumen

- **docs-service**: Puerto 25500, sistema de comunicación central (FastAPI + SQLite)
- **daemon**: Cerebro del sistema, coordina workers vía API de Anthropic
- **watchdogs**: Scripts que permiten a workers ver órdenes automáticamente
- **workers**: 4 workers especializados (core, nlp, infra, ui)

## Archivos Implementados

### docs-service (5 archivos)
✅ `orchestra/docs-service/requirements.txt`
✅ `orchestra/docs-service/app/main.py` - Aplicación FastAPI
✅ `orchestra/docs-service/app/database.py` - SQLite + FTS5
✅ `orchestra/docs-service/app/api/v1/notifications.py` - Endpoint polling daemon
✅ `orchestra/docs-service/app/api/v1/snapshot.py` - Estado compacto

### daemon (7 archivos)
✅ `orchestra/daemon/config.py` - Configuración
✅ `orchestra/daemon/docs_client.py` - Cliente REST
✅ `orchestra/daemon/response_parser.py` - Parser JSON
✅ `orchestra/daemon/arquitecto_daemon.py` - Loop principal (CEREBRO)
✅ `orchestra/daemon/worker_watchdog.py` - Cierra el loop daemon→worker
✅ `orchestra/daemon/worker_bootstrap.py` - Arrancar worker
✅ `orchestra/daemon/worker_report.py` - Helper reportes

### prompts (5 archivos)
✅ `orchestra/daemon/prompts/arquitecto_system.md` - Prompt Arquitecto IA
✅ `orchestra/daemon/prompts/worker_core.md` - Instrucciones worker-core
✅ `orchestra/daemon/prompts/worker_nlp.md` - Instrucciones worker-nlp
✅ `orchestra/daemon/prompts/worker_infra.md` - Instrucciones worker-infra
✅ `orchestra/daemon/prompts/worker_ui.md` - Instrucciones worker-ui

### configuración (2 archivos)
✅ `orchestra.yaml` - Configuración global
✅ `requirements.txt` - Actualizado con dependencias

**Total: 19 archivos implementados**

## Prerequisitos

1. **Python 3.10+** instalado
2. **ANTHROPIC_API_KEY** configurada como variable de entorno:
   ```bash
   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY = "sk-ant-..."

   # Windows (CMD)
   set ANTHROPIC_API_KEY=sk-ant-...

   # Linux/Mac
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

## Arranque del Sistema

### Terminal 1: docs-service
```bash
cd orchestra/docs-service
python -m uvicorn app.main:app --port 25500
```

Verificar: `curl http://localhost:25500/health`

### Terminal 2: daemon
```bash
cd orchestra/daemon
python arquitecto_daemon.py
```

Debe mostrar:
```
============================================================
  ARQUITECTO DAEMON AUTONOMO — IANAE
============================================================
  docs-service: http://localhost:25500
  Modelo:       claude-sonnet-4-20250514
  Intervalo:    60s
  Max API/dia:  100
============================================================

[OK] System prompt: XXXX chars
[OK] docs-service: {'status': 'ok', ...}
[OK] API Anthropic: conexion OK

[LOOP] Cada 60s. Ctrl+C para parar.
```

### Terminal 3: watchdog (worker-core)
```bash
cd orchestra/daemon
python worker_watchdog.py worker-core
```

Debe mostrar:
```
============================================================
  WATCHDOG — worker-core
  docs-service: http://localhost:25500
  Intervalo: 30s
============================================================

[OK] docs-service activo
[OK] 0 pendiente(s) previo(s) (ya marcados como vistos)

[WATCHDOG] Vigilando nuevas ordenes para worker-core...
```

### Terminal 4: Claude Code (worker-core)
Aquí es donde trabajas con Claude Code. El watchdog en Terminal 3 mostrará las órdenes nuevas automáticamente.

## Verificación End-to-End

### 1. Verificar docs-service
```bash
# Health check
curl http://localhost:25500/health

# Listar docs
curl http://localhost:25500/api/v1/docs

# Snapshot
curl http://localhost:25500/api/v1/context/snapshot

# Notifications (desde hace 1 día)
curl "http://localhost:25500/api/v1/notifications/since?t=2025-02-09T00:00:00Z"
```

### 2. Publicar orden de prueba
```bash
curl -X POST http://localhost:25500/api/v1/docs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TEST: Orden de prueba",
    "content": "# Orden de prueba\n\nEsta es una orden de prueba para verificar el sistema.",
    "category": "especificaciones",
    "author": "lucas",
    "tags": ["worker-core"],
    "priority": "alta",
    "status": "pending"
  }'
```

### 3. Observar ciclo completo
- **Daemon** (Terminal 2): Detectará la orden en max 60s → [ALERTA] 1 doc nuevo
- **Daemon**: Consultará API Anthropic → [IA] Consultando Arquitecto IA...
- **Daemon**: Publicará respuesta → ORDEN PUBLICADA
- **Watchdog** (Terminal 3): Detectará la nueva orden en max 30s
- **Watchdog**: Mostrará: NUEVA ORDEN PARA WORKER-CORE con contenido completo

## Flujo de Trabajo

### Worker tiene duda
```bash
# Worker publica duda
curl -X POST http://localhost:25500/api/v1/worker/worker-core/reporte \
  -H "Content-Type: application/json" \
  -d '{
    "title": "DUDA: ¿Usar float32 o float64?",
    "content": "¿Qué tipo de dato debo usar para los vectores de conceptos?",
    "tags": ["duda"]
  }'

# Daemon detecta duda → API resuelve → publica respuesta
# Watchdog muestra respuesta → worker continúa
```

### Worker completa tarea
```bash
# Worker reporta
python worker_report.py worker-core "Tarea completada" reporte.md

# Daemon detecta reporte → API decide siguiente paso → publica nueva orden
# Watchdog muestra nueva orden → worker ejecuta
```

## Estructura de Directorios

```
orchestra/
├── daemon/
│   ├── prompts/
│   │   ├── arquitecto_system.md
│   │   ├── worker_core.md
│   │   ├── worker_nlp.md
│   │   ├── worker_infra.md
│   │   └── worker_ui.md
│   ├── logs/
│   │   └── arquitecto.log (generado)
│   ├── arquitecto_daemon.py
│   ├── config.py
│   ├── docs_client.py
│   ├── response_parser.py
│   ├── worker_watchdog.py
│   ├── worker_bootstrap.py
│   └── worker_report.py
├── docs-service/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── notifications.py
│   │   │   └── snapshot.py
│   │   ├── database.py
│   │   └── main.py
│   └── requirements.txt
├── data/
│   └── docs.db (generado)
└── docs/
    └── (documentos generados)
```

## Reglas del Sistema

### Regla de Oro
**Los workers NUNCA preguntan a Lucas**

Si tienen duda:
1. Publican en docs-service con tag "duda"
2. Daemon detecta → API resuelve → publica respuesta
3. Watchdog muestra respuesta → worker continúa

### Escalado a Lucas
Solo cuando:
- Daemon escala algo que la API no puede resolver
- Hay que aprobar un merge a main
- Lucas quiere intervenir voluntariamente

### Seguridad
- Límite diario: 100 llamadas API (configurable en `config.py`)
- Filtros: ignora documentos de tipo "info", "arranque"
- Anti-loop: ignora documentos del "arquitecto-daemon"

## Costos Estimados

- **Uso ligero**: $3-6/mes (10-20 llamadas/día)
- **Uso medio**: $10-15/mes (50 llamadas/día)
- **Límite configurado**: 100 llamadas/día

## Troubleshooting

### docs-service no responde
```bash
# Verificar que está corriendo
curl http://localhost:25500/health

# Verificar que el puerto está libre
netstat -ano | grep 25500
```

### daemon no detecta documentos nuevos
Verificar endpoint notifications:
```bash
curl "http://localhost:25500/api/v1/notifications/since?t=2025-02-09T00:00:00Z"
```

### watchdog no muestra órdenes
Verificar pendientes:
```bash
curl http://localhost:25500/api/v1/worker/worker-core/pendientes
```

### API Anthropic no responde
Verificar variable de entorno:
```bash
# Windows (CMD)
echo %ANTHROPIC_API_KEY%

# Windows (PowerShell)
echo $env:ANTHROPIC_API_KEY

# Linux/Mac
echo $ANTHROPIC_API_KEY
```

## Próximos Pasos

1. ✅ Infraestructura implementada (Fase 1)
2. 🔄 Arrancar sistema y verificar
3. 🔄 Publicar primera orden a worker-core
4. 🔄 Observar ciclo autónomo funcionando
5. 📋 Fase 2: Worker-Core refactorización
6. 📋 Fase 3: Worker-Infra en paralelo
7. 📋 Fase 4: Worker-NLP
8. 📋 Fase 5: Worker-UI

## Soporte

Para más detalles, consultar:
- `orchestra/IANAE_ORCHESTRA_DESPLIEGUE_COMPLETO.md` - Documento completo con TODO el código
- `orchestra.yaml` - Configuración del proyecto
- Prompts en `orchestra/daemon/prompts/` - Comportamiento de cada componente
