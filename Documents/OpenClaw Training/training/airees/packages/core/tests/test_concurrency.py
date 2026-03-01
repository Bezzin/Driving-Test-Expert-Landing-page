"""Tests for the concurrency manager."""
import asyncio
import pytest
from airees.concurrency import ConcurrencyManager


@pytest.mark.asyncio
async def test_acquire_and_release():
    mgr = ConcurrencyManager(provider_limits={"anthropic": 2}, model_limits={})
    await mgr.acquire(provider="anthropic", model="haiku")
    await mgr.acquire(provider="anthropic", model="haiku")
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="anthropic", model="haiku"), timeout=0.1,
        )
    await mgr.release(provider="anthropic", model="haiku")
    await asyncio.wait_for(
        mgr.acquire(provider="anthropic", model="haiku"), timeout=0.1,
    )
    await mgr.release(provider="anthropic", model="haiku")
    await mgr.release(provider="anthropic", model="haiku")


@pytest.mark.asyncio
async def test_model_limit_overrides_provider():
    mgr = ConcurrencyManager(
        provider_limits={"anthropic": 10}, model_limits={"claude-opus-4-6": 1},
    )
    await mgr.acquire(provider="anthropic", model="claude-opus-4-6")
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="anthropic", model="claude-opus-4-6"), timeout=0.1,
        )
    await mgr.release(provider="anthropic", model="claude-opus-4-6")


@pytest.mark.asyncio
async def test_default_limit_when_not_configured():
    mgr = ConcurrencyManager(provider_limits={}, model_limits={}, default_limit=5)
    for _ in range(5):
        await mgr.acquire(provider="unknown", model="some-model")
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="unknown", model="some-model"), timeout=0.1,
        )
    for _ in range(5):
        await mgr.release(provider="unknown", model="some-model")


@pytest.mark.asyncio
async def test_different_providers_independent():
    mgr = ConcurrencyManager(
        provider_limits={"anthropic": 1, "openrouter": 1}, model_limits={},
    )
    await mgr.acquire(provider="anthropic", model="haiku")
    await asyncio.wait_for(
        mgr.acquire(provider="openrouter", model="llama"), timeout=0.1,
    )
    await mgr.release(provider="anthropic", model="haiku")
    await mgr.release(provider="openrouter", model="llama")
