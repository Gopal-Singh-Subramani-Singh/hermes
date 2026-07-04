cat > /mnt/user-data/outputs/hermes_FINAL_build_prompt.md << 'PROMPT_END'
# HERMES — Complete Build Prompt
# LLM Inference Gateway with UI, Tests, Load Testing, and Observability
# Target: Claude Code (paste entire file) or any agentic coding assistant
# Hardware: MacBook Air M4 24GB RAM | Budget: $0 | Ollama + MPS backend

---

## IDENTITY & MISSION

You are a senior distributed systems engineer. Your task is to build Hermes — a
production-grade LLM inference gateway — completely from scratch, file by file,
with zero omissions. Every function must be fully implemented. No stubs. No
placeholders. No "TODO" comments. No "implement this later." Every file listed
must be created with complete, working code.

Do not proceed to the next step until the current step is fully complete and
you have confirmed the file exists with full content.

---

## WHAT YOU ARE BUILDING

Hermes is an async API gateway that sits in front of multiple Ollama instances
running on Apple Silicon (MPS). It provides:

1. Unified REST API for chat completions and text completions
2. Four routing strategies: round-robin, latency-aware, least-connections, priority
3. Per-backend circuit breaker (CLOSED → OPEN → HALF-OPEN state machine)
4. Redis token-bucket rate limiter (Lua script, atomic, no race conditions)
5. Priority request queue backed by Redis Sorted Sets (premium > standard > batch)
6. SSE streaming proxy — forward Ollama token stream to client token-by-token
7. Async backend health checker with EWMA latency tracking
8. Prometheus metrics (8 counters, 4 histograms, 7 gauges) on every component
9. Grafana dashboard via Docker Compose
10. Minimal web UI (single HTML file, no framework) for live status and testing
11. Full pytest test suite (38+ tests, all mocked — no real Ollama or Redis needed)
12. Locust load test with chaos testing (kill a backend mid-test)
13. Admin API for live circuit breaker control and strategy switching

Hardware: MacBook Air M4 24GB RAM. No CUDA. Ollama runs on MPS natively.
All infrastructure runs in Docker on localhost. Zero cloud. Zero cost.

---

## COMPLETE FILE TREE

Create every single file in this tree. No exceptions.

```
hermes/
├── gateway/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, all routes
│   ├── router.py            # 4 routing strategies
│   ├── circuit_breaker.py   # 3-state machine
│   ├── rate_limiter.py      # token bucket via Redis Lua
│   ├── queue.py             # priority queue via Redis Sorted Sets
│   ├── health.py            # async health checker + backend state
│   ├── streaming.py         # SSE streaming proxy
│   └── models.py            # all Pydantic request/response models
├── config/
│   ├── __init__.py
│   ├── settings.py          # Pydantic Settings, load_config()
│   └── config.yaml          # full gateway configuration
├── ui/
│   └── index.html           # standalone dashboard UI (no framework)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # all shared fixtures
│   ├── test_circuit_breaker.py   # 9 tests
│   ├── test_rate_limiter.py      # 7 tests
│   ├── test_queue.py             # 8 tests
│   ├── test_router.py            # 8 tests
│   ├── test_health.py            # 4 tests
│   ├── test_streaming.py         # 4 tests
│   └── test_integration.py       # 6 tests
├── load_tests/
│   ├── locustfile.py        # load test + chaos scenarios
│   └── chaos.py             # chaos test runner script
├── dashboards/
│   └── hermes.json          # Grafana dashboard JSON
├── scripts/
│   ├── start_ollama.sh      # start 3 Ollama instances
│   └── verify_setup.sh      # verify all deps are running
├── docker-compose.yml
├── Dockerfile
├── prometheus.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## STEP 1 — requirements.txt

Create `requirements.txt` with these exact contents:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
redis==5.0.8
prometheus-client==0.21.0
pydantic==2.9.2
pydantic-settings==2.5.2
PyYAML==6.0.2
sse-starlette==2.1.3
structlog==24.4.0
tenacity==9.0.0
typer==0.12.5
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
anyio==4.6.2
fakeredis==2.26.1
locust==2.32.2
rich==13.9.2
python-multipart==0.0.12
aiofiles==24.1.0
```

---

## STEP 2 — pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "hermes"
version = "0.1.0"
description = "Distributed LLM Inference Gateway"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
filterwarnings = ["ignore::DeprecationWarning"]
```

---

## STEP 3 — config/config.yaml

```yaml
gateway:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  log_level: "info"

routing:
  default_strategy: "latency_aware"
  ewma_alpha: 0.1
  health_check_interval: 10

backends:
  - id: "llama3_3b"
    url: "http://localhost:11434"
    model: "llama3.2:3b"
    weight: 1
    max_connections: 10
    tags: ["fast", "small"]

  - id: "phi3_mini"
    url: "http://localhost:11435"
    model: "phi3:mini"
    weight: 1
    max_connections: 10
    tags: ["fast", "small"]

  - id: "qwen_7b"
    url: "http://localhost:11436"
    model: "qwen2.5:7b-q4"
    weight: 2
    max_connections: 5
    tags: ["quality", "large"]

rate_limiting:
  enabled: true
  default_rpm: 60
  burst_multiplier: 1.5
  tiers:
    premium: 300
    standard: 60
    batch: 20

circuit_breaker:
  error_threshold: 0.5
  window_seconds: 10
  open_timeout: 30
  success_threshold: 2

queue:
  enabled: true
  max_depth: 1000
  tiers:
    premium: 10
    standard: 5
    batch: 1

redis:
  url: "redis://localhost:6379"
  db: 0
  max_connections: 20

timeouts:
  connect: 5.0
  read: 120.0
  write: 10.0
```

---

## STEP 4 — config/settings.py

Write the complete Pydantic Settings module. Include every model class for every
config section. Include `load_config()` and the `get_config()` singleton:

```python
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Literal
from functools import lru_cache
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BackendConfig(BaseModel):
    id: str
    url: str
    model: str
    weight: int = 1
    max_connections: int = 10
    tags: List[str] = []


class RateLimitTiers(BaseModel):
    premium: int = 300
    standard: int = 60
    batch: int = 20


class RateLimitConfig(BaseModel):
    enabled: bool = True
    default_rpm: int = 60
    burst_multiplier: float = 1.5
    tiers: RateLimitTiers = Field(default_factory=RateLimitTiers)


class CircuitBreakerConfig(BaseModel):
    error_threshold: float = 0.5
    window_seconds: int = 10
    open_timeout: int = 30
    success_threshold: int = 2


class QueueTiers(BaseModel):
    premium: int = 10
    standard: int = 5
    batch: int = 1


class QueueConfig(BaseModel):
    enabled: bool = True
    max_depth: int = 1000
    tiers: QueueTiers = Field(default_factory=QueueTiers)


class RoutingConfig(BaseModel):
    default_strategy: Literal[
        "round_robin", "latency_aware", "least_connections", "priority"
    ] = "latency_aware"
    ewma_alpha: float = 0.1
    health_check_interval: int = 10


class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "info"


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"
    db: int = 0
    max_connections: int = 20


class TimeoutConfig(BaseModel):
    connect: float = 5.0
    read: float = 120.0
    write: float = 10.0


class HermesConfig(BaseModel):
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    backends: List[BackendConfig] = []
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)


_config: Optional[HermesConfig] = None


def load_config(path: str = "config/config.yaml") -> HermesConfig:
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return HermesConfig(**data)
    return HermesConfig()


