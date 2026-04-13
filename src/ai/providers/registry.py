"""Provider selection and instantiation."""

from __future__ import annotations

from typing import Optional

from src.config import Config, get_config

from .anthropic_provider import AnthropicProvider
from .base import BaseAIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    """Resolve the configured AI provider into a concrete adapter."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()

    def get_provider(
        self, provider_name: Optional[str] = None, model_override: Optional[str] = None
    ) -> BaseAIProvider:
        provider = (provider_name or self.config.ai.provider).lower()
        provider_config = self.config.get_ai_provider_config(provider)
        if model_override:
            provider_config.model = model_override

        if provider == "openai":
            return OpenAIProvider(
                api_key=provider_config.api_key,
                model=provider_config.model,
                temperature=provider_config.temperature,
                max_tokens=provider_config.max_tokens,
                timeout=provider_config.timeout,
            )
        if provider == "anthropic":
            return AnthropicProvider(
                api_key=provider_config.api_key,
                model=provider_config.model,
                temperature=provider_config.temperature,
                max_tokens=provider_config.max_tokens,
                timeout=provider_config.timeout,
            )
        if provider == "gemini":
            return GeminiProvider(
                api_key=provider_config.api_key,
                model=provider_config.model,
                temperature=provider_config.temperature,
                max_tokens=provider_config.max_tokens,
                timeout=provider_config.timeout,
            )
        raise ValueError(f"Unsupported AI provider '{provider}'")
