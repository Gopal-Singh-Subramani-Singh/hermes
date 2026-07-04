from __future__ import annotations
import json
import time
from typing import AsyncGenerator
import httpx
import structlog

from gateway.health import BackendState
from gateway.metrics import STREAM_CHUNKS_TOTAL, TTFT

logger = structlog.get_logger(__name__)


async def stream_chat(
    backend: BackendState,
    payload: dict,
) -> AsyncGenerator[str, None]:
    """
    Proxy a streaming chat request to Ollama.
    Yields Server-Sent Event formatted strings.
    """
    url = f"{backend.config.url}/api/chat"
    payload = {**payload, "stream": True}
    t_start = time.monotonic()
    first_token = True

    backend.increment_connections()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0, read=120.0, write=10.0, pool=5.0
            )
        ) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()

                async for raw_line in resp.aiter_lines():
                    if not raw_line.strip():
                        continue

                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    if first_token:
                        ttft = time.monotonic() - t_start
                        TTFT.labels(
                            backend_id=backend.config.id
                        ).observe(ttft)
                        first_token = False

                    STREAM_CHUNKS_TOTAL.labels(
                        backend_id=backend.config.id
                    ).inc()

                    content = (
                        chunk.get("message", {}).get("content", "")
                        or chunk.get("response", "")
                    )
                    done = chunk.get("done", False)

                    sse_payload = json.dumps(
                        {
                            "id": "hermes-stream",
                            "object": "chat.completion.chunk",
                            "backend_id": backend.config.id,
                            "model": backend.config.model,
                            "choices": [
                                {
                                    "delta": {"content": content},
                                    "finish_reason": "stop"
                                    if done
                                    else None,
                                }
                            ],
                        }
                    )
                    yield f"data: {sse_payload}\n\n"

                    if done:
                        yield "data: [DONE]\n\n"
                        break

        await backend.circuit_breaker.record_success()
        backend.requests_total += 1

    except httpx.HTTPStatusError as exc:
        await backend.circuit_breaker.record_failure()
        backend.errors_total += 1
        err = json.dumps(
            {
                "error": "backend_http_error",
                "status": exc.response.status_code,
                "backend_id": backend.config.id,
            }
        )
        yield f"data: {err}\n\n"
        logger.error(
            "stream.http_error",
            backend=backend.config.id,
            status=exc.response.status_code,
        )

    except Exception as exc:
        await backend.circuit_breaker.record_failure()
        backend.errors_total += 1
        err = json.dumps(
            {
                "error": "backend_error",
                "detail": str(exc),
                "backend_id": backend.config.id,
            }
        )
        yield f"data: {err}\n\n"
        logger.error(
            "stream.error",
            backend=backend.config.id,
            error=str(exc),
        )

    finally:
        backend.decrement_connections()