def get_config() -> HermesConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Used in tests to reset singleton."""
    global _config
    _config = None
```

---

## STEP 5 — gateway/models.py

Write all Pydantic request/response models used across the entire gateway:

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class RequestTier(str, Enum):
    PREMIUM = "premium"
    STANDARD = "standard"
    BATCH = "batch"


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LATENCY_AWARE = "latency_aware"
    LEAST_CONNECTIONS = "least_connections"
    PRIORITY = "priority"


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    tier: RequestTier = RequestTier.STANDARD
    routing_strategy: Optional[RoutingStrategy] = None


class CompletionRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    tier: RequestTier = RequestTier.STANDARD


class BackendStatus(BaseModel):
    id: str
    url: str
    model: str
    healthy: bool
    circuit_state: str
    active_connections: int
    latency_ewma_ms: float
    requests_total: int = 0
    errors_total: int = 0


class GatewayStatusResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    routing_strategy: str
    backends: List[BackendStatus]
    queue_depth: Dict[str, int]
    uptime_seconds: float
    redis_connected: bool


class RouteOverrideRequest(BaseModel):
    strategy: RoutingStrategy


class CircuitOverrideRequest(BaseModel):
    action: Literal["open", "close"]


class HealthResponse(BaseModel):
    status: str
    healthy_backends: int
    total_backends: int
    redis: str
    uptime_seconds: float


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    backend_id: Optional[str] = None
```

---

## STEP 6 — gateway/metrics.py

Write the complete Prometheus metrics module. Every metric used anywhere in the
codebase must be declared here as a module-level singleton:

```python
from __future__ import annotations
import time
from prometheus_client import Counter, Histogram, Gauge

# ── Counters ──────────────────────────────────────────────────────────────────

REQUESTS_TOTAL = Counter(
    "hermes_requests_total",
    "Total requests processed",
    ["backend_id", "model", "status", "tier"],
)

CIRCUIT_BREAKER_TRIPS = Counter(
    "hermes_circuit_breaker_trips_total",
    "Number of times a circuit breaker tripped to OPEN",
    ["backend_id"],
)

RATE_LIMIT_REJECTIONS = Counter(
    "hermes_rate_limit_rejections_total",
    "Requests rejected by rate limiter",
    ["tier"],
)

ROUTING_DECISIONS = Counter(
    "hermes_routing_decisions_total",
    "Routing decisions per strategy and backend",
    ["strategy", "backend_id"],
)

QUEUE_ENQUEUED = Counter(
    "hermes_queue_enqueued_total",
    "Requests added to the priority queue",
    ["tier"],
)

QUEUE_DEQUEUED = Counter(
    "hermes_queue_dequeued_total",
    "Requests dispatched from the priority queue",
    ["tier"],
)

STREAM_CHUNKS_TOTAL = Counter(
    "hermes_stream_chunks_total",
    "Total SSE chunks proxied to clients",
    ["backend_id"],
)

HEALTH_CHECKS_TOTAL = Counter(
    "hermes_health_checks_total",
    "Total backend health check attempts",
    ["backend_id", "result"],
)

# ── Histograms ─────────────────────────────────────────────────────────────────

REQUEST_DURATION = Histogram(
    "hermes_request_duration_seconds",
    "End-to-end request latency in seconds",
    ["backend_id", "model", "tier"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

BACKEND_LATENCY = Histogram(
    "hermes_backend_latency_seconds",
    "Raw backend response latency in seconds",
    ["backend_id"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

QUEUE_WAIT_TIME = Histogram(
    "hermes_queue_wait_seconds",
    "Seconds a request spends waiting in the priority queue",
    ["tier"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)

TTFT = Histogram(
    "hermes_time_to_first_token_seconds",
    "Time from request start to first streamed token",
    ["backend_id"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

# ── Gauges ─────────────────────────────────────────────────────────────────────

CIRCUIT_BREAKER_STATE = Gauge(
    "hermes_circuit_breaker_state",
    "Circuit breaker state: 0=CLOSED, 1=OPEN, 2=HALF_OPEN",
    ["backend_id"],
)

ACTIVE_CONNECTIONS = Gauge(
    "hermes_active_connections",
    "Active in-flight requests per backend",
    ["backend_id"],
)

TOKEN_BUCKET_REMAINING = Gauge(
    "hermes_token_bucket_remaining",
    "Remaining tokens in rate limit bucket",
    ["tier"],
)

QUEUE_DEPTH = Gauge(
    "hermes_queue_depth",
    "Current request queue depth per tier",
    ["tier"],
)

BACKEND_HEALTH = Gauge(
    "hermes_backend_health",
    "Backend liveness: 1=healthy, 0=unhealthy",
    ["backend_id"],
)

LATENCY_EWMA = Gauge(
    "hermes_latency_ewma_ms",
    "Exponentially weighted moving average of backend latency in ms",
    ["backend_id"],
)

UPTIME = Gauge("hermes_uptime_seconds", "Gateway process uptime in seconds")

_START_TIME = time.time()


def update_uptime() -> float:
    elapsed = time.time() - _START_TIME
    UPTIME.set(elapsed)
    return elapsed
```

---

## STEP 7 — gateway/circuit_breaker.py

Write the full 3-state circuit breaker. Each backend instance gets its own
CircuitBreaker. All state transitions must be protected by asyncio.Lock.
Record the full implementation — all methods, all edge cases:

```python
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
```

---

## STEP 8 — gateway/rate_limiter.py

Implement the full token bucket rate limiter. Use a Redis Lua script loaded via
SCRIPT LOAD / EVALSHA for atomic check-and-consume. Include retry logic for
script cache misses (NOSCRIPT error). Include `get_remaining()` and `reset()`:

```python
from __future__ import annotations
import time
from typing import Optional, Tuple
import redis.asyncio as aioredis
import structlog

from gateway.metrics import RATE_LIMIT_REJECTIONS, TOKEN_BUCKET_REMAINING
from config.settings import get_config

logger = structlog.get_logger(__name__)

# Atomic token bucket: check-and-consume in a single Redis round-trip.
# Returns [allowed (0/1), remaining_tokens (int)]
_LUA_CONSUME = """
local key          = KEYS[1]
local capacity     = tonumber(ARGV[1])
local refill_rate  = tonumber(ARGV[2])
local now          = tonumber(ARGV[3])
local requested    = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens      = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, math.floor(tokens)}
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {0, math.floor(tokens)}
end
"""


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._sha: Optional[str] = None

    async def _load_script(self) -> str:
        if self._sha is None:
            self._sha = await self._redis.script_load(_LUA_CONSUME)
        return self._sha

    async def _evalsha(self, key: str, capacity: int,
                       refill_rate: float, now: float,
                       requested: int = 1) -> Tuple[bool, int]:
        sha = await self._load_script()
        try:
            result = await self._redis.evalsha(
                sha, 1, key, capacity, refill_rate, now, requested
            )
        except aioredis.ResponseError as exc:
            if "NOSCRIPT" in str(exc):
                self._sha = None
                sha = await self._load_script()
                result = await self._redis.evalsha(
                    sha, 1, key, capacity, refill_rate, now, requested
                )
            else:
                raise
        return bool(int(result[0])), int(result[1])

    async def is_allowed(
        self,
        tier: str = "standard",
        key_suffix: str = "global",
    ) -> bool:
        cfg = get_config().rate_limiting
        if not cfg.enabled:
            return True

        rpm = getattr(cfg.tiers, tier, cfg.default_rpm)
        capacity = int(rpm * cfg.burst_multiplier)
        refill_rate = rpm / 60.0
        redis_key = f"hermes:rl:{tier}:{key_suffix}"

        allowed, remaining = await self._evalsha(
            redis_key, capacity, refill_rate, time.time()
        )

        TOKEN_BUCKET_REMAINING.labels(tier=tier).set(remaining)
        if not allowed:
            RATE_LIMIT_REJECTIONS.labels(tier=tier).inc()
            logger.debug(
                "rate_limit.rejected",
                tier=tier,
                remaining=remaining,
                key=redis_key,
            )
        return allowed

    async def get_remaining(
        self, tier: str = "standard", key_suffix: str = "global"
    ) -> int:
        redis_key = f"hermes:rl:{tier}:{key_suffix}"
        raw = await self._redis.hget(redis_key, "tokens")
        if raw is None:
            cfg = get_config().rate_limiting
            rpm = getattr(cfg.tiers, tier, cfg.default_rpm)
            return int(rpm * cfg.burst_multiplier)
        return int(float(raw))

    async def reset(
        self, tier: str = "standard", key_suffix: str = "global"
    ) -> None:
        redis_key = f"hermes:rl:{tier}:{key_suffix}"
        await self._redis.delete(redis_key)
        logger.info("rate_limit.reset", tier=tier, key=redis_key)
```

---

## STEP 9 — gateway/health.py

Write the full health checker module. BackendState holds all runtime state for
one backend. HealthChecker runs a background asyncio task polling every backend:

```python
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
```

---

## STEP 10 — gateway/queue.py

Implement the full priority queue backed by Redis Sorted Sets. Score is designed
so premium > standard > batch and FIFO within each tier. Include full
depth tracking, TTL on payload keys, and clear():

```python
from __future__ import annotations
import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
import redis.asyncio as aioredis
import structlog

from gateway.metrics import (
    QUEUE_DEPTH,
    QUEUE_ENQUEUED,
    QUEUE_DEQUEUED,
    QUEUE_WAIT_TIME,
)
from config.settings import get_config

logger = structlog.get_logger(__name__)

_QUEUE_KEY = "hermes:queue:zset"
_DATA_PREFIX = "hermes:queue:data:"
_PAYLOAD_TTL = 300  # 5 minutes


@dataclass
class QueuedRequest:
    request_id: str
    tier: str
    payload: Dict
    enqueued_at: float
    score: float


class RequestQueue:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _score(self, tier: str) -> float:
        cfg = get_config().queue
        tier_priority = getattr(cfg.tiers, tier, cfg.tiers.standard)
        # Higher tier_priority → higher score → dequeued first
        # Subtract timestamp so older requests win within same tier (FIFO)
        return tier_priority * 1e12 - time.time()

    async def enqueue(
        self, payload: Dict, tier: str = "standard"
    ) -> str:
        cfg = get_config().queue
        depth = await self._redis.zcard(_QUEUE_KEY)
        if depth >= cfg.max_depth:
            raise RuntimeError(
                f"Queue full: {depth}/{cfg.max_depth}"
            )

        request_id = str(uuid.uuid4())
        score = self._score(tier)
        now = time.time()

        data = json.dumps(
            {"tier": tier, "payload": payload, "enqueued_at": now}
        )

        pipe = self._redis.pipeline()
        pipe.zadd(_QUEUE_KEY, {request_id: score})
        pipe.setex(f"{_DATA_PREFIX}{request_id}", _PAYLOAD_TTL, data)
        await pipe.execute()

        QUEUE_ENQUEUED.labels(tier=tier).inc()
        await self._update_depth_gauge(tier)

        logger.debug(
            "queue.enqueued",
            request_id=request_id,
            tier=tier,
            queue_depth=depth + 1,
        )
        return request_id

    async def dequeue(self) -> Optional[QueuedRequest]:
        result = await self._redis.zpopmax(_QUEUE_KEY, count=1)
        if not result:
            return None

        raw_id, score = result[0]
        request_id = (
            raw_id if isinstance(raw_id, str) else raw_id.decode()
        )

        raw_data = await self._redis.getdel(
            f"{_DATA_PREFIX}{request_id}"
        )
        if raw_data is None:
            logger.warning(
                "queue.data_missing", request_id=request_id
            )
            return None

        data = json.loads(raw_data)
        tier = data["tier"]
        wait = time.time() - data["enqueued_at"]

        QUEUE_DEQUEUED.labels(tier=tier).inc()
        QUEUE_WAIT_TIME.labels(tier=tier).observe(wait)
        await self._update_depth_gauge(tier)

        return QueuedRequest(
            request_id=request_id,
            tier=tier,
            payload=data["payload"],
            enqueued_at=data["enqueued_at"],
            score=score,
        )

    async def depth(self) -> int:
        return await self._redis.zcard(_QUEUE_KEY)

    async def depth_by_tier(self) -> Dict[str, int]:
        return {
            "premium": await self._tier_count("premium"),
            "standard": await self._tier_count("standard"),
            "batch": await self._tier_count("batch"),
        }

    async def clear(self) -> None:
        await self._redis.delete(_QUEUE_KEY)

    async def _tier_count(self, tier: str) -> int:
        cfg = get_config().queue
        base = getattr(cfg.tiers, tier, cfg.tiers.standard) * 1e12
        return await self._redis.zcount(
            _QUEUE_KEY, base - 1e12, base
        )

    async def _update_depth_gauge(self, tier: str) -> None:
        count = await self._tier_count(tier)
        QUEUE_DEPTH.labels(tier=tier).set(count)
```

---

## STEP 11 — gateway/router.py

Implement all 4 routing strategies. Include async backend selection, weighted
round-robin, EWMA latency-aware, least-connections, and priority routing.
All selection methods must skip unhealthy or circuit-open backends:

```python
from __future__ import annotations
import asyncio
import itertools
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
```

---

## STEP 12 — gateway/streaming.py

Implement the SSE streaming proxy. Forward Ollama's NDJSON stream as
Server-Sent Events. Track TTFT, emit chunk metrics, handle errors gracefully,
always decrement connections in finally:

```python
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
```

---

## STEP 13 — gateway/main.py

Write the complete FastAPI application. Include:
- lifespan context manager (startup/shutdown)
- AppState dataclass holding all singleton objects
- request logging middleware
- /v1/chat/completions (streaming + non-streaming)
- /v1/completions
- /health
- /status
- /metrics (Prometheus)
- /admin/routing/strategy (POST)
- /admin/circuit-breaker/{backend_id}/open (POST)
- /admin/circuit-breaker/{backend_id}/close (POST)
- /admin/queue/depth (GET)
- /admin/rate-limit/reset (POST)
- /ui (GET, serves index.html)
- CORS middleware for the UI
- Full error handling with structured logging

```python
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
```

---

## STEP 14 — ui/index.html

Write the complete single-file dashboard UI. No React. No Vue. Pure HTML + CSS +
vanilla JS. The UI must:

1. Auto-refresh every 5 seconds by polling `/status`
2. Show a status card for each backend with: health indicator, circuit state
   (colored badge), EWMA latency, active connections, request/error counts
3. Show gateway uptime, routing strategy, Redis status
4. Show queue depth bars for premium/standard/batch
5. Have a chat test panel: textarea for message, model selector, tier selector,
   send button, displays response
6. Have admin controls: change routing strategy dropdown + apply button,
   per-backend circuit breaker open/close buttons
7. Show a live request log (last 10 requests with timestamp, backend, latency)
8. Dark-mode aware using CSS prefers-color-scheme
9. No external dependencies (no CDN, fully self-contained)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes — Inference Gateway</title>
<style>
  :root {
    --bg: #ffffff;
    --bg2: #f5f5f4;
    --bg3: #e8e8e6;
    --border: rgba(0,0,0,0.1);
    --text: #1a1a18;
    --text2: #6b6b67;
    --text3: #9b9b96;
    --accent: #185fa5;
    --green: #1D9E75;
    --red: #D85A30;
    --amber: #BA7517;
    --blue: #378ADD;
    --radius: 10px;
    --radius-sm: 6px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1a1a18;
      --bg2: #232320;
      --bg3: #2e2e2b;
      --border: rgba(255,255,255,0.1);
      --text: #e8e8e4;
      --text2: #9b9b96;
      --text3: #6b6b67;
      --accent: #85b7eb;
      --green: #5dcaa5;
      --red: #f0997b;
      --amber: #ef9f27;
      --blue: #85b7eb;
    }
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg2);
    color: var(--text);
    font-size: 14px;
    line-height: 1.5;
  }
  header {
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .logo { font-size: 16px; font-weight: 600; letter-spacing: -0.3px; }
  .logo span { color: var(--accent); }
  .header-right { display: flex; align-items: center; gap: 12px; }
  .badge {
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .badge-green { background: rgba(29,158,117,0.15); color: var(--green); }
  .badge-red { background: rgba(216,90,48,0.15); color: var(--red); }
  .badge-amber { background: rgba(186,117,23,0.15); color: var(--amber); }
  .badge-blue { background: rgba(55,138,221,0.15); color: var(--blue); }
  .badge-gray { background: var(--bg3); color: var(--text2); }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
  .refresh-indicator { font-size: 11px; color: var(--text3); }
  main { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  @media (max-width: 768px) {
    .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
  }
  .card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
  }
  .card-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text2);
    margin-bottom: 12px;
  }
  .metric-val { font-size: 28px; font-weight: 600; line-height: 1; }
  .metric-sub { font-size: 12px; color: var(--text3); margin-top: 4px; }
  section { margin-bottom: 24px; }
  .section-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text3);
    margin-bottom: 10px;
  }
  .backend-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .backend-header { display: flex; align-items: center; justify-content: space-between; }
  .backend-name { font-weight: 600; font-size: 14px; }
  .backend-model { font-size: 12px; color: var(--text2); font-family: monospace; }
  .kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .kv { display: flex; flex-direction: column; gap: 1px; }
  .kv-label { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.05em; }
  .kv-value { font-size: 13px; font-weight: 500; }
  .cb-controls { display: flex; gap: 6px; margin-top: 4px; }
  button {
    padding: 5px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg2);
    color: var(--text);
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s;
    font-weight: 500;
  }
  button:hover { background: var(--bg3); }
  button.btn-danger { border-color: rgba(216,90,48,0.3); color: var(--red); }
  button.btn-success { border-color: rgba(29,158,117,0.3); color: var(--green); }
  button.btn-primary {
    background: var(--accent);
    color: white;
    border-color: transparent;
  }
  button.btn-primary:hover { opacity: 0.9; }
  .queue-bar-container { margin-top: 6px; }
  .queue-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .queue-bar-label { font-size: 12px; color: var(--text2); min-width: 60px; }
  .queue-bar-track { flex: 1; height: 6px; background: var(--bg3); border-radius: 3px; overflow: hidden; }
  .queue-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
  .queue-bar-count { font-size: 12px; font-weight: 600; min-width: 24px; text-align: right; }
  .chat-panel {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
  }
  .chat-controls { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
  select {
    padding: 5px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg2);
    color: var(--text);
    font-size: 12px;
    cursor: pointer;
  }
  textarea {
    width: 100%;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg2);
    color: var(--text);
    font-size: 13px;
    resize: vertical;
    min-height: 80px;
    margin-bottom: 8px;
    font-family: inherit;
  }
  textarea:focus, select:focus, input:focus {
    outline: none;
    border-color: var(--accent);
  }
  .chat-response {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-size: 13px;
    min-height: 60px;
    max-height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 8px;
    display: none;
    color: var(--text);
    line-height: 1.6;
  }
  .chat-meta { font-size: 11px; color: var(--text3); margin-top: 6px; }
  .log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .log-table th {
    text-align: left;
    padding: 4px 8px;
    color: var(--text3);
    font-weight: 500;
    border-bottom: 1px solid var(--border);
  }
  .log-table td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }
  .log-table tr:last-child td { border-bottom: none; }
  .mono { font-family: 'SF Mono', monospace; }
  .admin-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
  }
  .status-dot.green { background: var(--green); }
  .status-dot.red { background: var(--red); }
  .status-dot.amber { background: var(--amber); }
  .divider { height: 1px; background: var(--border); margin: 16px 0; }
  .error-msg { color: var(--red); font-size: 12px; margin-top: 6px; }
  .loading { color: var(--text3); font-size: 13px; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
</style>
</head>
<body>

<header>
  <div class="logo">⚡ <span>Hermes</span></div>
  <div class="header-right">
    <span id="gateway-status-badge" class="badge badge-gray">
      <span class="dot"></span> Connecting...
    </span>
    <span class="refresh-indicator" id="last-refresh">—</span>
  </div>
</header>

<main>

  <!-- Metrics row -->
  <section>
    <div class="grid-4">
      <div class="card">
        <div class="card-title">Healthy backends</div>
        <div class="metric-val" id="m-healthy">—</div>
        <div class="metric-sub" id="m-total">of — total</div>
      </div>
      <div class="card">
        <div class="card-title">Routing strategy</div>
        <div class="metric-val" style="font-size:16px;padding-top:6px" id="m-strategy">—</div>
        <div class="metric-sub">current active strategy</div>
      </div>
      <div class="card">
        <div class="card-title">Uptime</div>
        <div class="metric-val" id="m-uptime">—</div>
        <div class="metric-sub">seconds</div>
      </div>
      <div class="card">
        <div class="card-title">Redis</div>
        <div class="metric-val" style="font-size:16px;padding-top:6px" id="m-redis">—</div>
        <div class="metric-sub">connection status</div>
      </div>
    </div>
  </section>

  <!-- Backends -->
  <section>
    <div class="section-title">Backends</div>
    <div class="grid-3" id="backends-grid">
      <div class="card"><div class="loading">Loading backends…</div></div>
    </div>
  </section>

  <!-- Queue depth -->
  <section>
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Request queue depth</div>
        <div class="queue-bar-container" id="queue-bars">
          <div class="queue-bar-row">
            <span class="queue-bar-label">Premium</span>
            <div class="queue-bar-track"><div class="queue-bar-fill" id="q-premium-bar" style="width:0%;background:var(--green)"></div></div>
            <span class="queue-bar-count" id="q-premium">0</span>
          </div>
          <div class="queue-bar-row">
            <span class="queue-bar-label">Standard</span>
            <div class="queue-bar-track"><div class="queue-bar-fill" id="q-standard-bar" style="width:0%;background:var(--blue)"></div></div>
            <span class="queue-bar-count" id="q-standard">0</span>
          </div>
          <div class="queue-bar-row">
            <span class="queue-bar-label">Batch</span>
            <div class="queue-bar-track"><div class="queue-bar-fill" id="q-batch-bar" style="width:0%;background:var(--amber)"></div></div>
            <span class="queue-bar-count" id="q-batch">0</span>
          </div>
        </div>
      </div>

      <!-- Admin: routing strategy -->
      <div class="card">
        <div class="card-title">Admin — routing strategy</div>
        <div class="admin-row" style="margin-bottom:12px">
          <select id="strategy-select">
            <option value="round_robin">Round Robin</option>
            <option value="latency_aware">Latency Aware</option>
            <option value="least_connections">Least Connections</option>
            <option value="priority">Priority</option>
          </select>
          <button class="btn-primary" onclick="applyStrategy()">Apply</button>
          <span id="strategy-msg" class="chat-meta"></span>
        </div>
        <div class="divider"></div>
        <div class="card-title" style="margin-bottom:8px">Rate limit</div>
        <div class="admin-row">
          <select id="rl-tier">
            <option value="standard">Standard</option>
            <option value="premium">Premium</option>
            <option value="batch">Batch</option>
          </select>
          <button onclick="resetRL()">Reset bucket</button>
          <span id="rl-msg" class="chat-meta"></span>
        </div>
      </div>
    </div>
  </section>

  <!-- Chat test panel -->
  <section>
    <div class="section-title">Chat test</div>
    <div class="chat-panel">
      <div class="chat-controls">
        <select id="chat-tier">
          <option value="standard">Standard</option>
          <option value="premium">Premium</option>
          <option value="batch">Batch</option>
        </select>
        <select id="chat-strategy">
          <option value="">Default strategy</option>
          <option value="round_robin">Round Robin</option>
          <option value="latency_aware">Latency Aware</option>
          <option value="least_connections">Least Connections</option>
          <option value="priority">Priority</option>
        </select>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--text2)">
          <input type="checkbox" id="chat-stream"> Stream
        </label>
      </div>
      <textarea id="chat-input" placeholder="Type a message to test the gateway…">What is a circuit breaker pattern in distributed systems?</textarea>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn-primary" onclick="sendChat()">Send request</button>
        <button onclick="clearChat()">Clear</button>
        <span id="chat-status" class="chat-meta"></span>
      </div>
      <div class="chat-response" id="chat-response"></div>
    </div>
  </section>

  <!-- Request log -->
  <section>
    <div class="section-title">Request log (last 10)</div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="log-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Backend</th>
            <th>Tier</th>
            <th>Latency</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="log-tbody">
          <tr><td colspan="5" style="color:var(--text3);padding:12px 8px">No requests yet</td></tr>
        </tbody>
      </table>
    </div>
  </section>

</main>

<script>
const BASE = window.location.origin;
const logs = [];

// ── Refresh loop ──────────────────────────────────────────────────────────────

async function refresh() {
  try {
    const resp = await fetch(`${BASE}/status`);
    if (!resp.ok) throw new Error(resp.status);
    const data = await resp.json();
    renderStatus(data);
    document.getElementById('last-refresh').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById('gateway-status-badge').className = 'badge badge-red';
    document.getElementById('gateway-status-badge').innerHTML =
      '<span class="dot"></span> Offline';
  }
}

function renderStatus(data) {
  // Header badge
  const healthy = data.backends.filter(b => b.healthy).length;
  const badge = document.getElementById('gateway-status-badge');
  badge.className = healthy > 0 ? 'badge badge-green' : 'badge badge-red';
  badge.innerHTML = `<span class="dot"></span> ${healthy > 0 ? 'Online' : 'Degraded'}`;

  // Metrics
  document.getElementById('m-healthy').textContent = healthy;
  document.getElementById('m-total').textContent = `of ${data.backends.length} total`;
  document.getElementById('m-strategy').textContent =
    data.routing_strategy.replace(/_/g, ' ');
  document.getElementById('m-uptime').textContent =
    Math.round(data.uptime_seconds);
  const redisBadge = document.getElementById('m-redis');
  redisBadge.textContent = data.redis_connected ? 'Connected' : 'Error';
  redisBadge.style.color = data.redis_connected ? 'var(--green)' : 'var(--red)';

  // Backends grid
  const grid = document.getElementById('backends-grid');
  grid.innerHTML = data.backends.map(b => {
    const cbColor = {
      CLOSED: 'green', OPEN: 'red', HALF_OPEN: 'amber'
    }[b.circuit_state] || 'gray';
    const healthDot = b.healthy ? 'green' : 'red';
    return `
      <div class="backend-card">
        <div class="backend-header">
          <div>
            <div class="backend-name">
              <span class="status-dot ${healthDot}"></span>
              ${b.id}
            </div>
            <div class="backend-model">${b.model}</div>
          </div>
          <span class="badge badge-${cbColor}">${b.circuit_state}</span>
        </div>
        <div class="kv-grid">
          <div class="kv">
            <span class="kv-label">EWMA latency</span>
            <span class="kv-value">${b.latency_ewma_ms} ms</span>
          </div>
          <div class="kv">
            <span class="kv-label">Active conns</span>
            <span class="kv-value">${b.active_connections}</span>
          </div>
          <div class="kv">
            <span class="kv-label">Requests</span>
            <span class="kv-value">${b.requests_total}</span>
          </div>
          <div class="kv">
            <span class="kv-label">Errors</span>
            <span class="kv-value" style="color:${b.errors_total > 0 ? 'var(--red)' : 'inherit'}">${b.errors_total}</span>
          </div>
        </div>
        <div class="cb-controls">
          <button class="btn-danger" onclick="cbAction('${b.id}','open')">Trip open</button>
          <button class="btn-success" onclick="cbAction('${b.id}','close')">Force close</button>
        </div>
      </div>`;
  }).join('');

  // Queue bars
  const qd = data.queue_depth;
  const maxQ = Math.max(1, qd.premium + qd.standard + qd.batch);
  setQBar('premium', qd.premium, maxQ);
  setQBar('standard', qd.standard, maxQ);
  setQBar('batch', qd.batch, maxQ);
}

function setQBar(tier, count, max) {
  document.getElementById(`q-${tier}`).textContent = count;
  document.getElementById(`q-${tier}-bar`).style.width =
    Math.round((count / max) * 100) + '%';
}

// ── Admin actions ─────────────────────────────────────────────────────────────

async function cbAction(backendId, action) {
  try {
    const r = await fetch(
      `${BASE}/admin/circuit-breaker/${backendId}/${action}`, {method:'POST'}
    );
    const d = await r.json();
    refresh();
  } catch(e) { alert('Error: ' + e.message); }
}

async function applyStrategy() {
  const strategy = document.getElementById('strategy-select').value;
  try {
    await fetch(`${BASE}/admin/routing/strategy`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({strategy})
    });
    document.getElementById('strategy-msg').textContent = '✓ Applied';
    setTimeout(() => document.getElementById('strategy-msg').textContent = '', 2000);
    refresh();
  } catch(e) {
    document.getElementById('strategy-msg').textContent = 'Error';
  }
}

async function resetRL() {
  const tier = document.getElementById('rl-tier').value;
  try {
    await fetch(`${BASE}/admin/rate-limit/reset?tier=${tier}`, {method:'POST'});
    document.getElementById('rl-msg').textContent = `✓ ${tier} reset`;
    setTimeout(() => document.getElementById('rl-msg').textContent = '', 2000);
  } catch(e) {
    document.getElementById('rl-msg').textContent = 'Error';
  }
}

// ── Chat test ─────────────────────────────────────────────────────────────────

async function sendChat() {
  const msg = document.getElementById('chat-input').value.trim();
  if (!msg) return;

  const tier = document.getElementById('chat-tier').value;
  const strategyRaw = document.getElementById('chat-strategy').value;
  const stream = document.getElementById('chat-stream').checked;

  const payload = {
    messages: [{role:'user', content: msg}],
    tier,
    stream,
    temperature: 0.7,
    ...(strategyRaw ? {routing_strategy: strategyRaw} : {})
  };

  const statusEl = document.getElementById('chat-status');
  const respEl = document.getElementById('chat-response');
  respEl.style.display = 'block';
  respEl.textContent = '';
  statusEl.textContent = 'Sending…';

  const t0 = Date.now();

  try {
    const resp = await fetch(`${BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const err = await resp.json();
      respEl.textContent = `Error ${resp.status}: ${JSON.stringify(err)}`;
      statusEl.textContent = `Failed (${resp.status})`;
      return;
    }

    const backendId = resp.headers.get('X-Backend-ID') || '?';

    if (stream) {
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let text = '';
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        const chunk = dec.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') break;
          try {
            const parsed = JSON.parse(raw);
            const content = parsed.choices?.[0]?.delta?.content || '';
            text += content;
            respEl.textContent = text;
          } catch {}
        }
      }
      const ms = Date.now() - t0;
      statusEl.textContent = `Done · ${backendId} · ${ms}ms (streamed)`;
      pushLog(backendId, tier, ms, 'stream');
    } else {
      const data = await resp.json();
      const content = data.choices?.[0]?.message?.content || JSON.stringify(data);
      respEl.textContent = content;
      const ms = Date.now() - t0;
      statusEl.textContent = `Done · ${data.backend_id || backendId} · ${ms}ms`;
      pushLog(data.backend_id || backendId, tier, ms, 'ok');
    }
  } catch(e) {
    respEl.textContent = 'Network error: ' + e.message;
    statusEl.textContent = 'Error';
    pushLog('?', tier, Date.now() - t0, 'error');
  }
}

function clearChat() {
  document.getElementById('chat-input').value = '';
  document.getElementById('chat-response').style.display = 'none';
  document.getElementById('chat-response').textContent = '';
  document.getElementById('chat-status').textContent = '';
}

// ── Request log ───────────────────────────────────────────────────────────────

function pushLog(backend, tier, ms, status) {
  logs.unshift({
    time: new Date().toLocaleTimeString(),
    backend, tier,
    ms: Math.round(ms),
    status
  });
  if (logs.length > 10) logs.pop();
  renderLogs();
}

function renderLogs() {
  const tbody = document.getElementById('log-tbody');
  if (logs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text3);padding:12px 8px">No requests yet</td></tr>';
    return;
  }
  tbody.innerHTML = logs.map(l => {
    const sc = l.status === 'ok' || l.status === 'stream' ? 'green' : 'red';
    return `<tr>
      <td class="mono">${l.time}</td>
      <td class="mono">${l.backend}</td>
      <td><span class="badge badge-gray">${l.tier}</span></td>
      <td class="mono">${l.ms}ms</td>
      <td><span class="badge badge-${sc}">${l.status}</span></td>
    </tr>`;
  }).join('');
}

// ── Init ──────────────────────────────────────────────────────────────────────

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
```

---

## STEP 15 — tests/conftest.py

Write all shared pytest fixtures. Use fakeredis for all Redis-dependent tests.
No real Ollama or Redis needed:

```python
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
```

---

## STEP 16 — tests/test_circuit_breaker.py

```python
from __future__ import annotations
import asyncio
import pytest
from gateway.circuit_breaker import CircuitBreaker, CircuitState


@pytest.mark.asyncio
async def test_initial_state_is_closed(circuit_breaker):
    assert circuit_breaker.state == CircuitState.CLOSED
    assert not await circuit_breaker.is_open()


@pytest.mark.asyncio
async def test_does_not_open_below_minimum_calls(circuit_breaker):
    # Need at least 5 calls in window before opening
    for _ in range(4):
        await circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold(circuit_breaker):
    for _ in range(2):
        await circuit_breaker.record_success()
    for _ in range(5):
        await circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.OPEN
    assert await circuit_breaker.is_open()


@pytest.mark.asyncio
async def test_transitions_to_half_open_after_timeout(circuit_breaker):
    for _ in range(2):
        await circuit_breaker.record_success()
    for _ in range(5):
        await circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.OPEN

    await asyncio.sleep(1.1)  # open_timeout=1 in fixture
    is_open = await circuit_breaker.is_open()
    assert not is_open
    assert circuit_breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_closes_on_successes_in_half_open(circuit_breaker):
    for _ in range(2):
        await circuit_breaker.record_success()
    for _ in range(5):
        await circuit_breaker.record_failure()
    await asyncio.sleep(1.1)
    await circuit_breaker.is_open()
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    await circuit_breaker.record_success()
    await circuit_breaker.record_success()  # success_threshold=2
    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_reopens_on_failure_in_half_open(circuit_breaker):
    for _ in range(2):
        await circuit_breaker.record_success()
    for _ in range(5):
        await circuit_breaker.record_failure()
    await asyncio.sleep(1.1)
    await circuit_breaker.is_open()
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    await circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_force_open_and_close(circuit_breaker):
    await circuit_breaker.force_open()
    assert circuit_breaker.state == CircuitState.OPEN
    assert await circuit_breaker.is_open()

    await circuit_breaker.force_close()
    assert circuit_breaker.state == CircuitState.CLOSED
    assert not await circuit_breaker.is_open()


@pytest.mark.asyncio
async def test_get_state_returns_string(circuit_breaker):
    assert circuit_breaker.get_state() == "CLOSED"
    await circuit_breaker.force_open()
    assert circuit_breaker.get_state() == "OPEN"


@pytest.mark.asyncio
async def test_stats_returns_counts(circuit_breaker):
    await circuit_breaker.record_success()
    await circuit_breaker.record_failure()
    s = circuit_breaker.stats()
    assert s["requests_total"] == 2
    assert s["errors_total"] == 1
    assert "error_rate" in s
    assert "state" in s
```

---

## STEP 17 — tests/test_rate_limiter.py

```python
from __future__ import annotations
import pytest
from gateway.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_allows_first_request(rate_limiter):
    result = await rate_limiter.is_allowed(tier="standard")
    assert result is True


@pytest.mark.asyncio
async def test_rejects_after_burst_exhausted(rate_limiter):
    # standard = 60rpm, burst = 1.5x = 90 tokens
    results = [
        await rate_limiter.is_allowed(tier="standard", key_suffix="burst_test")
        for _ in range(150)
    ]
    allowed = sum(r for r in results)
    rejected = len(results) - allowed
    assert allowed <= 95      # burst cap
    assert rejected >= 50     # definitely hits the cap


@pytest.mark.asyncio
async def test_premium_allows_more_than_batch(rate_limiter):
    premium_allowed = 0
    batch_allowed = 0
    for _ in range(350):
        if await rate_limiter.is_allowed(tier="premium", key_suffix="cmp_p"):
            premium_allowed += 1
        if await rate_limiter.is_allowed(tier="batch", key_suffix="cmp_b"):
            batch_allowed += 1
    assert premium_allowed > batch_allowed


@pytest.mark.asyncio
async def test_different_key_suffixes_independent(rate_limiter):
    for _ in range(150):
        await rate_limiter.is_allowed(tier="batch", key_suffix="sink")
    # Different key should still have tokens
    assert await rate_limiter.is_allowed(tier="batch", key_suffix="fresh")


@pytest.mark.asyncio
async def test_reset_refills_bucket(rate_limiter):
    for _ in range(150):
        await rate_limiter.is_allowed(tier="batch", key_suffix="reset_test")

    before = await rate_limiter.get_remaining(tier="batch", key_suffix="reset_test")
    await rate_limiter.reset(tier="batch", key_suffix="reset_test")
    after = await rate_limiter.get_remaining(tier="batch", key_suffix="reset_test")
    assert after > before


@pytest.mark.asyncio
async def test_disabled_always_allows(fake_redis, test_config):
    from unittest.mock import patch
    from config.settings import RateLimitConfig

    cfg = test_config.model_copy(
        update={"rate_limiting": RateLimitConfig(enabled=False)}
    )
    with patch("gateway.rate_limiter.get_config", return_value=cfg):
        rl = RateLimiter(fake_redis)
        for _ in range(500):
            assert await rl.is_allowed() is True


@pytest.mark.asyncio
async def test_get_remaining_returns_int(rate_limiter):
    remaining = await rate_limiter.get_remaining(tier="standard")
    assert isinstance(remaining, int)
    assert remaining > 0
```

---

## STEP 18 — tests/test_queue.py

```python
from __future__ import annotations
import asyncio
import pytest
from gateway.queue import RequestQueue


@pytest.mark.asyncio
async def test_enqueue_returns_uuid(request_queue):
    req_id = await request_queue.enqueue({"prompt": "hello"}, tier="standard")
    assert isinstance(req_id, str)
    assert len(req_id) == 36


@pytest.mark.asyncio
async def test_dequeue_returns_enqueued_payload(request_queue):
    payload = {"prompt": "test", "model": "llama"}
    req_id = await request_queue.enqueue(payload, tier="standard")
    item = await request_queue.dequeue()
    assert item is not None
    assert item.request_id == req_id
    assert item.payload["prompt"] == "test"
    assert item.tier == "standard"


@pytest.mark.asyncio
async def test_premium_before_standard(request_queue):
    await request_queue.enqueue({"order": 1}, tier="standard")
    await asyncio.sleep(0.01)
    await request_queue.enqueue({"order": 2}, tier="premium")

    first = await request_queue.dequeue()
    assert first.tier == "premium"
    second = await request_queue.dequeue()
    assert second.tier == "standard"


@pytest.mark.asyncio
async def test_fifo_within_tier(request_queue):
    for i in range(3):
        await request_queue.enqueue({"order": i}, tier="standard")
        await asyncio.sleep(0.01)

    orders = [(await request_queue.dequeue()).payload["order"] for _ in range(3)]
    assert orders == [0, 1, 2]


@pytest.mark.asyncio
async def test_depth_tracking(request_queue):
    assert await request_queue.depth() == 0
    await request_queue.enqueue({"x": 1}, tier="premium")
    await request_queue.enqueue({"x": 2}, tier="standard")
    await request_queue.enqueue({"x": 3}, tier="batch")
    assert await request_queue.depth() == 3


@pytest.mark.asyncio
async def test_queue_full_raises(request_queue):
    # max_depth = 50 in test_config
    for i in range(50):
        await request_queue.enqueue({"i": i}, tier="batch")
    with pytest.raises(RuntimeError, match="Queue full"):
        await request_queue.enqueue({"overflow": True}, tier="batch")


@pytest.mark.asyncio
async def test_dequeue_empty_returns_none(request_queue):
    result = await request_queue.dequeue()
    assert result is None


@pytest.mark.asyncio
async def test_clear_empties_queue(request_queue):
    for i in range(5):
        await request_queue.enqueue({"i": i}, tier="standard")
    await request_queue.clear()
    assert await request_queue.depth() == 0
```

---

## STEP 19 — tests/test_router.py

```python
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
```

---

## STEP 20 — tests/test_health.py

```python
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
```

---

## STEP 21 — tests/test_streaming.py

```python
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
```

---

## STEP 22 — tests/test_integration.py

```python
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
    from gateway.main import app
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
```

---

## STEP 23 — load_tests/locustfile.py

```python
"""
Hermes load test.
Usage:
  locust -f load_tests/locustfile.py --host http://localhost:8000

