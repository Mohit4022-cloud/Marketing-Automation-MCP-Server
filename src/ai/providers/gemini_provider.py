"""Gemini provider adapter."""

from __future__ import annotations

import json
from typing import Any, Dict

from google import genai
from google.genai import types

from .base import BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Gemini provider with JSON schema-aware generation when available."""

    name = "gemini"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.require_configured()
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        return (response.text or "").strip()

    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.require_configured()
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        payload = json.loads((response.text or "").strip())
        return self._validate_payload(payload, schema)
