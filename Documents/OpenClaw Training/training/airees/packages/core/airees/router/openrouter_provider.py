"""OpenRouter provider — httpx-based client for the OpenRouter API.

OpenRouter exposes an OpenAI-compatible ``/chat/completions`` endpoint that
fronts hundreds of models (DeepSeek, Llama, Mistral, etc.).  This provider
lets Airees agents use any OpenRouter-hosted model alongside native Anthropic
models by simply setting ``provider: openrouter`` in the model config.

Usage::

    provider = OpenRouterProvider(api_key="or-...")
    result = await provider.create_message(
        model=ModelConfig(model_id="deepseek/deepseek-r1", provider=ProviderType.OPENROUTER),
        system="You are helpful",
        messages=[{"role": "user", "content": "Hello"}],
    )

The provider is intentionally thin — it translates Airees' internal message
format into the OpenAI-compatible payload that OpenRouter expects, then
returns the raw JSON response for the router layer to normalise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from airees.router.types import ModelConfig, ProviderType

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class OpenRouterProvider:
    """Async provider that sends chat-completion requests to OpenRouter.

    Attributes:
        api_key: OpenRouter API key (starts with ``or-``).
        provider_type: Always :attr:`ProviderType.OPENROUTER`.  Set
            automatically; not user-configurable.
    """

    api_key: str
    provider_type: ProviderType = field(default=ProviderType.OPENROUTER, init=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat-completion request to OpenRouter.

        Args:
            model: The model configuration specifying which model to call.
            system: System prompt prepended as the first message.
            messages: Conversation history in OpenAI message format.
            tools: Optional list of tool definitions (OpenAI function-calling
                schema).
            max_tokens: Override for :attr:`ModelConfig.max_tokens`.

        Returns:
            The raw JSON response from OpenRouter.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        payload: dict[str, Any] = {
            "model": model.model_id,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "max_tokens": max_tokens or model.max_tokens,
        }
        if tools:
            payload["tools"] = tools

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