Headless (CI):
  locust -f load_tests/locustfile.py --host http://localhost:8000 \
         --users 50 --spawn-rate 5 --run-time 60s --headless
"""
import random
import json
from locust import HttpUser, task, between, events


PROMPTS = [
    "Explain the circuit breaker pattern in one sentence.",
    "What is exponential backoff?",
    "Define EWMA.",
    "What is the CAP theorem?",
    "Explain token bucket rate limiting.",
    "What is a priority queue?",
    "Define p99 latency.",
    "What is a service mesh?",
    "Explain SSE vs WebSocket.",
    "What does idempotent mean?",
]

TIERS = ["premium", "standard", "standard", "standard", "batch"]
STRATEGIES = [None, None, "round_robin", "latency_aware", "least_connections"]


class HermesUser(HttpUser):
    wait_time = between(0.2, 1.5)

    @task(8)
    def chat(self):
        payload = {
            "messages": [{"role": "user", "content": random.choice(PROMPTS)}],
            "tier": random.choice(TIERS),
            "temperature": 0.7,
        }
        strategy = random.choice(STRATEGIES)
        if strategy:
            payload["routing_strategy"] = strategy

        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            catch_response=True,
            timeout=120,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            elif resp.status_code == 503:
                resp.failure("No backends")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def status(self):
        self.client.get("/status")

    @task(1)
    def metrics(self):
        self.client.get("/metrics")
```

---

## STEP 24 — load_tests/chaos.py

```python
"""
Chaos test runner.
Starts a Locust load, then kills and restores Ollama backends mid-test
to verify circuit breaker behavior.

