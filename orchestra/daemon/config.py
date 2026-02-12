"""
Configuracion del daemon Arquitecto para IANAE.
"""

import os

# docs-service IANAE
DOCS_SERVICE_URL = "http://localhost:25500"

# Proveedores LLM (orden = prioridad, mas barato primero)
LLM_PROVIDERS = [
    {
        "name": "deepseek",
        "endpoint": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    {
        "name": "qwen",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    {
        "name": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
]

# API legacy (para compatibilidad)
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Tokens y limites
MAX_TOKENS = 2048

# Daemon
CHECK_INTERVAL = 10
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "arquitecto.log")
SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompts", "arquitecto_system.md")

# Filtros
IGNORE_TYPES = ["info", "arranque"]
IGNORE_AUTHORS = ["arquitecto-daemon"]

# Seguridad
MAX_DAILY_API_CALLS = 50

# Workers validos
VALID_WORKERS = ["worker-core", "worker-nlp", "worker-infra", "worker-ui"]

# Dependencias entre workers
WORKER_DEPENDENCIES = {
    "worker-core": [],
    "worker-nlp": ["worker-core"],
    "worker-infra": [],
    "worker-ui": ["worker-core", "worker-infra"],
}

# Cache de respuestas
CACHE_TTL_SECONDS = 3600
CACHE_MAX_ENTRIES = 500

# Worker executor
WORKER_CHECK_INTERVAL = 15  # segundos entre polls
WORKER_MAX_TOKENS = 8192    # tokens para generar codigo (max DeepSeek)
WORKER_MAX_FILES = 5        # max archivos por orden
WORKER_MAX_RETRIES = 2      # reintentos por orden antes de marcar blocked
WORKER_RETRY_DELAY = 10     # segundos entre reintentos
WORKER_CHUNK_PLAN_TOKENS = 2048    # tokens para planning call (chunked generation)
WORKER_CHUNK_FILE_TOKENS = 6000    # tokens para cada file generation call (chunked, DeepSeek)
WORKER_ANTHROPIC_FILE_TOKENS = 16000  # tokens para file generation con Anthropic (mas capacidad)

# Seleccion dinamica de provider:
# - Tareas simples (1-2 archivos nuevos): DeepSeek (barato, 6000 tokens/archivo)
# - Tareas complejas (3+ archivos, o modificar archivos grandes): Anthropic (16000 tokens/archivo)
WORKER_COMPLEXITY_THRESHOLD_FILES = 3  # >= este numero de archivos = complejo
WORKER_LARGE_FILE_LINES = 200          # archivos con mas lineas = complejos

# Scopes de workers (que archivos puede tocar cada uno)
WORKER_SCOPES = {
    "worker-core": {
        "paths": ["src/core/", "tests/core/"],
        "test_cmd": "python -m pytest tests/core/ -q",
    },
    "worker-infra": {
        "paths": ["tests/", "docker/", "config/", "pyproject.toml"],
        "test_cmd": "python -m pytest tests/ -q",
    },
    "worker-nlp": {
        "paths": ["src/nlp/", "tests/"],
        "test_cmd": "python -m pytest tests/ -q",
    },
    "worker-ui": {
        "paths": ["src/ui/", "src/web/"],
        "test_cmd": "python -m pytest tests/ -q",
    },
}
