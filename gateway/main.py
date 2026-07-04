from __future__ import annotations
import time
import json
import httpx
import structlog
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config.settings import get_config, BackendConfig
from gateway.models import (
    ChatCompletionRequest,
    CompletionRequest,
    GatewayStatusResponse,
    BackendStatus,
    RouteOverrideRequest,
    HealthResponse,
    RequestTier,
)
from gateway.circuit_breaker import CircuitBreaker
from gateway.health import BackendState, HealthChecker
from gateway.router import Router
from gateway.rate_limiter import RateLimiter
from gateway.queue import RequestQueue
from gateway.streaming import stream_chat
from gateway.metrics import (
    REQUESTS_TOTAL,
    REQUEST_DURATION,
    BACKEND_LATENCY,
    update_uptime,
)

logger = structlog.get_logger(__name__)


@dataclass
class AppState:
    redis: Optional[aioredis.Redis] = None
    backends: Dict[str, BackendState] = field(default_factory=dict)
    router: Optional[Router] = None
    rate_limiter: Optional[RateLimiter] = None
    queue: Optional[RequestQueue] = None
    health_checker: Optional[HealthChecker] = None
    start_time: float = field(default_factory=time.time)
    redis_ok: bool = False


app_state = AppState()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()

    # Redis
    app_state.redis = aioredis.from_url(
        cfg.redis.url,
        db=cfg.redis.db,
        max_connections=cfg.redis.max_connections,
        decode_responses=True,
    )
    try:
        await app_state.redis.ping()
        app_state.redis_ok = True
        logger.info("redis.connected", url=cfg.redis.url)
    except Exception as e:
        logger.error("redis.connection_failed", error=str(e))

    # Build BackendState for each configured backend
    cb_cfg = cfg.circuit_breaker
    for bc in cfg.backends:
        cb = CircuitBreaker(
            backend_id=bc.id,
            error_threshold=cb_cfg.error_threshold,
            window_seconds=cb_cfg.window_seconds,
            open_timeout=cb_cfg.open_timeout,
            success_threshold=cb_cfg.success_threshold,
        )
        app_state.backends[bc.id] = BackendState(
            config=bc, circuit_breaker=cb
        )

    app_state.router = Router(app_state.backends, cfg.routing)
    app_state.rate_limiter = RateLimiter(app_state.redis)
    app_state.queue = RequestQueue(app_state.redis)
    app_state.health_checker = HealthChecker(app_state.backends)
    await app_state.health_checker.start()

    # Initialize rate limit metrics to 0 for a clean dashboard
    from gateway.metrics import RATE_LIMIT_REJECTIONS
    for tier in cfg.rate_limiting.tiers.model_dump().keys():
        RATE_LIMIT_REJECTIONS.labels(tier=tier).inc(0)

    logger.info(
        "hermes.started",
        backends=list(app_state.backends.keys()),
        strategy=cfg.routing.default_strategy,
    )

    yield  # ← app is live here

    await app_state.health_checker.stop()
    if app_state.redis:
        await app_state.redis.aclose()
    logger.info("hermes.shutdown")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hermes — LLM Inference Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware ─────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - t0) * 1000, 1)
    logger.info(
        "http",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ms=ms,
    )
    return response


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _call_backend(
    backend: BackendState,
    url_path: str,
    payload: dict,
    cfg,
    tier: str,
    model: str,
):
    t0 = time.monotonic()
    backend.increment_connections()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=cfg.timeouts.connect,
                read=cfg.timeouts.read,
                write=cfg.timeouts.write,
                pool=5.0,
            )
        ) as client:
            resp = await client.post(
                f"{backend.config.url}{url_path}", json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        latency_s = time.monotonic() - t0
        backend.update_ewma(latency_s * 1000)
        backend.requests_total += 1
        await backend.circuit_breaker.record_success()

        REQUESTS_TOTAL.labels(
            backend_id=backend.config.id,
            model=model,
            status="success",
            tier=tier,
        ).inc()
        REQUEST_DURATION.labels(
            backend_id=backend.config.id, model=model, tier=tier
        ).observe(latency_s)
        BACKEND_LATENCY.labels(backend_id=backend.config.id).observe(
            latency_s
        )
        return data

    except httpx.HTTPStatusError as exc:
        backend.errors_total += 1
        await backend.circuit_breaker.record_failure()
        REQUESTS_TOTAL.labels(
            backend_id=backend.config.id,
            model=model,
            status="error",
            tier=tier,
        ).inc()
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Backend {backend.config.id}: {exc}",
        )
    except Exception as exc:
        backend.errors_total += 1
        await backend.circuit_breaker.record_failure()
        REQUESTS_TOTAL.labels(
            backend_id=backend.config.id,
            model=model,
            status="error",
            tier=tier,
        ).inc()
        raise HTTPException(
            status_code=502,
            detail=f"Backend {backend.config.id} error: {str(exc)}",
        )
    finally:
        backend.decrement_connections()


