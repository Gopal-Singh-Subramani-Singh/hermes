from __future__ import annotations
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fakeredis import aioredis as fake_aioredis

from config.settings import (
    HermesConfig, BackendConfig, RateLimitConfig, RateLimitTiers,
    CircuitBreakerConfig, QueueConfig, QueueTiers, RoutingConfig,
    RedisConfig, TimeoutConfig, GatewayConfig,
)
from gateway.circuit_breaker import CircuitBreaker
from gateway.health import BackendState
from gateway.rate_limiter import RateLimiter
from gateway.queue import RequestQueue
from gateway.router import Router


# ── Config fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def test_config() -> HermesConfig:
    return HermesConfig(
        gateway=GatewayConfig(),
        routing=RoutingConfig(
            default_strategy="latency_aware",
            ewma_alpha=0.1,
            health_check_interval=1,
        ),
        backends=[
            BackendConfig(
                id="backend_a",
                url="http://localhost:11434",
                model="llama3.2:3b",
                weight=1,
            ),
            BackendConfig(
                id="backend_b",
                url="http://localhost:11435",
                model="phi3:mini",
                weight=1,
            ),
            BackendConfig(
                id="backend_c",
                url="http://localhost:11436",
                model="qwen2.5:7b",
                weight=2,
            ),
        ],
        rate_limiting=RateLimitConfig(
            enabled=True,
            default_rpm=60,
            burst_multiplier=1.5,
            tiers=RateLimitTiers(premium=300, standard=60, batch=20),
        ),
        circuit_breaker=CircuitBreakerConfig(
            error_threshold=0.5,
            window_seconds=10,
            open_timeout=1,  # short for tests
            success_threshold=2,
        ),
        queue=QueueConfig(
            enabled=True,
            max_depth=50,
            tiers=QueueTiers(premium=10, standard=5, batch=1),
        ),
        redis=RedisConfig(url="redis://localhost:6379"),
    )


# ── Redis fixture ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def fake_redis():
    r = fake_aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


# ── Component fixtures ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def circuit_breaker():
    return CircuitBreaker(
        backend_id="test_backend",
        error_threshold=0.5,
        window_seconds=10,
        open_timeout=1,
        success_threshold=2,
    )


@pytest_asyncio.fixture
async def rate_limiter(fake_redis, test_config):
    with patch("gateway.rate_limiter.get_config", return_value=test_config):
        rl = RateLimiter(fake_redis)
        yield rl


@pytest_asyncio.fixture
async def request_queue(fake_redis, test_config):
    with patch("gateway.queue.get_config", return_value=test_config):
        q = RequestQueue(fake_redis)
        yield q


# ── Backend factory ────────────────────────────────────────────────────────────

def make_backend(
    backend_id: str = "test",
    latency_ms: float = 100.0,
    connections: int = 0,
    healthy: bool = True,
    weight: int = 1,
    open_timeout: int = 1,
) -> BackendState:
    cb = CircuitBreaker(
        backend_id=backend_id,
        error_threshold=0.5,
        window_seconds=10,
        open_timeout=open_timeout,
        success_threshold=2,
    )
    bc = BackendConfig(
        id=backend_id,
        url=f"http://localhost:1143x",
        model="test-model",
        weight=weight,
    )
    state = BackendState(config=bc, circuit_breaker=cb)
    state.healthy = healthy
    state.latency_ewma_ms = latency_ms
    state.active_connections = connections
    return state


@pytest_asyncio.fixture
async def router(test_config):
    backends = {
        "backend_a": make_backend("backend_a", latency_ms=50.0, connections=2),
        "backend_b": make_backend("backend_b", latency_ms=200.0, connections=1),
        "backend_c": make_backend("backend_c", latency_ms=100.0, connections=5, weight=2),
    }
    return Router(backends, test_config.routing)
