"""ModelRouter — single entry point for all LLM API calls in Airees.

The router inspects the :class:`ModelConfig` to determine which provider
(Anthropic or OpenRouter) should handle a given request, then delegates
the ``create_message`` call to the selected provider.

Usage::

    router = ModelRouter(
        anthropic_api_key="sk-ant-...",
        openrouter_api_key="or-...",      # optional
    )

    config = ModelConfig(model_id="claude-sonnet-4-6")
    result = await router.create_message(
        model=config,
        system="You are helpful",
        messages=[{"role": "user", "content": "Hello"}],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from airees.router.types import ModelConfig, ProviderType
from airees.router.anthropic_provider import AnthropicProvider
from airees.router.openrouter_provider import OpenRouterProvider


@dataclass
class ModelRouter:
    """Dispatches API calls to the correct provider based on ModelConfig.

    Attributes:
        anthropic_api_key: Required API key for the Anthropic provider.
        openrouter_api_key: Optional API key for the OpenRouter provider.
            When ``None``, only Anthropic models are available.
    """

    anthropic_api_key: str
    openrouter_api_key: str | None = None
    _anthropic: AnthropicProvider = field(init=False, repr=False)
    _openrouter: OpenRouterProvider | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._anthropic = AnthropicProvider(api_key=self.anthropic_api_key)
        if self.openrouter_api_key:
            self._openrouter = OpenRouterProvider(api_key=self.openrouter_api_key)

    def _get_provider(self, model: ModelConfig) -> AnthropicProvider | OpenRouterProvider:
        """Select the appropriate provider for the given model configuration.

        Args:
            model: The model configuration that specifies which provider to
                route to via its ``provider`` field.

        Returns:
            The matching provider instance.

        Raises:
            ValueError: If the model requires OpenRouter but no API key was
                configured.
        """
        if model.provider == ProviderType.OPENROUTER:
            if self._openrouter is None:
                raise ValueError("OpenRouter API key not configured")
            return self._openrouter
        return self._anthropic

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """Route a message-creation request to the correct provider.

        Args:
            model: The model configuration specifying which model and provider
                to use.
            system: The system prompt.
            messages: Conversation history in the provider's message format.
            tools: Optional list of tool definitions.
            max_tokens: Override for ``model.max_tokens``.  When ``None``,
                the value from the :class:`ModelConfig` is used.

        Returns:
            The raw response from the selected provider.

        Raises:
            ValueError: If the model requires a provider that is not
                configured.
        """
        provider = self._get_provider(model)
        return await provider.create_message(
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )

    async def close(self) -> None:
        """Release resources held by the underlying providers."""
        if self._openrouter:
            await self._openrouter.close()
