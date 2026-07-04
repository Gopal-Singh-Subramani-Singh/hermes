# ADR-002: Per-Backend Circuit Breaker with Sliding Window

**Status:** Accepted  
**Date:** 2026-06  
**Deciders:** Architecture team

---

## Context

LLM inference backends are slow and stateful. A backend that is overloaded, OOM-killed, or stuck on a long generation can stop responding without closing the TCP connection — hanging the gateway and all requests assigned to it. Without isolation, one bad backend degrades the entire gateway.

The classic solution is the circuit breaker pattern: detect a failing backend, stop sending it traffic, and probe periodically for recovery.

Key design questions:
1. **When should the circuit open?** A single error is noise. A sustained error rate is signal.
2. **How long to stay open?** Long enough to let the backend recover; short enough to resume quickly.
3. **How to confirm recovery?** Don't immediately flood a recovering backend — use a probe.

---

## Decision

Implement a 3-state circuit breaker per backend using a **sliding time window** error rate:

```
CLOSED ──[error_rate >= 0.5 AND calls >= 5]──► OPEN
  ▲                                               │
  │                                     [timeout: 30s]
  │                                               ▼
  └──[2 consecutive successes]──────── HALF_OPEN
              ◄──[any failure]──────────────────────
```

**Error rate** is computed over a 10-second sliding window using a `deque` of `(timestamp, ok)` tuples. The window prunes on every access — no timer needed.

**Minimum call threshold:** The circuit will not open until at least 5 calls exist in the window. This prevents false trips from a single failure on a cold backend.

**HALF_OPEN probe:** After the open timeout, one request is allowed through. If it succeeds, the success counter increments. After 2 consecutive successes, the circuit closes and the window is cleared. If it fails, the circuit reopens immediately.

**asyncio.Lock:** All state transitions are guarded by an `asyncio.Lock` to prevent race conditions between concurrent in-flight requests.

---

## Alternatives Considered

**Fixed error count (e.g., open after 5 consecutive failures)**  
Simpler to implement. Rejected because it doesn't account for traffic rate — 5 failures in 1 second on a high-traffic backend is very different from 5 failures in 5 minutes on a low-traffic one.

**External circuit breaker (e.g., Resilience4j, Hystrix)**  
Battle-tested. Rejected because these are JVM libraries. A Python equivalent would add a significant dependency and still require integration code.

**Health-check-only availability**  
Rely solely on the periodic health checker to mark backends unhealthy. Rejected because health checks run every 10 seconds — a backend that starts returning errors during active traffic would affect up to 10 seconds of requests before the health check catches it. The circuit breaker reacts within the same request cycle.

---

## Consequences

**Pros:**
- Isolates backend failures at the request level — no waiting for the health check cycle.
- HALF_OPEN probe prevents thundering herd on recovery.
- Minimum call threshold eliminates false positives during low traffic.
- State is fully observable via `hermes_circuit_breaker_state` Prometheus gauge (0/1/2).
- Admin API (`/admin/circuit-breaker/{id}/open|close`) enables manual control for testing and incident response.

**Cons:**
- State is in-process memory. In a multi-worker deployment, each worker has an independent circuit breaker. A backend failing for one worker may not be marked open by another. Mitigation: move state to Redis for multi-worker deployments.
- The asyncio.Lock adds slight overhead per request for the state check. Acceptable — the lock is held briefly (microseconds) and uncontested most of the time.

---

## Outcome

Implemented in `gateway/circuit_breaker.py`. Covered by 9 tests in `tests/test_circuit_breaker.py` including full state machine traversal, timeout transitions, and forced open/close via admin API.
