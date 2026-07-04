from __future__ import annotations
import pytest
from gateway.router import Router
from gateway.circuit_breaker import CircuitBreaker
from config.settings import RoutingConfig
from tests.conftest import make_backend


@pytest.mark.asyncio
async def test_latency_aware_selects_fastest(router):
    for _ in range(10):
        selected = await router.select(strategy="latency_aware")
        assert selected.config.id == "backend_a"  # 50ms wins


@pytest.mark.asyncio
async def test_least_connections_selects_min(router):
    # backend_b has 1 connection — wins
    selected = await router.select(strategy="least_connections")
    assert selected.config.id == "backend_b"


@pytest.mark.asyncio
async def test_round_robin_uses_all_backends(router):
    seen = set()
    for _ in range(30):
        b = await router.select(strategy="round_robin")
        seen.add(b.config.id)
    assert len(seen) == 3


@pytest.mark.asyncio
async def test_unhealthy_backend_excluded():
    backends = {
        "a": make_backend("a", healthy=True, latency_ms=100),
        "b": make_backend("b", healthy=False, latency_ms=10),
    }
    r = Router(backends, RoutingConfig(default_strategy="latency_aware"))
    for _ in range(10):
        selected = await r.select(strategy="latency_aware")
        assert selected.config.id == "a"


@pytest.mark.asyncio
async def test_open_circuit_backend_excluded():
    backends = {
        "a": make_backend("a", latency_ms=200),
        "b": make_backend("b", latency_ms=10),
    }
    await backends["b"].circuit_breaker.force_open()
    r = Router(backends, RoutingConfig(default_strategy="latency_aware"))
    for _ in range(10):
        selected = await r.select(strategy="latency_aware")
        assert selected.config.id == "a"


@pytest.mark.asyncio
async def test_no_backends_returns_none():
    backends = {
        "a": make_backend("a", healthy=False),
        "b": make_backend("b", healthy=False),
    }
    r = Router(backends, RoutingConfig())
    result = await r.select()
    assert result is None


@pytest.mark.asyncio
async def test_priority_premium_picks_fastest(router):
    selected = await router.select(strategy="priority", tier="premium")
    assert selected.config.id == "backend_a"  # lowest EWMA


@pytest.mark.asyncio
async def test_priority_batch_picks_least_connections(router):
    selected = await router.select(strategy="priority", tier="batch")
    assert selected.config.id == "backend_b"  # 1 connection


@pytest.mark.asyncio
async def test_weighted_round_robin_respects_weight():
    backends = {
        "a": make_backend("a", weight=1),
        "b": make_backend("b", weight=3),
    }
    r = Router(backends, RoutingConfig(default_strategy="round_robin"))
    counts = {"a": 0, "b": 0}
    for _ in range(100):
        s = await r.select(strategy="round_robin")
        counts[s.config.id] += 1
    # b should appear ~3x more than a
    assert counts["b"] > counts["a"] * 2
