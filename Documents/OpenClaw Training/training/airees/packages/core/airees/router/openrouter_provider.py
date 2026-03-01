"""OpenRouter provider — httpx-based client for the OpenRouter API.

OpenRouter exposes an OpenAI-compatible ``/chat/completions`` endpoint that
fronts hundreds of models (DeepSeek, Llama, Mistral, etc.).  This provider
lets Airees agents use any OpenRouter-hosted model alongside native Anthropic
models by simply setting ``provider: openrouter`` in the model config.

The provider normalises the OpenAI-format response into a lightweight object
that matches what the Runner expects from the Anthropic provider, so the
Runner can handle both providers uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from airees.router.types import ModelConfig, ProviderType

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class _ContentBlock:
    """Normalised content block matching the Anthropic SDK shape."""
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _Usage:
    """Token usage matching the Anthropic SDK shape."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class _NormalisedResponse:
    """Thin wrapper that gives an OpenRouter JSON response the same attribute
    interface as an Anthropic SDK ``Message`` object."""
    content: list[_ContentBlock]
    stop_reason: str
    usage: _Usage


def _normalise_response(data: dict[str, Any]) -> _NormalisedResponse:
    """Convert an OpenAI-compatible chat completion dict into the normalised
    response object the Runner expects."""
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    finish = choice.get("finish_reason", "end_turn")

    blocks: list[_ContentBlock] = []

    # Text content
    text = message.get("content") or ""
    if text:
        blocks.append(_ContentBlock(type="text", text=text))

    # Tool calls (OpenAI format -> Anthropic-style blocks)
    for tc in message.get("tool_calls", []):
        import json
        fn = tc.get("function", {})
        args = fn.get("arguments", "{}")
        try:
            parsed = json.loads(args) if isinstance(args, str) else args
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        blocks.append(_ContentBlock(
            type="tool_use",
            id=tc.get("id", ""),
            name=fn.get("name", ""),
            input=parsed,
        ))

    usage_data = data.get("usage", {})
    usage = _Usage(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
    )

    # Map OpenAI finish reasons to Anthropic stop reasons
    stop_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "end_turn",
    }

    return _NormalisedResponse(
        content=blocks if blocks else [_ContentBlock(type="text", text="")],
        stop_reason=stop_map.get(finish, "end_turn"),
        usage=usage,
    )


@dataclass
class OpenRouterProvider:
    """Async provider that sends chat-completion requests to OpenRouter.

    Attributes:
        api_key: OpenRouter API key (starts with ``sk-or-``).
        app_name: Optional app name sent as X-Title header for rankings.
        provider_type: Always :attr:`ProviderType.OPENROUTER`.
    """

    api_key: str
    app_name: str = "Airees"
    provider_type: ProviderType = field(default=ProviderType.OPENROUTER, init=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/airees",
                "X-Title": self.app_name,
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
    ) -> _NormalisedResponse:
        """Send a chat-completion request to OpenRouter.

        Returns a normalised response object with the same attribute
        interface as an Anthropic SDK Message (.content, .usage, .stop_reason).
        """
        payload: dict[str, Any] = {
            "model": model.model_id,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "max_tokens": max_tokens or model.max_tokens,
            "temperature": model.temperature,
            "provider": {
                "sort": "price",
                "allow_fallbacks": True,
                "require_parameters": True,
            },
        }
        if tools:
            # Convert Anthropic tool format to OpenAI function-calling format
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                })
            payload["tools"] = openai_tools

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return _normalise_response(response.json())

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
