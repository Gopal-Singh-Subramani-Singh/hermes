# ADR-003: Redis for Queueing and Rate Limiting over Kafka

**Status:** Accepted  
**Date:** 2026-06  
**Deciders:** Architecture team

---

## Context

Hermes needs two stateful, shared data structures:

1. **Rate limiter:** A token bucket per tier that must survive concurrent reads and writes from all in-flight requests without race conditions.
2. **Priority queue:** A backpressure buffer that orders requests by tier (premium > standard > batch) and FIFO within each tier.

Both require a fast, shared, atomic store. The two main candidates evaluated were Redis and Kafka.

---

## Decision

Use **Redis** for both the rate limiter and the priority queue.

- **Rate limiter:** Redis hash (`HMGET`/`HMSET`) with an atomic Lua script loaded via `SCRIPT LOAD` / `EVALSHA`. The Lua script runs atomically inside the Redis process — no check-then-act race conditions possible.
- **Priority queue:** Redis Sorted Set (`ZADD`, `ZPOPMAX`, `ZCOUNT`) with a score formula that encodes tier priority and insertion timestamp. Payload stored as a separate key with TTL for automatic cleanup.

---

## Alternatives Considered

**Kafka**  
Kafka is purpose-built for durable, high-throughput message queuing with consumer groups, offsets, and replay. For this use case:
- Requires a Kafka broker (ZooKeeper or KRaft) — minimum 3 processes just for infrastructure
- No native priority ordering — would require separate topics per tier and a priority consumer
- Overkill for local single-node deployment
- Rate limiting would still need a separate store (Redis or in-memory)

Rejected. The operational overhead does not justify the throughput gains for a local inference gateway.

**In-memory (Python dict/asyncio.Queue)**  
Zero external dependencies. Rejected because:
- Not shared across workers (future multi-process deployment)
- Lost on restart — outstanding requests in the queue disappear
- In-memory token bucket has race conditions across concurrent asyncio tasks without explicit locking

**PostgreSQL / SQLite**  
Persistent and queryable. Rejected because:
- Disk I/O latency is too high for per-request rate limit checks (sub-millisecond required)
- No atomic scripting equivalent to Redis Lua
- Schema management overhead for what is essentially a counters store

---

## Consequences

**Pros:**
- Single dependency covers both use cases (rate limit + queue)
- Redis Sorted Sets natively support priority ordering and ZPOPMAX atomic dequeue
- Lua scripts guarantee atomic check-and-consume — no external distributed lock needed
- `fakeredis` enables full test coverage with no real Redis required
- Redis 7 (alpine, ~30MB) starts in under a second in Docker
- TTL on queue payload keys (`SETEX`) provides automatic cleanup for abandoned items

**Cons:**
- Redis is a network process — adds ~1ms round-trip vs in-memory
- No message durability by default (AOF disabled in default alpine image) — queue items lost on Redis restart
- Token bucket is non-atomic in test mode (no `lupa` Lua runtime) — acceptable because tests are single-process
- Redis Sorted Set scores are floating point — precision edge cases possible at extreme time values (not a concern within the operational lifetime of a running gateway)

---

## Outcome

Redis selected. Rate limiter implemented in `gateway/rate_limiter.py` using atomic Lua script with pure-Redis fallback. Priority queue implemented in `gateway/queue.py` using Redis Sorted Sets. Covered by 7 rate limiter tests and 8 queue tests.
