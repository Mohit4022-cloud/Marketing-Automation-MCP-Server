"""OpenAI provider adapter using the Responses API."""

from __future__ import annotations

import json
from typing import Any, Dict

from openai import AsyncOpenAI

from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider backed by the Responses API."""

    name = "openai"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.require_configured()
        response = await self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )
        return (response.output_text or "").strip()

    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.require_configured()
        response = await self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "structured_response",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        payload = json.loads((response.output_text or "").strip())
        return self._validate_payload(payload, schema)
