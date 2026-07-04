from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
import httpx
import structlog

from gateway.metrics import (
    BACKEND_HEALTH,
    LATENCY_EWMA,
    ACTIVE_CONNECTIONS,
    HEALTH_CHECKS_TOTAL,
)
from gateway.circuit_breaker import CircuitBreaker
from config.settings import BackendConfig, get_config

logger = structlog.get_logger(__name__)


@dataclass
class BackendState:
    config: BackendConfig
    circuit_breaker: CircuitBreaker
    healthy: bool = True
    active_connections: int = 0
    latency_ewma_ms: float = 100.0
    requests_total: int = 0
    errors_total: int = 0
    last_checked: float = field(default_factory=time.monotonic)

    def update_ewma(self, latency_ms: float) -> None:
        alpha = get_config().routing.ewma_alpha
        self.latency_ewma_ms = (
            alpha * latency_ms + (1 - alpha) * self.latency_ewma_ms
        )
        LATENCY_EWMA.labels(backend_id=self.config.id).set(
            self.latency_ewma_ms
        )

    def increment_connections(self) -> None:
        self.active_connections += 1
        ACTIVE_CONNECTIONS.labels(backend_id=self.config.id).set(
            self.active_connections
        )

    def decrement_connections(self) -> None:
        self.active_connections = max(0, self.active_connections - 1)
        ACTIVE_CONNECTIONS.labels(backend_id=self.config.id).set(
            self.active_connections
        )


class HealthChecker:
    def __init__(self, backends: Dict[str, BackendState]) -> None:
        self._backends = backends
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(
            self._loop(), name="health_checker"
        )
        logger.info(
            "health_checker.started",
            backends=list(self._backends.keys()),
        )

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("health_checker.stopped")

    async def _loop(self) -> None:
        while self._running:
            await asyncio.gather(
                *[self._check(b) for b in self._backends.values()],
                return_exceptions=True,
            )
            interval = get_config().routing.health_check_interval
            await asyncio.sleep(interval)

    async def _check(self, state: BackendState) -> None:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{state.config.url}/api/ps")
                resp.raise_for_status()

            latency_ms = (time.monotonic() - t0) * 1000
            state.healthy = True
            state.last_checked = time.monotonic()
            state.update_ewma(latency_ms)
            BACKEND_HEALTH.labels(backend_id=state.config.id).set(1)
            HEALTH_CHECKS_TOTAL.labels(
                backend_id=state.config.id, result="ok"
            ).inc()
            logger.debug(
                "health_check.ok",
                backend=state.config.id,
                latency_ms=round(latency_ms, 1),
            )
        except Exception as exc:
            state.healthy = False
            BACKEND_HEALTH.labels(backend_id=state.config.id).set(0)
            HEALTH_CHECKS_TOTAL.labels(
                backend_id=state.config.id, result="fail"
            ).inc()
            logger.warning(
                "health_check.failed",
                backend=state.config.id,
                error=str(exc),
            )
