"""
Ianae v3 - Configuracion
"""
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent
DIARIO_DIR = BASE_DIR / "diario"
MEMORIA_DIR = BASE_DIR / "memoria"
DATOS_DIR = BASE_DIR / "datos"
ESTADO_FILE = MEMORIA_DIR / "mente.json"

# Ciclo autonomo
CICLO_INTERVALO_SEG = 180       # cada 3 minutos
CICLO_PAUSA_NOCHE = True        # pausa de 01:00 a 07:00
CICLO_NOCHE_INICIO = 1
CICLO_NOCHE_FIN = 7

# Mente
VECTOR_DIM = 32                 # dimensiones del vector de concepto
FUERZA_INICIAL = 0.5            # fuerza de un concepto nuevo
DECAY_RATE = 0.005              # decaimiento por ciclo sin uso
UMBRAL_OLVIDO = 0.02            # debajo de esto, se olvida
CURIOSIDAD_BASE = 0.3           # curiosidad inicial
MAX_CONCEPTOS = 500             # limite para no explotar
CONEXION_MIN = 0.05             # peso minimo de conexion

# Observacion
FUENTES_OBSERVACION = [
    "archivos",         # lee archivos del servidor
    "logs",             # logs del sistema
    "tiempo",           # hora, dia, estacion
    "clima",            # clima actual
    "sistema",          # estado del servidor (cpu, mem, disco)
    "ruido",            # input aleatorio (creatividad pura)
    "propiocepcion",    # se observa a si misma
    "wikipedia",        # explora Wikipedia por curiosidad
]

# Telegram (voz de Ianae)
TELEGRAM_BOT_TOKEN = "8591374624:AAFlKsiRbb8MHFJTaBkkag85JZ2Qp4XjWQ0"
TELEGRAM_CHAT_ID = "1244114483"
HABLAR_COOLDOWN_SEG = 1800          # minimo 30 min entre mensajes

# LLM (sentidos)
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"
LLM_TIMEOUT = 30

# Asegurar directorios
for d in [DIARIO_DIR, MEMORIA_DIR, DATOS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
