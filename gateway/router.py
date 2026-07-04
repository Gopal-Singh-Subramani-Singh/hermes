from __future__ import annotations
import asyncio
from typing import Dict, List, Optional
import structlog

from gateway.health import BackendState
from gateway.metrics import ROUTING_DECISIONS
from config.settings import RoutingConfig

logger = structlog.get_logger(__name__)


class Router:
    def __init__(
        self,
        backends: Dict[str, BackendState],
        config: RoutingConfig,
    ) -> None:
        self._backends = backends
        self._config = config
        self._rr_index: int = 0
        self._lock = asyncio.Lock()

    async def select(
        self,
        strategy: Optional[str] = None,
        tier: str = "standard",
    ) -> Optional[BackendState]:
        strategy = strategy or self._config.default_strategy
        available = await self._available()

        if not available:
            logger.error("router.no_healthy_backends")
            return None

        backend: Optional[BackendState] = None

        if strategy == "round_robin":
            backend = await self._round_robin(available)
        elif strategy == "latency_aware":
            backend = self._latency_aware(available)
        elif strategy == "least_connections":
            backend = self._least_connections(available)
        elif strategy == "priority":
            backend = await self._priority(available, tier)
        else:
            backend = await self._round_robin(available)

        if backend:
            ROUTING_DECISIONS.labels(
                strategy=strategy,
                backend_id=backend.config.id,
            ).inc()
            logger.debug(
                "router.selected",
                strategy=strategy,
                backend=backend.config.id,
                tier=tier,
                available=len(available),
            )

        return backend

    async def _available(self) -> List[BackendState]:
        result: List[BackendState] = []
        for b in self._backends.values():
            if not b.healthy:
                continue
            if await b.circuit_breaker.is_open():
                continue
            result.append(b)
        return result

    async def _round_robin(
        self, available: List[BackendState]
    ) -> BackendState:
        async with self._lock:
            weighted: List[BackendState] = []
            for b in available:
                weighted.extend([b] * max(1, b.config.weight))
            chosen = weighted[self._rr_index % len(weighted)]
            self._rr_index = (self._rr_index + 1) % len(weighted)
            return chosen

    def _latency_aware(
        self, available: List[BackendState]
    ) -> BackendState:
        return min(available, key=lambda b: b.latency_ewma_ms)

    def _least_connections(
        self, available: List[BackendState]
    ) -> BackendState:
        return min(available, key=lambda b: b.active_connections)

    async def _priority(
        self, available: List[BackendState], tier: str
    ) -> BackendState:
        if tier == "premium":
            return self._latency_aware(available)
        elif tier == "batch":
            return self._least_connections(available)
        else:
            return self._latency_aware(available)

    def backend_ids(self) -> List[str]:
        return list(self._backends.keys())
