from __future__ import annotations
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import make_backend
from gateway.streaming import stream_chat


def make_ollama_line(content: str, done: bool = False) -> str:
    return json.dumps({
        "message": {"role": "assistant", "content": content},
        "done": done,
    })


@pytest.mark.asyncio
async def test_streams_tokens_as_sse():
    backend = make_backend("test_backend")
    lines = [
        make_ollama_line("Hello"),
        make_ollama_line(" world"),
        make_ollama_line("", done=True),
    ]

    async def fake_aiter_lines():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = fake_aiter_lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("gateway.streaming.httpx.AsyncClient", return_value=mock_client):
        chunks = [chunk async for chunk in stream_chat(backend, {"model": "test"})]

    sse_data = [c for c in chunks if c.startswith("data: ") and "[DONE]" not in c]
    assert len(sse_data) >= 2

    parsed = json.loads(sse_data[0][6:])
    assert "choices" in parsed
    assert parsed["backend_id"] == "test_backend"


@pytest.mark.asyncio
async def test_emits_done_signal():
    backend = make_backend("test_backend")
    lines = [make_ollama_line("Hi", done=True)]

    async def fake_aiter_lines():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = fake_aiter_lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("gateway.streaming.httpx.AsyncClient", return_value=mock_client):
        chunks = [chunk async for chunk in stream_chat(backend, {"model": "test"})]

    assert any("[DONE]" in c for c in chunks)


@pytest.mark.asyncio
async def test_records_failure_on_http_error():
    import httpx
    backend = make_backend("test_backend")

    async def fake_aiter_lines():
        return
        yield  # make it an async generator

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500)
        )
    )
    mock_resp.aiter_lines = fake_aiter_lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("gateway.streaming.httpx.AsyncClient", return_value=mock_client):
        chunks = [chunk async for chunk in stream_chat(backend, {"model": "test"})]

    assert any("error" in c for c in chunks)
    assert backend.errors_total == 1


@pytest.mark.asyncio
async def test_connection_decremented_after_stream():
    backend = make_backend("test_backend")
    assert backend.active_connections == 0

    lines = [make_ollama_line("done", done=True)]

    async def fake_aiter_lines():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = fake_aiter_lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("gateway.streaming.httpx.AsyncClient", return_value=mock_client):
        _ = [c async for c in stream_chat(backend, {"model": "test"})]

    assert backend.active_connections == 0
