"""
Tests para llm_provider.py — Abstraccion multi-proveedor LLM.

Verifica:
- ProviderChain hace fallback cuando un provider falla
- Solo providers con API key se incluyen
- LLMResponse contiene datos correctos
- Error si no hay providers disponibles
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Agregar path del daemon
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "orchestra", "daemon"))

from llm_provider import (
    LLMResponse,
    DeepSeekProvider,
    QwenProvider,
    AnthropicProvider,
    ProviderChain,
    PROVIDER_CLASSES,
)


# ============================================
# Tests de LLMResponse
# ============================================

class TestLLMResponse:
    def test_dataclass_fields(self):
        r = LLMResponse(
            text="hola",
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=100,
            output_tokens=50,
        )
        assert r.text == "hola"
        assert r.provider == "deepseek"
        assert r.model == "deepseek-chat"
        assert r.input_tokens == 100
        assert r.output_tokens == 50


# ============================================
# Tests de Provider availability
# ============================================

class TestProviderAvailability:
    def test_provider_available_with_key(self):
        with patch.dict(os.environ, {"TEST_KEY": "sk-123"}):
            p = DeepSeekProvider({"api_key_env": "TEST_KEY"})
            assert p.available is True

    def test_provider_unavailable_without_key(self):
        env = os.environ.copy()
        env.pop("MISSING_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            p = DeepSeekProvider({"api_key_env": "MISSING_KEY"})
            assert p.available is False

    def test_deepseek_defaults(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            p = DeepSeekProvider({"api_key_env": "DEEPSEEK_API_KEY"})
            assert p.name == "deepseek"
            assert p.model == "deepseek-chat"

    def test_qwen_defaults(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test"}):
            p = QwenProvider({"api_key_env": "DASHSCOPE_API_KEY"})
            assert p.name == "qwen"
            assert p.model == "qwen-plus"

    def test_anthropic_defaults(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            p = AnthropicProvider({"api_key_env": "ANTHROPIC_API_KEY"})
            assert p.name == "anthropic"
            assert p.model == "claude-sonnet-4-20250514"


# ============================================
# Tests de ProviderChain
# ============================================

class TestProviderChain:
    def _make_config(self, available_keys):
        """Crea config con API keys controladas."""
        configs = []
        mapping = {
            "deepseek": "DEEPSEEK_API_KEY",
            "qwen": "DASHSCOPE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        for name in ["deepseek", "qwen", "anthropic"]:
            env_var = mapping[name]
            configs.append({
                "name": name,
                "api_key_env": env_var,
                "model": "test-model",
            })
        return configs, {k: "sk-test" for k in available_keys}

    def test_chain_with_all_providers(self):
        configs, env = self._make_config(
            ["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "ANTHROPIC_API_KEY"]
        )
        with patch.dict(os.environ, env, clear=True):
            chain = ProviderChain(configs)
            assert len(chain.providers) == 3
            assert chain.available_providers == ["deepseek", "qwen", "anthropic"]

    def test_chain_with_single_provider(self):
        configs, env = self._make_config(["ANTHROPIC_API_KEY"])
        with patch.dict(os.environ, env, clear=True):
            chain = ProviderChain(configs)
            assert len(chain.providers) == 1
            assert chain.available_providers == ["anthropic"]

    def test_chain_no_providers_raises(self):
        configs, _ = self._make_config([])
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="No hay providers LLM disponibles"):
                ProviderChain(configs)

    def test_fallback_on_first_provider_failure(self):
        """Si DeepSeek falla, debe usar Qwen."""
        configs, env = self._make_config(
            ["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"]
        )
        with patch.dict(os.environ, env, clear=True):
            chain = ProviderChain(configs)

            # Mock: primer provider falla, segundo exito
            expected = LLMResponse(
                text='{"action": "none"}',
                provider="qwen",
                model="test-model",
                input_tokens=100,
                output_tokens=50,
            )
            chain.providers[0].chat = MagicMock(
                side_effect=Exception("DeepSeek timeout")
            )
            chain.providers[1].chat = MagicMock(return_value=expected)

            result = chain.chat(
                system="test",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=100,
            )

            assert result.provider == "qwen"
            assert result.text == '{"action": "none"}'
            chain.providers[0].chat.assert_called_once()
            chain.providers[1].chat.assert_called_once()

    def test_all_providers_fail_raises(self):
        """Si todos fallan, lanza RuntimeError con ultimo error."""
        configs, env = self._make_config(["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"])
        with patch.dict(os.environ, env, clear=True):
            chain = ProviderChain(configs)

            chain.providers[0].chat = MagicMock(
                side_effect=Exception("DeepSeek down")
            )
            chain.providers[1].chat = MagicMock(
                side_effect=Exception("Qwen down")
            )

            with pytest.raises(RuntimeError, match="Todos los providers fallaron"):
                chain.chat(
                    system="test",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=100,
                )

    def test_first_provider_success_no_fallback(self):
        """Si el primer provider funciona, no toca los demas."""
        configs, env = self._make_config(
            ["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"]
        )
        with patch.dict(os.environ, env, clear=True):
            chain = ProviderChain(configs)

            expected = LLMResponse(
                text="ok",
                provider="deepseek",
                model="test-model",
                input_tokens=50,
                output_tokens=25,
            )
            chain.providers[0].chat = MagicMock(return_value=expected)
            chain.providers[1].chat = MagicMock()

            result = chain.chat(
                system="test",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=100,
            )

            assert result.provider == "deepseek"
            chain.providers[0].chat.assert_called_once()
            chain.providers[1].chat.assert_not_called()

    def test_unknown_provider_skipped(self):
        """Providers desconocidos se ignoran sin error."""
        configs = [
            {"name": "unknown_provider", "api_key_env": "FAKE_KEY"},
            {"name": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"},
        ]
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
            chain = ProviderChain(configs)
            assert chain.available_providers == ["deepseek"]
