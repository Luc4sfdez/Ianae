# INFORME DE REORGANIZACIÓN — IANAE

**Fecha:** 2026-02-10 13:07:45
**Archivos copiados:** 180
**Tamaño total:** 2.1 MB

## Resumen por categoría

| Categoría | Archivos | Tamaño |
|-----------|----------|--------|
| config | 5 | 53.9 KB |
| core | 10 | 215.6 KB |
| data | 2 | 2.8 KB |
| docs | 16 | 70.1 KB |
| framework | 56 | 284.3 KB |
| historico | 56 | 990.4 KB |
| llm | 7 | 48.8 KB |
| memory | 12 | 210.8 KB |
| tests | 7 | 144.6 KB |
| web | 9 | 126.3 KB |

## Archivos por categoría

### config (5 archivos)

- `.gitignore`
- `README.md`
- `config\conceptos_lucas_poblado.json`
- `config\ianae_config.json`
- `requirements.txt`

### core (10 archivos)

- `src\core\ciclos.py`
- `src\core\conceptos.py`
- `src\core\config.py`
- `src\core\emergente.py`
- `src\core\emergente_memory.py`
- `src\core\emergente_original.py`
- `src\core\nucleo.py`
- `src\core\nucleo_v2.py`
- `src\core\optimizador.py`
- `src\core\optimizador_complemento.py`

### data (2 archivos)

- `data/conversaciones_indice.txt`
- `data\memory_summary.json`

### docs (16 archivos)

- `docs\README_APP.md`
- `docs\README_IANAE.md`
- `docs\README_root.md`
- `docs\documentacion_consolidada.md`
- `docs\estado_actual.md`
- `docs\estado_documentacion.md`
- `docs\notas\analisis_limpio.md`
- `docs\notas\resumen_sesion.md`
- `docs\notas\session_handoff.md`
- `docs\roadmap.md`
- `docs\tech\consultas_inteligentes.md`
- `docs\tech\deep_content_analysis.md`
- `docs\tech\emergente.md`
- `docs\tech\emergente_lucas.md`
- `docs\tech\memory_system.md`
- `docs\tech\procesamiento_conversaciones.md`

### framework (56 archivos)

- `src\framework\auto_detector.py`
- `src\framework\core\__init__.py`
- `src\framework\core\concepts.py`
- `src\framework\core\config.py`
- `src\framework\core\database.py`
- `src\framework\core\deduplicator.py`
- `src\framework\core\exceptions.py`
- `src\framework\core\manager.py`
- `src\framework\core\patterns.py`
- `src\framework\core\plugins\__init__.py`
- `src\framework\core\plugins\base_plugin.py`
- `src\framework\core\plugins\hooks.py`
- `src\framework\core\plugins\plugin_manager.py`
- `src\framework\core\relationships.py`
- `src\framework\core\search.py`
- `src\framework\core\summarizer.py`
- `src\framework\demo.py`
- `src\framework\install.py`
- `src\framework\llm\__init__.py`
- `src\framework\llm\client.py`
- `src\framework\llm\context_builder.py`
- `src\framework\llm\prompts\__init__.py`
- `src\framework\llm\prompts\analysis_prompts.py`
- `src\framework\llm\prompts\chat_prompts.py`
- `src\framework\llm\prompts\summary_prompts.py`
- `src\framework\llm\prompts\system_prompts.py`
- `src\framework\llm\providers\__init__.py`
- `src\framework\llm\providers\anthropic.py`
- `src\framework\llm\providers\base_provider.py`
- `src\framework\llm\providers\lmstudio.py`
- `src\framework\llm\providers\local_models.py`
- `src\framework\llm\providers\ollama.py`
- `src\framework\llm\providers\openai.py`
- `src\framework\llm\response_parser.py`
- `src\framework\pipeline\__init__.py`
- `src\framework\pipeline\middleware\__init__.py`
- `src\framework\pipeline\middleware\caching_middleware.py`
- `src\framework\pipeline\middleware\error_middleware.py`
- `src\framework\pipeline\middleware\logging_middleware.py`
- `src\framework\pipeline\middleware\rate_limit_middleware.py`
- `src\framework\pipeline\orchestrator.py`
- `src\framework\pipeline\stages\__init__.py`
- `src\framework\pipeline\stages\analysis.py`
- `src\framework\pipeline\stages\enrichment.py`
- `src\framework\pipeline\stages\ingestion.py`
- `src\framework\pipeline\stages\processing.py`
- `src\framework\pipeline\stages\storage.py`
- `src\framework\pipeline\task_queue.py`
- `src\framework\processors\__init__.py`
- `src\framework\processors\ai_platforms\chatgpt.py`
- `src\framework\processors\ai_platforms\claude.py`
- `src\framework\processors\ai_platforms\cline.py`
- `src\framework\processors\auto_detector.py`
- `src\framework\processors\base.py`
- `src\framework\web\app.py`
- `src\framework\webapp.py`

### historico (56 archivos)

