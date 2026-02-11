"""
Tests para response_cache.py — Cache de respuestas LLM.

Verifica:
- Cache hit para contextos identicos
- Cache miss para contextos diferentes
- TTL expira correctamente
- Limite de entradas se respeta
- Stats reportan correctamente
"""

import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "orchestra", "daemon"))

from response_cache import ResponseCache


@pytest.fixture
def cache(tmp_path):
    """Cache con DB temporal y TTL corto para tests."""
    db_path = str(tmp_path / "test_cache.db")
    return ResponseCache(ttl_seconds=60, max_entries=10, db_path=db_path)


@pytest.fixture
def short_ttl_cache(tmp_path):
    """Cache con TTL de 1 segundo para tests de expiracion."""
    db_path = str(tmp_path / "test_cache_ttl.db")
    return ResponseCache(ttl_seconds=1, max_entries=10, db_path=db_path)


class TestCacheBasics:
    def test_put_and_get(self, cache):
        system = "Eres un arquitecto"
        messages = [{"role": "user", "content": "hola"}]

        cache.put(system, messages, '{"action": "none"}', "deepseek")

        result = cache.get(system, messages)
        assert result is not None
        assert result["text"] == '{"action": "none"}'
        assert result["provider"] == "deepseek"

    def test_miss_on_different_context(self, cache):
        system = "Eres un arquitecto"
        messages1 = [{"role": "user", "content": "contexto A"}]
        messages2 = [{"role": "user", "content": "contexto B"}]

        cache.put(system, messages1, "respuesta A", "deepseek")

        result = cache.get(system, messages2)
        assert result is None

    def test_miss_on_empty_cache(self, cache):
        result = cache.get("system", [{"role": "user", "content": "test"}])
        assert result is None

    def test_overwrite_existing(self, cache):
        system = "sys"
        messages = [{"role": "user", "content": "test"}]

        cache.put(system, messages, "respuesta 1", "deepseek")
        cache.put(system, messages, "respuesta 2", "qwen")

        result = cache.get(system, messages)
        assert result["text"] == "respuesta 2"
        assert result["provider"] == "qwen"


class TestCacheTTL:
    def test_expired_entry_returns_none(self, short_ttl_cache):
        system = "sys"
        messages = [{"role": "user", "content": "test"}]

        short_ttl_cache.put(system, messages, "respuesta", "deepseek")

        # Verificar que esta disponible
        result = short_ttl_cache.get(system, messages)
        assert result is not None

        # Esperar que expire
        time.sleep(1.1)

        result = short_ttl_cache.get(system, messages)
        assert result is None


class TestCacheLimits:
    def test_enforce_max_entries(self, tmp_path):
        db_path = str(tmp_path / "test_limit.db")
        cache = ResponseCache(ttl_seconds=60, max_entries=3, db_path=db_path)

        # Insertar 5 entradas
        for i in range(5):
            cache.put("sys", [{"role": "user", "content": f"msg-{i}"}], f"resp-{i}", "test")

        stats = cache.stats()
        assert stats["total_entries"] <= 3

    def test_oldest_entries_evicted(self, tmp_path):
        db_path = str(tmp_path / "test_evict.db")
        cache = ResponseCache(ttl_seconds=60, max_entries=2, db_path=db_path)

        cache.put("sys", [{"role": "user", "content": "old"}], "old-resp", "test")
        time.sleep(0.01)  # Asegurar diferente timestamp
        cache.put("sys", [{"role": "user", "content": "mid"}], "mid-resp", "test")
        time.sleep(0.01)
        cache.put("sys", [{"role": "user", "content": "new"}], "new-resp", "test")

        # "old" deberia haber sido eliminado
        assert cache.get("sys", [{"role": "user", "content": "old"}]) is None
        # "new" deberia estar
        assert cache.get("sys", [{"role": "user", "content": "new"}]) is not None


class TestCacheStats:
    def test_stats_empty(self, cache):
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["max_entries"] == 10
        assert stats["ttl_seconds"] == 60

    def test_stats_after_inserts(self, cache):
        for i in range(3):
            cache.put("sys", [{"role": "user", "content": f"msg-{i}"}], f"resp-{i}", "test")

        stats = cache.stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3


class TestCacheHash:
    def test_same_content_same_hash(self, cache):
        """Mensajes identicos deben producir el mismo hash."""
        system = "sys"
        messages = [{"role": "user", "content": "test"}]

        h1 = ResponseCache._hash_context(system, messages)
        h2 = ResponseCache._hash_context(system, messages)
        assert h1 == h2

    def test_different_content_different_hash(self, cache):
        h1 = ResponseCache._hash_context("sys", [{"role": "user", "content": "a"}])
        h2 = ResponseCache._hash_context("sys", [{"role": "user", "content": "b"}])
        assert h1 != h2

    def test_different_system_different_hash(self, cache):
        messages = [{"role": "user", "content": "test"}]
        h1 = ResponseCache._hash_context("system A", messages)
        h2 = ResponseCache._hash_context("system B", messages)
        assert h1 != h2
