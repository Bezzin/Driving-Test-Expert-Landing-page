"""Model routing types for the Airees core SDK.

ModelConfig determines which LLM provider handles a request. The
``openrouter/`` prefix convention lets users write
``model: openrouter/deepseek/deepseek-r1`` in YAML configs and have it
auto-route to OpenRouter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProviderType(Enum):
    """Supported LLM provider backends."""

    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass(frozen=True)
class ModelConfig:
    """Immutable model configuration that pairs a model ID with its provider.

    Attributes:
        model_id: The model identifier (e.g. ``claude-sonnet-4-6`` or
            ``deepseek/deepseek-r1``).  If prefixed with ``openrouter/``,
            the prefix is stripped and the provider is set to
            :attr:`ProviderType.OPENROUTER` automatically.
        provider: The backend that serves this model.  Defaults to
            :attr:`ProviderType.ANTHROPIC`.
        temperature: Sampling temperature.  Defaults to ``1.0``.
        max_tokens: Maximum tokens in the completion.  Defaults to ``4096``.
    """

    model_id: str
    provider: ProviderType = field(default=ProviderType.ANTHROPIC)
    temperature: float = 1.0
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        if self.model_id.startswith("openrouter/"):
            object.__setattr__(self, "model_id", self.model_id[len("openrouter/"):])
            object.__setattr__(self, "provider", ProviderType.OPENROUTER)
