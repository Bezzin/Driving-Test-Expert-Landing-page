"""Tests for model routing types — the first real code in Airees core.

Validates that ModelConfig correctly identifies providers, handles the
openrouter/ shorthand prefix, and remains immutable (frozen dataclass).
"""

from airees.router.types import ModelConfig, ProviderType


def test_model_config_anthropic_default():
    config = ModelConfig(model_id="claude-sonnet-4-6")
    assert config.provider == ProviderType.ANTHROPIC
    assert config.model_id == "claude-sonnet-4-6"


def test_model_config_openrouter():
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    assert config.provider == ProviderType.OPENROUTER


def test_model_config_shorthand():
    config = ModelConfig(model_id="openrouter/deepseek/deepseek-r1")
    assert config.provider == ProviderType.OPENROUTER
    assert config.model_id == "deepseek/deepseek-r1"


def test_model_config_is_frozen():
    import pytest

    config = ModelConfig(model_id="claude-sonnet-4-6")
    with pytest.raises(AttributeError):
        config.model_id = "something-else"
