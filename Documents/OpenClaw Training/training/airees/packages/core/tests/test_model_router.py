"""Tests for ModelRouter — the single entry point for all LLM API calls.

Validates provider selection logic:
- Anthropic by default
- OpenRouter when explicitly requested
- ValueError when OpenRouter requested but no key configured
- Graceful operation with only an Anthropic key
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from airees.router.model_router import ModelRouter
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def router():
    return ModelRouter(
        anthropic_api_key="test-anthropic",
        openrouter_api_key="test-openrouter",
    )


def test_router_has_both_providers(router):
    assert router._anthropic is not None
    assert router._openrouter is not None


def test_router_selects_anthropic_by_default(router):
    config = ModelConfig(model_id="claude-sonnet-4-6")
    provider = router._get_provider(config)
    assert provider.provider_type == ProviderType.ANTHROPIC


def test_router_selects_openrouter_for_openrouter_model(router):
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    provider = router._get_provider(config)
    assert provider.provider_type == ProviderType.OPENROUTER


def test_router_without_openrouter_key():
    router = ModelRouter(anthropic_api_key="test")
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    with pytest.raises(ValueError, match="OpenRouter API key not configured"):
        router._get_provider(config)


def test_router_anthropic_only():
    router = ModelRouter(anthropic_api_key="test")
    assert router._anthropic is not None
    assert router._openrouter is None
