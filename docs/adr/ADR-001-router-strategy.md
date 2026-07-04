# ADR-001: Pluggable Routing Strategy with Per-Request Override

**Status:** Accepted  
**Date:** 2026-06  
**Deciders:** Architecture team

---

## Context

Hermes routes inference requests across multiple Ollama backends. No single routing strategy is optimal for all workloads:

- Interactive chat cares most about **response latency** — pick the fastest backend.
- Batch jobs care most about **throughput** — spread load evenly without racing for the fastest node.
- Premium users expect consistently **low latency** regardless of cluster conditions.
- Some clients want **predictable affinity** (round-robin) for reproducibility or debugging.

A hardcoded strategy would force a single trade-off onto all users.

---

## Decision

Implement four routing strategies in a single `Router` class, selected at runtime:

| Strategy | Algorithm | Best for |
|---|---|---|
| `latency_aware` | min(EWMA latency) | Interactive chat (default) |
| `round_robin` | weighted modulo counter | Balanced, reproducible testing |
| `least_connections` | min(active_connections) | High-concurrency batch |
| `priority` | tier-aware dispatch | Mixed workloads with SLA tiers |

The active strategy is set globally in `config.yaml` (`routing.default_strategy`) and can be changed live via `POST /admin/routing/strategy`. Any individual request can override the strategy via the `routing_strategy` field in the request body — without affecting the global default.

---

## Alternatives Considered

**Single fixed strategy (latency_aware only)**  
Simpler. Rejected because batch workloads routed to the lowest-latency backend can saturate it while others sit idle.

**External load balancer (nginx, HAProxy)**  
Offloads routing to a proven tool. Rejected because an external balancer has no awareness of circuit breaker state, tier, or per-backend model assignment — it would route to backends that Hermes already knows are unhealthy.

**Consistent hashing**  
Good for cache affinity. Rejected because Hermes does not maintain session state per backend; there is no benefit to routing the same client to the same backend.

---

## Consequences

**Pros:**
- Single place to add new strategies — implement one method, register the name.
- Per-request override enables A/B testing strategies without config changes.
- `ROUTING_DECISIONS` counter (labelled by strategy + backend) makes strategy effectiveness measurable in Prometheus.

**Cons:**
- The `Router._lock` for round-robin index serializes concurrent selection under that strategy. Under very high concurrency this becomes a bottleneck. A lock-free atomic counter would remove this, but adds complexity.
- Per-request strategy override means a malicious client could force an unfavourable strategy. Should be restricted by auth in production.

---

## Outcome

Four strategies implemented in `gateway/router.py`. Default is `latency_aware`. All four strategies share the same availability filter (healthy + circuit-closed). Covered by 9 tests in `tests/test_router.py`.
