"""
LLM Service

Provider-agnostic wrapper for chat completions.

Supports:
- OpenAI (default, direct API)
- HuggingFace Inference API (Qwen, Llama, Mistral, etc. via OpenAI-compatible endpoint)
- Any OpenAI-compatible endpoint (vLLM, Ollama, LiteLLM, Together AI, etc.)

The OpenAI Python SDK supports custom `base_url`, so HuggingFace's
OpenAI-compatible inference endpoint works without any SDK change — just
point the base_url to https://router.huggingface.co/v1 and use your
HF token as the API key.

Configuration (in .env):
- LLM_API_KEY: Your API key (HuggingFace token or OpenAI key)
- LLM_BASE_URL: Custom endpoint (empty = OpenAI default)
- LLM_MODEL: Model identifier (e.g. "Qwen/Qwen2.5-72B-Instruct" for HF)

Backward compatible: if LLM_API_KEY is empty, falls back to OPENAI_API_KEY/OPENAI_MODEL.
"""

import json
import re
from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings


class LLMServiceError(Exception):
    """Raised when the LLM call fails (rate limit, timeout, invalid response, etc)."""
    pass


class LLMService:
    """
    Wraps LLM chat completions behind a provider-agnostic interface.

    Works with any OpenAI-compatible API:
    - OpenAI directly
    - HuggingFace Inference API (Qwen 2.5, Llama, Mistral, etc.)
    - Self-hosted (vLLM, Ollama, text-generation-inference)
    """

    def __init__(self, model: Optional[str] = None):
        # Resolve model: new config > legacy config
        self.model = model or settings.LLM_MODEL or settings.OPENAI_MODEL
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazily create the client pointing at the configured LLM endpoint."""
        if self._client is None:
            # Resolve API key: new config > legacy config
            api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY
            if not api_key:
                raise LLMServiceError(
                    "LLM_API_KEY (or OPENAI_API_KEY) is not configured. "
                    "Set it in your .env file."
                )

            # Resolve base URL: new config > None (defaults to OpenAI)
            base_url = settings.LLM_BASE_URL or None

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        return self._client

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Get a plain text completion from the LLM.

        Works identically regardless of whether the backend is OpenAI,
        HuggingFace, or any other OpenAI-compatible endpoint.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMServiceError("LLM returned an empty response")
            return content.strip()
        except OpenAIError as e:
            raise LLMServiceError(f"LLM request failed: {str(e)}") from e

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 1000,
    ) -> dict:
        """
        Get a JSON-structured completion from the LLM.

        For OpenAI: uses response_format=json_object for guaranteed valid JSON.
        For HuggingFace/other providers: relies on prompt instruction + post-processing
        (not all providers support response_format).
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "max_tokens": max_tokens,
            }

            # Only use response_format for providers that support it (OpenAI, some HF models)
            # HuggingFace's API may or may not support this depending on the model
            if not settings.LLM_BASE_URL:
                # Pure OpenAI — use JSON mode
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise LLMServiceError("LLM returned an empty response")

            # Clean up response: some models wrap JSON in markdown code fences
            cleaned = self._extract_json(content)
            return json.loads(cleaned)

        except OpenAIError as e:
            raise LLMServiceError(f"LLM request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise LLMServiceError(f"LLM returned invalid JSON: {str(e)}") from e

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Extract JSON from LLM response, handling common formatting issues:
        - Markdown code fences (```json ... ```)
        - Leading/trailing text around the JSON object
        """
        text = text.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # Remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try to find JSON object boundaries if there's surrounding text
        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group()

        return text
