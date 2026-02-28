"""Anthropic provider — wraps AsyncAnthropic for Claude API calls.

This is the native provider for the Airees model router.  It translates
the generic ``create_message`` interface into calls against the Anthropic
Messages API, forwarding tools and respecting per-request max_tokens
overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from airees.router.types import ModelConfig, ProviderType


@dataclass
class AnthropicProvider:
    """Thin wrapper around :class:`anthropic.AsyncAnthropic`.

    Attributes:
        api_key: Anthropic API key used to authenticate requests.
        provider_type: Always :attr:`ProviderType.ANTHROPIC` (set
            automatically, not user-supplied).
    """

    api_key: str
    provider_type: ProviderType = field(default=ProviderType.ANTHROPIC, init=False)
    _client: anthropic.AsyncAnthropic = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """Send a message creation request to the Anthropic Messages API.

        Parameters:
            model: The model configuration specifying which Claude model to
                call and its default parameters.
            system: The system prompt.
            messages: Conversation history in Anthropic message format.
            tools: Optional list of tool definitions to make available to the
                model.
            max_tokens: Override for ``model.max_tokens``.  When ``None``,
                the value from the :class:`ModelConfig` is used.

        Returns:
            The raw Anthropic ``Message`` response object.
        """
        kwargs: dict[str, Any] = {
            "model": model.model_id,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens or model.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        return await self._client.messages.create(**kwargs)
