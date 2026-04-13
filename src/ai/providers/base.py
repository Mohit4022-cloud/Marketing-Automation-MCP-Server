"""Common abstractions for AI providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from jsonschema import ValidationError, validate


class AIProviderError(Exception):
    """Base provider error."""


class AIProviderNotConfiguredError(AIProviderError):
    """Raised when the selected provider lacks credentials or model configuration."""


class StructuredGenerationError(AIProviderError):
    """Raised when a provider returns malformed structured output."""


def strip_json_fences(text: str) -> str:
    """Strip common markdown fencing from provider JSON responses."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


class BaseAIProvider(ABC):
    """Provider contract for text and structured generation."""

    name = "base"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        *,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Whether the provider has enough config to serve requests."""
        return bool(self.api_key and self.model)

    def require_configured(self):
        """Raise if the provider is not ready for use."""
        if not self.is_configured:
            raise AIProviderNotConfiguredError(
                f"{self.name} provider is not configured with API key and model"
            )

    def _validate_payload(self, payload: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a structured response against its schema."""
        try:
            validate(instance=payload, schema=schema)
        except ValidationError as exc:
            raise StructuredGenerationError(
                f"{self.name} provider returned payload that failed schema validation: {exc.message}"
            ) from exc
        return payload

    def _parse_json_response(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate a JSON response string."""
        try:
            payload = json.loads(strip_json_fences(text))
        except json.JSONDecodeError as exc:
            raise StructuredGenerationError(
                f"{self.name} provider returned invalid JSON: {exc.msg}"
            ) from exc
        return self._validate_payload(payload, schema)

    @abstractmethod
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Generate unstructured text."""

    @abstractmethod
    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON matching the supplied schema."""
