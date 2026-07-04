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
