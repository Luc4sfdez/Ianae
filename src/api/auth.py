"""Autenticacion y rate limiting para la API IANAE."""
import os
import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader


# --- API Key validation ---

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Keys validas: desde variable de entorno o default para desarrollo
_VALID_KEYS = set()


def _load_keys():
    global _VALID_KEYS
    env_keys = os.environ.get("IANAE_API_KEYS", "")
    if env_keys:
        _VALID_KEYS = {k.strip() for k in env_keys.split(",") if k.strip()}


_load_keys()


def get_valid_keys():
    """Retorna el set de keys validas (para testing)."""
    return _VALID_KEYS


def add_api_key(key: str):
    """Agrega una API key valida en runtime."""
    _VALID_KEYS.add(key)


def remove_api_key(key: str):
    """Elimina una API key."""
    _VALID_KEYS.discard(key)


def is_auth_enabled() -> bool:
    """Auth esta habilitada solo si hay keys configuradas."""
    return len(_VALID_KEYS) > 0


async def validate_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)):
    """
    Dependency de FastAPI para validar API key.

    Si no hay keys configuradas (desarrollo), permite acceso libre.
    Si hay keys configuradas, requiere header X-API-Key valido.
    """
    if not is_auth_enabled():
        return None  # Sin auth configurada, acceso libre

    if not api_key:
        raise HTTPException(status_code=401, detail="API key requerida (header X-API-Key)")

    if api_key not in _VALID_KEYS:
        raise HTTPException(status_code=403, detail="API key invalida")

    return api_key


# --- Rate Limiting ---

class RateLimiter:
    """
    Rate limiter simple in-memory por IP y por API key.

    Usa ventana deslizante por minuto.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._requests = defaultdict(list)  # key -> [timestamps]

    def _cleanup(self, key: str, now: float):
        """Elimina timestamps mas viejos que 60s."""
        cutoff = now - 60.0
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, key: str) -> bool:
        """Retorna True si la request esta permitida."""
        now = time.time()
        self._cleanup(key, now)

        if len(self._requests[key]) >= self.rpm:
            return False

        self._requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        """Requests restantes en la ventana actual."""
        now = time.time()
        self._cleanup(key, now)
        return max(0, self.rpm - len(self._requests[key]))

    def reset(self):
        """Limpia todo el estado (para tests)."""
        self._requests.clear()


# Instancia global
rate_limiter = RateLimiter(requests_per_minute=60)


async def check_rate_limit(request: Request):
    """Dependency de FastAPI para rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"ip:{client_ip}"

    if not rate_limiter.check(key):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit excedido ({rate_limiter.rpm} requests/min)"
        )