- `versiones_anteriores\app_github_original\IANAE\ianae_visual.py`
- `versiones_anteriores\app_github_original\README.md`
- `versiones_anteriores\app_github_original\__init__.py`
- `versiones_anteriores\app_github_original\datos\README.txt`
- `versiones_anteriores\app_github_original\datos\temp\conceptos_apartados.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_ciclo_100.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_ciclo_20.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_ciclo_40.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_ciclo_60.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_ciclo_80.json`
- `versiones_anteriores\app_github_original\datos\temp\estado_inicial.json`
- `versiones_anteriores\app_github_original\datos\temp\informe_sistema.json`
- `versiones_anteriores\app_github_original\datos\temp\metricas_rendimiento.json`
- `versiones_anteriores\app_github_original\ejemplos\basicos.py`
- `versiones_anteriores\app_github_original\ejemplos\imagenes\README.txt`
- `versiones_anteriores\app_github_original\ejemplos\orientacion.py`
- `versiones_anteriores\app_github_original\ejemplos\texto.py`
- `versiones_anteriores\app_github_original\ejemplos\visualizacion.py`
- `versiones_anteriores\app_github_original\ianae.egg-info\SOURCES.txt`
- `versiones_anteriores\app_github_original\ianae.egg-info\dependency_links.txt`
- `versiones_anteriores\app_github_original\ianae.egg-info\requires.txt`
- `versiones_anteriores\app_github_original\ianae.egg-info\top_level.txt`
- `versiones_anteriores\app_github_original\ianae_optimizador.py`
- `versiones_anteriores\app_github_original\optimizador-ianae.py`
- `versiones_anteriores\app_github_original\requirements.txt`
- `versiones_anteriores\monoliticos\ianae_complete_v3.py`
- `versiones_anteriores\monoliticos\ianae_complete_v3_NOVA.py`
- `versiones_anteriores\monoliticos\ianae_completo_funcional.py`
- `versiones_anteriores\monoliticos\ianae_final_working.py`
- `versiones_anteriores\ver00_original\ciclos.py`
- `versiones_anteriores\ver00_original\emergente.py`
- `versiones_anteriores\ver00_original\experimento.py`
- `versiones_anteriores\ver00_original\main.py`
- `versiones_anteriores\ver00_original\nucleo.py`
- `versiones_anteriores\ver00_original\optimizador.py`
- `versiones_anteriores\ver00_original\optimizador_complemento.py`
- `versiones_anteriores\ver00_original\setup.py`
- `versiones_anteriores\ver00_original\test_dependencias.py`
- `versiones_anteriores\ver00_original\test_ianae.py`
- `versiones_anteriores\ver01_memoria\core\config\ianae_config.json`
- `versiones_anteriores\ver01_memoria\core\config\lm_studio_config.json`
- `versiones_anteriores\ver01_memoria\core\personality\memory_bank_initial.txt`
- `versiones_anteriores\ver01_memoria\core\personality\system_prompt_file.txt`
- `versiones_anteriores\ver01_memoria\deep_content_analysis.py`
- `versiones_anteriores\ver01_memoria\diagnostic_json.py`
- `versiones_anteriores\ver01_memoria\ianae_consultas_inteligentes.py`
- `versiones_anteriores\ver01_memoria\ianae_memory_system.py`
- `versiones_anteriores\ver01_memoria\inspect_message_structure.py`
- `versiones_anteriores\ver01_memoria\main.py`
- `versiones_anteriores\ver01_memoria\nucleo.py`
- `versiones_anteriores\ver01_memoria\nucleo_types.py`
- `versiones_anteriores\ver01_memoria\rag_system\chat_con_memoria.py`
- `versiones_anteriores\ver01_memoria\rag_system\config.json`
- `versiones_anteriores\ver01_memoria\rag_system\logs\rag_log_20250527.txt`
- `versiones_anteriores\ver01_memoria\rag_system\rag_server.py`
- `versiones_anteriores\ver01_memoria\rag_system\requirements.txt`

### llm (7 archivos)

- `src\llm\connector.py`
- `src\llm\integration.py`
- `src\llm\rag\chat_con_memoria.py`
- `src\llm\rag\config.json`
- `src\llm\rag\logs\rag_log_20250527.txt`
- `src\llm\rag\rag_server.py`
- `src\llm\rag\requirements.txt`

### memory (12 archivos)

- `src\memory\connector.py`
- `src\memory\connector_v2.py`
- `src\memory\consultas_inteligentes.py`
- `src\memory\database.py`
- `src\memory\extractor_directo.py`
- `src\memory\extractor_potente.py`
- `src\memory\generador_resumenes.py`
- `src\memory\lucas_memory.py`
- `src\memory\memory_final.py`
- `src\memory\memory_fixed.py`
- `src\memory\memory_system.py`
- `src\memory\memory_working.py`

### tests (7 archivos)

- `tests\core\test_ianae.py`
- `tests\core\test_ianae_lucas.py`
- `tests\core\test_ianae_original.py`
- `tests\framework\integration\test_ianae_completo.py`
- `tests\framework\integration\test_ianae_completo_r.py`
- `tests\framework\test_ianae.py`
- `tests\framework\test_sistema_completo.py`

### web (9 archivos)

- `src\web\api_endpoint.py`
- `src\web\ianae_server.py`
- `src\web\simple_server.py`
- `src\web\static\css\style.css`
- `src\web\static\js\chat.js`
- `src\web\templates\chat.html`
- `src\web\webapp.py`
- `src\web\webapp_complete.py`
- `src\web\webapp_original.py`

## Archivos no encontrados

- No existe: E:\ianae-main-20260210\ianae-architecture-doc.md
- No existe: E:\ianae-main-20260210\ianae-documento.md
- No existe: E:\ianae-main-20260210\ianae-integration-paper.md
- No existe: E:\ianae-main-20260210\ianae-llm-alexa-integration.md
- No existe: E:\ianae-main-20260210\ianae-nlp-integration.md
- No existe: E:\ianae-main-20260210\ianae-workflows-doc.md

---
*Generado por reorganizar_ianae.py — 2026-02-10 13:07:45*