Usage:
  python load_tests/chaos.py

Requires: hermes running, ollama instances running on ports 11434-11436.
"""
import asyncio
import httpx
import time


GATEWAY = "http://localhost:8000"
BACKENDS = ["llama3_3b", "phi3_mini", "qwen_7b"]


async def get_status():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY}/status")
        return resp.json()


async def force_circuit(backend_id: str, action: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY}/admin/circuit-breaker/{backend_id}/{action}"
        )
        return resp.json()


async def run_requests(n: int = 20):
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = []
        for i in range(n):
            payload = {
                "messages": [{"role": "user", "content": f"test request {i}"}],
                "tier": "standard",
            }
            tasks.append(
                client.post(f"{GATEWAY}/v1/chat/completions", json=payload)
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        err = len(results) - ok
        return ok, err


async def main():
    print("=" * 60)
    print("HERMES CHAOS TEST")
    print("=" * 60)

    print("\n[1] Baseline — all backends healthy")
    status = await get_status()
    for b in status["backends"]:
        print(f"  {b['id']:20s} {b['circuit_state']:12s} healthy={b['healthy']}")

    print("\n[2] Running 20 baseline requests…")
    ok, err = await run_requests(20)
    print(f"  OK={ok}  ERR={err}")

    print("\n[3] CHAOS: Force open circuit on llama3_3b")
    result = await force_circuit("llama3_3b", "open")
    print(f"  Result: {result}")
    await asyncio.sleep(1)

    print("\n[4] Running 20 requests with 1 backend degraded…")
    ok, err = await run_requests(20)
    print(f"  OK={ok}  ERR={err} (traffic should reroute)")

    status = await get_status()
    for b in status["backends"]:
        print(f"  {b['id']:20s} {b['circuit_state']:12s}")

    print("\n[5] Restore: Force close circuit on llama3_3b")
    result = await force_circuit("llama3_3b", "close")
    print(f"  Result: {result}")
    await asyncio.sleep(1)

    print("\n[6] CHAOS: Force open ALL backends simultaneously")
    for backend_id in BACKENDS:
        await force_circuit(backend_id, "open")
    print("  All circuits open")

    print("\n[7] Running 10 requests with ALL backends degraded…")
    ok, err = await run_requests(10)
    print(f"  OK={ok}  ERR={err} (expect all 503)")

    print("\n[8] Restore all backends")
    for backend_id in BACKENDS:
        await force_circuit(backend_id, "close")
    await asyncio.sleep(1)

    print("\n[9] Final check — all restored")
    ok, err = await run_requests(10)
    print(f"  OK={ok}  ERR={err}")

    print("\n" + "=" * 60)
    print("CHAOS TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## STEP 25 — docker-compose.yml

```yaml
version: "3.9"

services:
  hermes:
    build: .
    container_name: hermes_gateway
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config:ro
      - ./ui:/app/ui:ro
    environment:
      PYTHONUNBUFFERED: "1"
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - hermes_net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hermes_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - hermes_net
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    container_name: hermes_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=7d"
    networks:
      - hermes_net
    depends_on:
      - hermes

  grafana:
    image: grafana/grafana:latest
    container_name: hermes_grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: hermes
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - hermes_net

networks:
  hermes_net:
    driver: bridge

volumes:
  redis_data:
  grafana_data:
```

---

## STEP 26 — Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "gateway.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
```

---

## STEP 27 — prometheus.yml

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_configs:
  - job_name: "hermes"
    static_configs:
      - targets: ["hermes:8000"]
    metrics_path: "/metrics"
    scrape_interval: 10s

  - job_name: "hermes_local"
    static_configs:
      - targets: ["host.docker.internal:8000"]
    metrics_path: "/metrics"
    scrape_interval: 10s
```

---

## STEP 28 — scripts/start_ollama.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Starting Ollama instances for Hermes..."

# Instance 1: llama3.2:3b on default port 11434
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
PID1=$!
echo "  [1] llama3.2:3b  → port 11434 (PID $PID1)"
sleep 3

# Instance 2: phi3:mini on port 11435
OLLAMA_HOST=0.0.0.0:11435 ollama serve &
PID2=$!
echo "  [2] phi3:mini    → port 11435 (PID $PID2)"
sleep 3

# Instance 3: qwen2.5:7b on port 11436
OLLAMA_HOST=0.0.0.0:11436 ollama serve &
PID3=$!
echo "  [3] qwen2.5:7b   → port 11436 (PID $PID3)"
sleep 3

echo ""
echo "Pulling models (first time only)..."
OLLAMA_HOST=0.0.0.0:11434 ollama pull llama3.2:3b
OLLAMA_HOST=0.0.0.0:11435 ollama pull phi3:mini
OLLAMA_HOST=0.0.0.0:11436 ollama pull qwen2.5:7b-q4

echo ""
echo "All instances ready."
echo "PIDs: $PID1 $PID2 $PID3"
echo "Stop with: kill $PID1 $PID2 $PID3"
echo ""
echo "Start gateway: uvicorn gateway.main:app --reload --port 8000"

wait
```

---

## STEP 29 — scripts/verify_setup.sh

```bash
#!/usr/bin/env bash
echo "=== Hermes Setup Verification ==="

# Redis
echo -n "[Redis] "
if redis-cli -p 6379 ping 2>/dev/null | grep -q PONG; then
  echo "✓ Running on :6379"
else
  echo "✗ Not running — start with: docker run -d -p 6379:6379 redis:7-alpine"
fi

# Ollama instances
for port in 11434 11435 11436; do
  echo -n "[Ollama :$port] "
  if curl -sf http://localhost:$port/api/ps > /dev/null 2>&1; then
    echo "✓ Running"
  else
    echo "✗ Not running"
  fi
done

# Hermes gateway
echo -n "[Hermes :8000] "
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "✓ Running"
else
  echo "✗ Not running — start with: uvicorn gateway.main:app --reload"
fi

echo ""
echo "Endpoints when running:"
echo "  Dashboard : http://localhost:8000/ui"
echo "  API docs  : http://localhost:8000/docs"
echo "  Metrics   : http://localhost:8000/metrics"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana   : http://localhost:3000 (admin/hermes)"
```

---

## STEP 30 — README.md

```markdown
# Hermes — Distributed LLM Inference Gateway

Production-grade async API gateway for multiple Ollama backends.
Built for MacBook Air M4. $0 budget. Fully local.

## What it does
- Routes requests across 3 Ollama models via 4 strategies
- Circuit breaker per backend (CLOSED/OPEN/HALF-OPEN)
- Redis token-bucket rate limiting (atomic Lua script)
- Priority queue: premium > standard > batch
- SSE streaming proxy with TTFT tracking
- Prometheus metrics + Grafana dashboards
- Live dashboard UI at /ui

## Quick start

### 1. Install dependencies
pip install -r requirements.txt

### 2. Start infrastructure
docker run -d -p 6379:6379 redis:7-alpine

### 3. Start Ollama instances
chmod +x scripts/start_ollama.sh
./scripts/start_ollama.sh

### 4. Start Hermes
uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000

### 5. Open dashboard
http://localhost:8000/ui

## Run tests (no Ollama or Redis needed)
pytest tests/ -v

## Load test
locust -f load_tests/locustfile.py --host http://localhost:8000

## Chaos test
python load_tests/chaos.py

## Full Docker stack
docker compose up --build

## Endpoints
| Endpoint | Method | Description |
|---|---|---|
| /v1/chat/completions | POST | Chat completions |
| /v1/completions | POST | Text completions |
| /health | GET | Health check |
| /status | GET | Full gateway status |
| /metrics | GET | Prometheus metrics |
| /ui | GET | Live dashboard |
| /admin/routing/strategy | POST | Change routing strategy |
| /admin/circuit-breaker/{id}/open | POST | Force trip circuit |
| /admin/circuit-breaker/{id}/close | POST | Force close circuit |
| /admin/queue/depth | GET | Queue depth by tier |
| /admin/rate-limit/reset | POST | Reset rate limit bucket |

## Architecture
Gateway → Router → Backend (Ollama)
            ↑
    Circuit Breaker (per backend)
    Rate Limiter (per tier, Redis)
    Priority Queue (Redis Sorted Set)
    Health Checker (async loop, EWMA)
    Prometheus metrics (all components)
```

---

## STEP 31 — FINAL VERIFICATION CHECKLIST

After all files are created, run these commands in order. Every command must
succeed before moving to the next.

### Install
```bash
pip install -r requirements.txt
pip install fakeredis  # if not in requirements.txt already
```

### Run tests (all 38+ must pass, zero failures)
```bash
pytest tests/ -v --tb=short
```
Expected: 38 passed, 0 failed, 0 errors

### Start infrastructure
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Start gateway (dev mode)
```bash
uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify all endpoints respond
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/status | python3 -m json.tool
curl -s http://localhost:8000/metrics | head -20
curl -s http://localhost:8000/ | python3 -m json.tool
```

### Open UI
```
http://localhost:8000/ui
```
Should show the live dashboard with backend status cards.

### Start Ollama (if you want live inference)
```bash
./scripts/start_ollama.sh
```

### Send a real chat request
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is a circuit breaker?"}],
    "tier": "standard"
  }'
```

### Test circuit breaker admin
```bash
# Trip a circuit open
curl -X POST http://localhost:8000/admin/circuit-breaker/llama3_3b/open
curl -s http://localhost:8000/status | python3 -c "
import json,sys
d=json.load(sys.stdin)
for b in d['backends']:
    print(b['id'], b['circuit_state'])
"
# Should show llama3_3b as OPEN

# Close it again
curl -X POST http://localhost:8000/admin/circuit-breaker/llama3_3b/close
```

### Run load test (optional, needs Ollama running)
```bash
locust -f load_tests/locustfile.py --host http://localhost:8000 \
       --users 20 --spawn-rate 2 --run-time 30s --headless
```

### Run chaos test (optional, needs Ollama running)
```bash
python load_tests/chaos.py
```

### Full Docker Compose stack
```bash
docker compose up --build
# UI:         http://localhost:8000/ui
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000  (login: admin / hermes)
```

---

## DEFINITION OF DONE

The project is complete when ALL of the following are true:

- [ ] All 30 files exist with complete, non-stubbed code
- [ ] `pytest tests/ -v` shows 38+ passed, 0 failed
- [ ] `uvicorn gateway.main:app` starts without import errors
- [ ] `/health` returns JSON with `status` field
- [ ] `/status` returns JSON with `backends`, `queue_depth`, `routing_strategy`
- [ ] `/metrics` returns Prometheus text with `hermes_` prefix
- [ ] `/ui` serves the HTML dashboard (no 404)
- [ ] Dashboard auto-refreshes and shows backend status cards
- [ ] Chat test panel in dashboard sends a request and shows response
- [ ] Circuit breaker trip/close buttons in dashboard work
- [ ] `docker compose up` brings full stack up cleanly
- [ ] Grafana accessible at :3000, Prometheus at :9090

PROMPT_END
echo "Written: $(wc -l < /mnt/user-data/outputs/hermes_FINAL_build_prompt.md) lines"
Output