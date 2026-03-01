"""Model routing — provider detection and model configuration."""

from airees.router.anthropic_provider import AnthropicProvider
from airees.router.fallback import FallbackRouter
from airees.router.model_router import ModelRouter
from airees.router.openrouter_provider import OpenRouterProvider
from airees.router.types import ModelConfig, ProviderType

__all__ = [
    "AnthropicProvider",
    "FallbackRouter",
    "ModelConfig",
    "ModelRouter",
    "OpenRouterProvider",
    "ProviderType",
]
