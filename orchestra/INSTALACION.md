# Guía de Instalación Claude-Orchestra para IANAE

## Estado Actual

✅ **COMPLETADO**: Todos los archivos del sistema han sido implementados (19 archivos).

## Resumen de Implementación

```
✅ Fase 1: Infraestructura Base (COMPLETADA)
   ✅ Estructura de directorios
   ✅ docs-service (5 archivos)
   ✅ daemon (7 archivos)
   ✅ prompts (5 archivos)
   ✅ configuración (2 archivos)

🔄 Fase 2: Verificación
   - Instalar dependencias
   - Arrancar docs-service
   - Arrancar daemon
   - Arrancar watchdog
   - Probar ciclo completo

📋 Fase 3: Desarrollo
   - Worker-Core refactorización
   - Worker-Infra en paralelo
   - Worker-NLP
   - Worker-UI
```

## Paso 1: Verificar Archivos

Ejecuta el script de verificación:

```bash
cd E:\ianae-final
python orchestra/verify_system.py
```

Debe mostrar ✅ en todos los componentes.

## Paso 2: Instalar Dependencias

```bash
pip install -r requirements.txt
```

Dependencias instaladas:
- anthropic>=0.21.0 (API de Claude)
- requests>=2.31.0 (cliente HTTP)
- fastapi>=0.104.0 (docs-service)
- uvicorn>=0.24.0 (servidor ASGI)
- python-multipart>=0.0.6 (formularios)

## Paso 3: Configurar ANTHROPIC_API_KEY

### Windows (PowerShell - recomendado)
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Para hacerlo permanente:
1. Panel de Control → Sistema → Configuración avanzada
2. Variables de entorno
3. Nueva variable de usuario: `ANTHROPIC_API_KEY` = `sk-ant-...`

### Windows (CMD)
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
```

### Linux/Mac
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Para hacerlo permanente, añadir a `~/.bashrc` o `~/.zshrc`:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
```

Verificar:
```bash
echo %ANTHROPIC_API_KEY%  # Windows CMD
echo $env:ANTHROPIC_API_KEY  # Windows PowerShell
echo $ANTHROPIC_API_KEY  # Linux/Mac
```

## Paso 4: Arrancar docs-service

**Terminal 1:**
```bash
cd E:\ianae-final\orchestra\docs-service
python -m uvicorn app.main:app --port 25500
```

Verificar en otra terminal:
```bash
curl http://localhost:25500/health
```

Debe responder:
```json
{
  "status": "ok",
  "service": "docs-service-ianae",
  "port": 25500
}
```

## Paso 5: Arrancar daemon

**Terminal 2:**
```bash
cd E:\ianae-final\orchestra\daemon
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
  Log:          E:\ianae-final\orchestra\daemon\logs\arquitecto.log
============================================================

[OK] System prompt: 3842 chars
[OK] docs-service: {'status': 'ok', 'service': 'docs-service-ianae', 'port': 25500}
[OK] API Anthropic: conexion OK

[LOOP] Cada 60s. Ctrl+C para parar.

.
```

Si hay errores:
- `[ERROR] No existe: ...arquitecto_system.md` → verificar que el prompt existe
- `[ERROR] docs-service no responde` → arrancar docs-service primero (Terminal 1)
- `[ERROR] ANTHROPIC_API_KEY no configurada` → configurar variable de entorno (Paso 3)
- `[ERROR] API Anthropic: ...` → verificar que la API key es válida

## Paso 6: Arrancar watchdog

**Terminal 3:**
```bash
cd E:\ianae-final\orchestra\daemon
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

.
```

## Paso 7: Probar Ciclo Completo

**Terminal 4 (o misma terminal donde verificaste health):**

Publicar orden de prueba:

```bash
curl -X POST http://localhost:25500/api/v1/docs ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"TEST: Orden de prueba\",\"content\":\"# Orden de prueba\n\nVerificar que el sistema funciona.\n\n## Tarea\nLeer este mensaje y reportar que lo recibiste.\n\n## Criterio de hecho\n- Reporte publicado confirmando recepción\",\"category\":\"especificaciones\",\"author\":\"lucas\",\"tags\":[\"worker-core\"],\"priority\":\"alta\",\"status\":\"pending\"}"
```

