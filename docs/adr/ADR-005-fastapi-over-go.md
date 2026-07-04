# ADR-005: FastAPI (Python) over Go for Gateway Implementation

**Status:** Accepted  
**Date:** 2026-06  
**Deciders:** Architecture team

---

## Context

A gateway is typically a performance-sensitive component — it sits in the critical path of every request. Languages like Go are commonly chosen for API gateways (Caddy, Traefik, Kong) because of low memory overhead, fast startup, and native concurrency.

Python has historically been considered unsuitable for high-performance networking. The question is whether that trade-off applies here.

The key constraint: the bottleneck is **LLM inference**, not the gateway. A single llama3.2:3b inference on M4 takes 2–30 seconds. The gateway's per-request overhead is measured in milliseconds. A 10× difference in gateway throughput is irrelevant when each request spends 99%+ of its time waiting for Ollama.

---

## Decision

Use **Python 3.11 with FastAPI and uvicorn** running on asyncio.

---

## Rationale

**The bottleneck is not the gateway.**  
Inference on llama3.2:3b takes roughly 2–10 seconds end-to-end, and 30–120 seconds for larger models. The gateway adds perhaps 5–20ms of overhead. Optimizing the gateway from 10ms to 1ms would not be perceptible to users.

**asyncio handles the concurrency model naturally.**  
The gateway is almost entirely I/O-bound: waiting for Redis and waiting for Ollama. Python's asyncio event loop handles thousands of concurrent I/O-bound tasks efficiently. CPU-bound operations (JSON parsing, Pydantic validation) are minimal per request.

**The ecosystem is unmatched for this use case.**  
- Pydantic v2 provides request validation, serialization, and OpenAPI schema generation in one library
- FastAPI generates interactive `/docs` (Swagger UI) automatically from type annotations
- `prometheus-client`, `structlog`, `httpx`, `fakeredis` — everything needed exists as a first-class Python package
- Tests use `pytest-asyncio` and `httpx.ASGITransport` for in-process integration testing with no mocking overhead

**Operational familiarity.**  
The ML/AI toolchain is Python-first. The team operating this gateway will also work with PyTorch, transformers, and Ollama Python clients. A Python gateway is easier to extend and debug in that context.

---

## Alternatives Considered

**Go (net/http or Gin/Fiber)**  
Go would offer lower memory footprint (~20MB vs ~100MB), faster cold start, and higher raw request throughput. Rejected because:
- The throughput advantage is irrelevant given LLM inference latency
- Go's type system would require manual OpenAPI schema maintenance
- No equivalent of FastAPI's automatic schema generation from type hints
- The team's primary language is Python; a Go gateway would be a maintenance island

**Rust (Axum/Actix-web)**  
Maximum performance. Rejected because:
- Same reasoning as Go, amplified by steeper learning curve
- Async Rust has non-trivial complexity (`Pin`, `Send` bounds, lifetime management)
- Zero practical benefit given the bottleneck analysis

**Node.js (Express/Fastify)**  
Good async I/O. Rejected because:
- JavaScript/TypeScript adds a language boundary for a Python-centric team
- The LLM ecosystem is not JS-native

**Flask (synchronous Python)**  
Simpler. Rejected because:
- Synchronous request handling would block the thread during Ollama I/O
- Each concurrent request would require a thread, capping concurrency
- No native async Redis support
- No automatic OpenAPI generation

---

## Consequences

**Pros:**
- FastAPI's dependency injection and Pydantic models make the codebase self-documenting
- asyncio-native from the ground up — all I/O (Redis, Ollama, health checks) is non-blocking
- `lifespan` context manager provides clean startup/shutdown without lifecycle hacks
- Auto-generated `/docs` endpoint (Swagger UI) with zero additional code
- Python's duck typing and `unittest.mock` make the test suite highly expressive

**Cons:**
- GIL (Global Interpreter Lock) prevents true multi-core CPU parallelism. Mitigated by running multiple uvicorn workers — but in-memory state (circuit breakers, EWMA) then needs to move to Redis.
- Higher memory footprint than Go/Rust (~100–150MB baseline).
- Python startup time (~1s) is slower than Go (<100ms). Irrelevant for a long-running gateway process; matters for serverless.
- CPython async has higher per-coroutine overhead than Go goroutines. Again: irrelevant against LLM inference latency.

---

## Outcome

FastAPI on Python 3.11 selected. The choice optimizes for developer velocity, ecosystem fit, and operational simplicity. Performance is adequate — the gateway is not the bottleneck. Covered end-to-end by 6 integration tests using FastAPI's ASGI transport, with no mocking of the framework layer.
