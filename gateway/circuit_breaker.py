from __future__ import annotations
import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Tuple
import structlog

from gateway.metrics import (
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_TRIPS,
)

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    backend_id: str
    error_threshold: float = 0.5
    window_seconds: int = 10
    open_timeout: int = 30
    success_threshold: int = 2

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _call_log: Deque[Tuple[float, bool]] = field(
        default_factory=deque, init=False
    )
    _opened_at: float = field(default=0.0, init=False)
    _half_open_successes: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _requests_total: int = field(default=0, init=False)
    _errors_total: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        CIRCUIT_BREAKER_STATE.labels(backend_id=self.backend_id).set(0)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def is_open(self) -> bool:
        """
        Returns True if this circuit will block the request.
        Side effect: may transition OPEN → HALF_OPEN if timeout elapsed.
        """
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return False

            if self.state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.open_timeout:
                    self._set_state(CircuitState.HALF_OPEN)
                    self._half_open_successes = 0
                    logger.info(
                        "circuit_breaker.half_open",
                        backend=self.backend_id,
                    )
                    return False  # allow probe
                return True  # still open

            # HALF_OPEN: allow probe requests
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._requests_total += 1
            self._call_log.append((time.monotonic(), True))
            self._prune_window()

            if self.state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.success_threshold:
                    self._set_state(CircuitState.CLOSED)
                    self._half_open_successes = 0
                    self._call_log.clear()
                    logger.info(
                        "circuit_breaker.closed",
                        backend=self.backend_id,
                    )

    async def record_failure(self) -> None:
        async with self._lock:
            self._requests_total += 1
            self._errors_total += 1
            self._call_log.append((time.monotonic(), False))
            self._prune_window()

            if self.state == CircuitState.HALF_OPEN:
                self._set_state(CircuitState.OPEN)
                self._opened_at = time.monotonic()
                self._half_open_successes = 0
                logger.warning(
                    "circuit_breaker.reopened",
                    backend=self.backend_id,
                )
                return

            if self.state == CircuitState.CLOSED:
                rate = self._error_rate()
                if rate >= self.error_threshold and len(self._call_log) >= 5:
                    self._set_state(CircuitState.OPEN)
                    self._opened_at = time.monotonic()
                    CIRCUIT_BREAKER_TRIPS.labels(
                        backend_id=self.backend_id
                    ).inc()
                    logger.warning(
                        "circuit_breaker.opened",
                        backend=self.backend_id,
                        error_rate=round(rate, 3),
                    )

    async def force_open(self) -> None:
        async with self._lock:
            self._set_state(CircuitState.OPEN)
            self._opened_at = time.monotonic()
            logger.info("circuit_breaker.force_open", backend=self.backend_id)

    async def force_close(self) -> None:
        async with self._lock:
            self._call_log.clear()
            self._half_open_successes = 0
            self._errors_total = 0
            self._set_state(CircuitState.CLOSED)
            logger.info(
                "circuit_breaker.force_close", backend=self.backend_id
            )

    def get_state(self) -> str:
        return self.state.value

    def error_rate(self) -> float:
        return self._error_rate()

    def stats(self) -> dict:
        return {
            "state": self.state.value,
            "requests_total": self._requests_total,
            "errors_total": self._errors_total,
            "error_rate": round(self._error_rate(), 3),
            "window_size": len(self._call_log),
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _prune_window(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        while self._call_log and self._call_log[0][0] < cutoff:
            self._call_log.popleft()

    def _error_rate(self) -> float:
        self._prune_window()
        if not self._call_log:
            return 0.0
        errors = sum(1 for _, ok in self._call_log if not ok)
        return errors / len(self._call_log)

    def _set_state(self, new_state: CircuitState) -> None:
        self.state = new_state
        state_map = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }
        CIRCUIT_BREAKER_STATE.labels(backend_id=self.backend_id).set(
            state_map[new_state]
        )
