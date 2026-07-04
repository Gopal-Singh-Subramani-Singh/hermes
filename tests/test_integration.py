from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_root_returns_service_info():
    from gateway.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Hermes"
    assert "ui" in data


@pytest.mark.asyncio
async def test_health_endpoint_structure():
    from gateway.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "healthy_backends" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_metrics_contains_hermes_prefix():
    from gateway.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert b"hermes_" in resp.content


@pytest.mark.asyncio
async def test_chat_returns_429_when_rate_limited():
    from gateway.main import app, app_state
    with patch.object(app_state, "rate_limiter") as mock_rl:
        mock_rl.is_allowed = AsyncMock(return_value=False)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_chat_returns_503_when_no_backends():
    from gateway.main import app, app_state
    with patch.object(app_state, "rate_limiter") as mock_rl:
        mock_rl.is_allowed = AsyncMock(return_value=True)
        with patch.object(app_state, "router") as mock_router:
            mock_router.select = AsyncMock(return_value=None)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": "hi"}]},
                )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_status_endpoint_shape():
    from gateway.main import app, app_state
    mock_queue = AsyncMock()
    mock_queue.depth_by_tier = AsyncMock(return_value={"premium": 0, "standard": 0, "batch": 0})
    with patch.object(app_state, "queue", mock_queue):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "backends" in data
    assert "routing_strategy" in data
    assert "queue_depth" in data
    assert "uptime_seconds" in data
