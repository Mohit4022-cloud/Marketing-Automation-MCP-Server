"""Anthropic provider adapter."""

from __future__ import annotations

import json
from typing import Any, Dict

from anthropic import AsyncAnthropic

from .base import BaseAIProvider


class AnthropicProvider(BaseAIProvider):
    """Anthropic provider with prompt-level JSON coercion."""

    name = "anthropic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.require_configured()
        response = await self._client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        schema_prompt = json.dumps(schema, indent=2, sort_keys=True)
        text = await self.generate_text(
            system_prompt=(
                f"{system_prompt}\n\n"
                "Return JSON only. Do not wrap it in markdown fences. "
                f"The JSON must validate against this schema:\n{schema_prompt}"
            ),
            user_prompt=user_prompt,
        )
        return self._parse_json_response(text, schema)