# ── Inference routes ───────────────────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    cfg = get_config()
    tier = req.tier.value

    if not await app_state.rate_limiter.is_allowed(tier=tier):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    strategy = (
        req.routing_strategy.value if req.routing_strategy else None
    )
    backend = await app_state.router.select(
        strategy=strategy, tier=tier
    )
    if backend is None:
        raise HTTPException(
            status_code=503, detail="No healthy backends available"
        )

    model = req.model or backend.config.model
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in req.messages],
        "stream": req.stream,
        "options": {
            "temperature": req.temperature,
            **(
                {"num_predict": req.max_tokens}
                if req.max_tokens
                else {}
            ),
        },
    }

    if req.stream:
        return StreamingResponse(
            stream_chat(backend, payload),
            media_type="text/event-stream",
            headers={"X-Backend-ID": backend.config.id},
        )

    data = await _call_backend(
        backend, "/api/chat", payload, cfg, tier, model
    )
    return {
        "id": "hermes-chat",
        "object": "chat.completion",
        "backend_id": backend.config.id,
        "model": model,
        "choices": [
            {
                "message": data.get("message", {}),
                "finish_reason": "stop",
            }
        ],
        "usage": data.get("eval_count", {}),
    }


@app.post("/v1/completions")
async def completions(req: CompletionRequest):
    chat_req = ChatCompletionRequest(
        model=req.model,
        messages=[{"role": "user", "content": req.prompt}],
        stream=req.stream,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        tier=req.tier,
    )
    return await chat_completions(chat_req)


# ── Observability ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    uptime = update_uptime()
    healthy = sum(1 for b in app_state.backends.values() if b.healthy)
    return HealthResponse(
        status="ok" if healthy > 0 else "degraded",
        healthy_backends=healthy,
        total_backends=len(app_state.backends),
        redis="ok" if app_state.redis_ok else "unavailable",
        uptime_seconds=round(uptime, 1),
    )


@app.get("/status", response_model=GatewayStatusResponse)
async def status():
    uptime = update_uptime()
    cfg = get_config()
    backend_list = [
        BackendStatus(
            id=b.config.id,
            url=b.config.url,
            model=b.config.model,
            healthy=b.healthy,
            circuit_state=b.circuit_breaker.get_state(),
            active_connections=b.active_connections,
            latency_ewma_ms=round(b.latency_ewma_ms, 1),
            requests_total=b.requests_total,
            errors_total=b.errors_total,
        )
        for b in app_state.backends.values()
    ]
    queue_depth = await app_state.queue.depth_by_tier()
    return GatewayStatusResponse(
        status="ok",
        routing_strategy=cfg.routing.default_strategy,
        backends=backend_list,
        queue_depth=queue_depth,
        uptime_seconds=round(uptime, 1),
        redis_connected=app_state.redis_ok,
    )


@app.get("/metrics")
async def metrics():
    update_uptime()
    return Response(
        content=generate_latest(), media_type=CONTENT_TYPE_LATEST
    )


# ── Admin ──────────────────────────────────────────────────────────────────────

@app.post("/admin/routing/strategy")
async def set_routing_strategy(req: RouteOverrideRequest):
    get_config().routing.default_strategy = req.strategy.value
    logger.info(
        "admin.strategy_changed", strategy=req.strategy.value
    )
    return {"strategy": req.strategy.value, "status": "ok"}


@app.post("/admin/circuit-breaker/{backend_id}/open")
async def cb_open(backend_id: str):
    if backend_id not in app_state.backends:
        raise HTTPException(status_code=404, detail="Backend not found")
    await app_state.backends[backend_id].circuit_breaker.force_open()
    return {"backend_id": backend_id, "state": "OPEN"}


@app.post("/admin/circuit-breaker/{backend_id}/close")
async def cb_close(backend_id: str):
    if backend_id not in app_state.backends:
        raise HTTPException(status_code=404, detail="Backend not found")
    await app_state.backends[backend_id].circuit_breaker.force_close()
    return {"backend_id": backend_id, "state": "CLOSED"}


@app.get("/admin/queue/depth")
async def queue_depth():
    return await app_state.queue.depth_by_tier()


@app.post("/admin/rate-limit/reset")
async def reset_rate_limit(tier: str = "standard"):
    await app_state.rate_limiter.reset(tier=tier)
    return {"tier": tier, "status": "reset"}


# ── UI ─────────────────────────────────────────────────────────────────────────

@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path("ui/index.html")
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text())
    return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)


@app.get("/")
async def root():
    return {"service": "Hermes", "version": "0.1.0", "ui": "/ui", "docs": "/docs"}
