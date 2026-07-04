from __future__ import annotations
import pytest
from gateway.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_allows_first_request(rate_limiter):
    result = await rate_limiter.is_allowed(tier="standard")
    assert result is True


@pytest.mark.asyncio
async def test_rejects_after_burst_exhausted(rate_limiter):
    # standard = 60rpm, burst = 1.5x = 90 tokens
    results = [
        await rate_limiter.is_allowed(tier="standard", key_suffix="burst_test")
        for _ in range(150)
    ]
    allowed = sum(r for r in results)
    rejected = len(results) - allowed
    assert allowed <= 95      # burst cap
    assert rejected >= 50     # definitely hits the cap


@pytest.mark.asyncio
async def test_premium_allows_more_than_batch(rate_limiter):
    premium_allowed = 0
    batch_allowed = 0
    for _ in range(350):
        if await rate_limiter.is_allowed(tier="premium", key_suffix="cmp_p"):
            premium_allowed += 1
        if await rate_limiter.is_allowed(tier="batch", key_suffix="cmp_b"):
            batch_allowed += 1
    assert premium_allowed > batch_allowed


@pytest.mark.asyncio
async def test_different_key_suffixes_independent(rate_limiter):
    for _ in range(150):
        await rate_limiter.is_allowed(tier="batch", key_suffix="sink")
    # Different key should still have tokens
    assert await rate_limiter.is_allowed(tier="batch", key_suffix="fresh")


@pytest.mark.asyncio
async def test_reset_refills_bucket(rate_limiter):
    for _ in range(150):
        await rate_limiter.is_allowed(tier="batch", key_suffix="reset_test")

    before = await rate_limiter.get_remaining(tier="batch", key_suffix="reset_test")
    await rate_limiter.reset(tier="batch", key_suffix="reset_test")
    after = await rate_limiter.get_remaining(tier="batch", key_suffix="reset_test")
    assert after > before


@pytest.mark.asyncio
async def test_disabled_always_allows(fake_redis, test_config):
    from unittest.mock import patch
    from config.settings import RateLimitConfig

    cfg = test_config.model_copy(
        update={"rate_limiting": RateLimitConfig(enabled=False)}
    )
    with patch("gateway.rate_limiter.get_config", return_value=cfg):
        rl = RateLimiter(fake_redis)
        for _ in range(500):
            assert await rl.is_allowed() is True


@pytest.mark.asyncio
async def test_get_remaining_returns_int(rate_limiter):
    remaining = await rate_limiter.get_remaining(tier="standard")
    assert isinstance(remaining, int)
    assert remaining > 0