**Nota:** En Windows CMD, el comando debe estar en una sola línea. En PowerShell o bash, usa `\` al final de cada línea para continuar.

### Observar el ciclo:

1. **Terminal 2 (daemon)** - En max 60s:
   ```
   [ALERTA] 1 doc(s) nuevo(s):
      -> [especificaciones] TEST: Orden de prueba (de lucas)
   [IA] Consultando Arquitecto IA...
   ORDEN: ... -> ['worker-core']
   ```

2. **Terminal 3 (watchdog)** - En max 30s después:
   ```
   ============================================================
     NUEVA ORDEN PARA WORKER-CORE
     15:42:30
   ============================================================
     Titulo: ...
     ID: 2

   --- CONTENIDO ---
   ...
   --- FIN CONTENIDO ---

   [ACCION] Lee la orden anterior y ejecutala.
   [ACCION] Al terminar, reporta con:
     python worker_report.py worker-core "Titulo del reporte" reporte.md
   ```

3. **¡Ciclo funcionando!** El watchdog mostró la orden automáticamente.

## Paso 8: Reportar desde Worker

Cuando completes una tarea:

```bash
cd E:\ianae-final\orchestra\daemon

# Opción 1: Con archivo
echo "# Reporte\n\nTarea completada exitosamente." > reporte.md
python worker_report.py worker-core "Tarea de prueba completada" reporte.md

# Opción 2: Sin archivo (contenido desde stdin)
echo "# Reporte\n\nTarea completada." | python worker_report.py worker-core "Tarea completada"

# Opción 3: Publicar duda
python worker_report.py worker-core "DUDA: ¿Usar float32 o float64?" --duda
```

El daemon detectará el reporte → API decidirá siguiente paso → watchdog mostrará nueva orden.

## Verificación Final

Sistema funcionando cuando:

- ✅ docs-service responde en puerto 25500
- ✅ daemon arranca sin errores y entra en loop
- ✅ watchdog arranca y hace polling
- ✅ Ciclo completo: orden manual → daemon detecta → API responde → watchdog muestra
- ✅ Workers pueden publicar reportes

## Próximos Pasos

Una vez verificado el sistema:

1. **Terminal 4**: Abrir Claude Code en `E:\ianae-final`
2. **Publicar primera orden real**: Analizar nucleo.py y planificar refactorización
3. **Observar**: Daemon coordina, watchdog muestra órdenes, workers ejecutan
4. **Lucas toma café** ☕ y solo interviene para aprobar merges

## Comandos Útiles

### Ver estado del sistema
```bash
# Salud docs-service
curl http://localhost:25500/health

# Snapshot del proyecto
curl http://localhost:25500/api/v1/context/snapshot

# Pendientes de un worker
curl http://localhost:25500/api/v1/worker/worker-core/pendientes

# Documentos recientes
curl "http://localhost:25500/api/v1/notifications/since?t=2025-02-10T00:00:00Z"

# Listar todos los docs
curl http://localhost:25500/api/v1/docs
```

### Detener el sistema
```
Terminal 1 (docs-service): Ctrl+C
Terminal 2 (daemon): Ctrl+C
Terminal 3 (watchdog): Ctrl+C
```

## Troubleshooting

Ver `orchestra/README.md` sección "Troubleshooting" para problemas comunes y soluciones.

## Logs

- **daemon**: `E:\ianae-final\orchestra\daemon\logs\arquitecto.log`
- **docs-service**: salida en terminal
- **watchdog**: salida en terminal

## Documentación

- `orchestra/README.md` - Documentación completa
- `orchestra/IANAE_ORCHESTRA_DESPLIEGUE_COMPLETO.md` - Especificación técnica completa
- `orchestra.yaml` - Configuración del proyecto
- `orchestra/daemon/prompts/` - Comportamiento de cada componente

---

**¡Sistema listo para uso!** 🚀
