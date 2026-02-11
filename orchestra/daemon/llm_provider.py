"""
Abstraccion multi-proveedor LLM para IANAE.

Soporta DeepSeek, Qwen y Anthropic con cadena de fallback automatico.
Orden por defecto: DeepSeek (mas barato) -> Qwen -> Anthropic (fallback caro).

Uso:
    from llm_provider import ProviderChain
    from config import LLM_PROVIDERS, MAX_TOKENS

    chain = ProviderChain(LLM_PROVIDERS)
    response = chain.chat(system="...", messages=[...], max_tokens=2048)
    print(response.text, response.provider, response.input_tokens)
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger("llm_provider")


@dataclass
class LLMResponse:
    """Respuesta unificada de cualquier proveedor LLM."""
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider:
    """Interfaz base para proveedores LLM."""

    name: str = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model", "")
        self.api_key = os.environ.get(config.get("api_key_env", ""), "")

    @property
    def available(self) -> bool:
        """True si el provider tiene API key configurada."""
        return bool(self.api_key)

    def chat(self, system: str, messages: List[Dict], max_tokens: int) -> LLMResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider para APIs compatibles con OpenAI (DeepSeek, Qwen, etc).
    Usa el SDK openai que maneja streaming, errores y reintentos.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "openai-compatible")
        self.endpoint = config.get("endpoint", "")

    def chat(self, system: str, messages: List[Dict], max_tokens: int) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.endpoint,
        )

        # Construir mensajes en formato OpenAI
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for msg in messages:
            oai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        response = client.chat.completions.create(
            model=self.model,
            messages=oai_messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek Chat (V3) - ~$0.27/1M input, $1.10/1M output."""

    def __init__(self, config: Dict[str, Any]):
        config.setdefault("endpoint", "https://api.deepseek.com")
        config.setdefault("model", "deepseek-chat")
        config.setdefault("name", "deepseek")
        super().__init__(config)


class QwenProvider(OpenAICompatibleProvider):
    """Qwen Plus - ~$0.80/1M input, $2.00/1M output."""

    def __init__(self, config: Dict[str, Any]):
        config.setdefault("endpoint", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        config.setdefault("model", "qwen-plus")
        config.setdefault("name", "qwen")
        super().__init__(config)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude - fallback caro (~$3/1M input, $15/1M output)."""

    name = "anthropic"

    def __init__(self, config: Dict[str, Any]):
        config.setdefault("model", "claude-sonnet-4-20250514")
        config.setdefault("name", "anthropic")
        super().__init__(config)

    def chat(self, system: str, messages: List[Dict], max_tokens: int) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )

        return LLMResponse(
            text=response.content[0].text,
            provider=self.name,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


# Mapa de nombres a clases de provider
PROVIDER_CLASSES = {
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "anthropic": AnthropicProvider,
}


class ProviderChain:
    """
    Cadena de proveedores con fallback automatico.

    Intenta el proveedor mas barato primero. Si falla, pasa al siguiente.
    Solo inicializa providers que tengan API key configurada.

    Uso:
        chain = ProviderChain(LLM_PROVIDERS)
        print(chain.available_providers)  # ['deepseek', 'qwen']
        response = chain.chat(system="...", messages=[...], max_tokens=2048)
    """

    def __init__(self, provider_configs: List[Dict[str, Any]]):
        self.providers: List[LLMProvider] = []

        for config in provider_configs:
            name = config.get("name", "")
            provider_class = PROVIDER_CLASSES.get(name)

            if provider_class is None:
                logger.warning(f"Provider desconocido: {name}, saltando")
                continue

            provider = provider_class(config)

            if provider.available:
                self.providers.append(provider)
                logger.info(f"Provider {name} ({provider.model}): disponible")
            else:
                env_var = config.get("api_key_env", "?")
                logger.info(f"Provider {name}: sin API key ({env_var})")

        if not self.providers:
            raise RuntimeError(
                "No hay providers LLM disponibles. "
                "Configura al menos una API key: DEEPSEEK_API_KEY, DASHSCOPE_API_KEY o ANTHROPIC_API_KEY"
            )

    @property
    def available_providers(self) -> List[str]:
        """Lista de nombres de providers disponibles (en orden de prioridad)."""
        return [p.name for p in self.providers]

    def chat(self, system: str, messages: List[Dict], max_tokens: int) -> LLMResponse:
        """
        Llama al LLM usando la cadena de fallback.

        Intenta cada provider en orden. Si uno falla, pasa al siguiente.
        Lanza la ultima excepcion si todos fallan.
        """
        last_error = None

        for provider in self.providers:
            try:
                start = time.time()
                response = provider.chat(system, messages, max_tokens)
                elapsed = time.time() - start

                logger.info(
                    f"LLM response via {provider.name} "
                    f"({response.input_tokens}in/{response.output_tokens}out) "
                    f"en {elapsed:.1f}s"
                )
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Provider {provider.name} fallo: {type(e).__name__}: {e}"
                )
                continue

        raise RuntimeError(
            f"Todos los providers fallaron. Ultimo error: {last_error}"
        ) from last_error
