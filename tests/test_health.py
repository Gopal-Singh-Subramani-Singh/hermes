from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import make_backend
from gateway.health import HealthChecker


def test_ewma_update_converges():
    b = make_backend("test", latency_ms=100.0)
    for _ in range(200):
        b.update_ewma(50.0)
    assert b.latency_ewma_ms < 55.0


def test_increment_decrement_connections():
    b = make_backend("test")
    assert b.active_connections == 0
    b.increment_connections()
    b.increment_connections()
    assert b.active_connections == 2
    b.decrement_connections()
    assert b.active_connections == 1
    b.decrement_connections()
    b.decrement_connections()  # should not go below 0
    assert b.active_connections == 0


@pytest.mark.asyncio
async def test_health_checker_marks_healthy():
    backend = make_backend("a", healthy=False)
    checker = HealthChecker({"a": backend})

    with patch("gateway.health.httpx.AsyncClient") as MockClient:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_resp
        )
        await checker._check(backend)

    assert backend.healthy is True


@pytest.mark.asyncio
async def test_health_checker_marks_unhealthy():
    import httpx
    backend = make_backend("a", healthy=True)
    checker = HealthChecker({"a": backend})

    with patch("gateway.health.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        await checker._check(backend)

    assert backend.healthy is False
