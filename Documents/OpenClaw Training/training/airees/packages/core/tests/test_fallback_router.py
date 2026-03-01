"""Tests for the fallback router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from airees.router.fallback import FallbackRouter
from airees.router.types import ModelConfig


@pytest.mark.asyncio
async def test_fallback_uses_first_provider():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(return_value=MagicMock(content=[]))
    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    await router.create_message(model=model, system="test", messages=[])
    provider1.create_message.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_retries_on_error():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(
        side_effect=[Exception("rate limit"), MagicMock(content=[])]
    )
    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        backoff_base=0.01,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    await router.create_message(model=model, system="test", messages=[])
    assert provider1.create_message.call_count == 2


@pytest.mark.asyncio
async def test_fallback_tries_next_provider():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("down"))
    provider2 = AsyncMock()
    provider2.create_message = AsyncMock(return_value=MagicMock(content=[]))
    router = FallbackRouter(
        providers=[("anthropic", provider1), ("openrouter", provider2)],
        model_compatibility={"claude-haiku-4-5": ["anthropic", "openrouter"]},
        max_retries=1,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    await router.create_message(model=model, system="test", messages=[])
    provider2.create_message.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_skips_incompatible_providers():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("down"))
    provider2 = AsyncMock()
    provider2.create_message = AsyncMock(return_value=MagicMock(content=[]))
    router = FallbackRouter(
        providers=[("anthropic", provider1), ("openai", provider2)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        max_retries=1,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    with pytest.raises(Exception, match="down"):
        await router.create_message(model=model, system="test", messages=[])
    provider2.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_raises_after_all_retries():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("always fails"))
    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        max_retries=2, backoff_base=0.01,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    with pytest.raises(Exception, match="always fails"):
        await router.create_message(model=model, system="test", messages=[])
