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
CHECK_INTERVAL = 300
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
