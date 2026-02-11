"""
Cache de respuestas LLM para evitar llamadas duplicadas.

Usa SQLite local con TTL y limpieza automatica.
Contextos identicos (mismo hash SHA-256) devuelven respuesta cacheada.

Uso:
    from response_cache import ResponseCache

    cache = ResponseCache(ttl_seconds=3600, max_entries=500)
    cached = cache.get(system_prompt, user_message)
    if cached:
        print("Cache hit:", cached)
    else:
        response = llm.chat(...)
        cache.put(system_prompt, user_message, response.text, response.provider)
"""

import os
import hashlib
import json
import sqlite3
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("response_cache")

# Directorio del cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
DEFAULT_DB_PATH = os.path.join(CACHE_DIR, "response_cache.db")


class ResponseCache:
    """
    Cache de respuestas LLM basado en SQLite.

    - Hash SHA-256 del contexto (system + messages) como clave
    - TTL configurable (default 1 hora)
    - Limite de entradas con limpieza automatica
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_entries: int = 500,
        db_path: str = DEFAULT_DB_PATH,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.db_path = db_path

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()
        self._cleanup_expired()

    def _init_db(self):
        """Crea la tabla de cache si no existe."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    context_hash TEXT PRIMARY KEY,
                    response_text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON response_cache(created_at)
            """)

    def _connect(self) -> sqlite3.Connection:
        """Conecta a SQLite."""
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _hash_context(system: str, messages: list) -> str:
        """Genera hash SHA-256 del contexto (system + messages)."""
        content = json.dumps({"system": system, "messages": messages}, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, system: str, messages: list) -> Optional[Dict[str, Any]]:
        """
        Busca respuesta en cache.

        Returns:
            Dict con 'text' y 'provider' si hay hit, None si miss.
        """
        context_hash = self._hash_context(system, messages)
        now = time.time()
        min_time = now - self.ttl_seconds

        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_text, provider, created_at "
                "FROM response_cache "
                "WHERE context_hash = ? AND created_at > ?",
                (context_hash, min_time),
            ).fetchone()

        if row:
            age = int(now - row[2])
            logger.info(f"Cache HIT (age={age}s, provider={row[1]})")
            return {"text": row[0], "provider": row[1]}

        return None

    def put(self, system: str, messages: list, response_text: str, provider: str):
        """Almacena respuesta en cache."""
        context_hash = self._hash_context(system, messages)
        now = time.time()

        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO response_cache "
                "(context_hash, response_text, provider, created_at) "
                "VALUES (?, ?, ?, ?)",
                (context_hash, response_text, provider, now),
            )

        logger.info(f"Cache PUT (provider={provider})")

        # Limpieza si excede limite
        self._enforce_limit()

    def _cleanup_expired(self):
        """Elimina entradas expiradas."""
        min_time = time.time() - self.ttl_seconds
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM response_cache WHERE created_at < ?",
                (min_time,),
            )
            if result.rowcount > 0:
                logger.info(f"Cache: {result.rowcount} entradas expiradas eliminadas")

    def _enforce_limit(self):
        """Si excede max_entries, elimina las mas antiguas."""
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM response_cache"
            ).fetchone()[0]

            if count > self.max_entries:
                excess = count - self.max_entries
                conn.execute(
                    "DELETE FROM response_cache WHERE context_hash IN ("
                    "  SELECT context_hash FROM response_cache "
                    "  ORDER BY created_at ASC LIMIT ?"
                    ")",
                    (excess,),
                )
                logger.info(f"Cache: {excess} entradas antiguas eliminadas (limite={self.max_entries})")

    def stats(self) -> Dict[str, Any]:
        """Estadisticas del cache."""
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM response_cache"
            ).fetchone()[0]
            valid = conn.execute(
                "SELECT COUNT(*) FROM response_cache WHERE created_at > ?",
                (time.time() - self.ttl_seconds,),
            ).fetchone()[0]

        return {
            "total_entries": count,
            "valid_entries": valid,
            "expired_entries": count - valid,
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
        }
