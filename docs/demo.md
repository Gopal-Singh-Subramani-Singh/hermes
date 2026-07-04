# Hermes — Demo Guide

## What this demo proves

- The gateway routes requests and returns structured responses
- Circuit breakers respond correctly to forced failure injection
- Rate limiting enforces tier-based token buckets
- Priority queue tracks queue depth by tier
- Prometheus metrics are populated and queryable
- Dashboard UI is live at `/ui`

---

## Prerequisites

```bash
pip install -r requirements.txt
docker run -d -p 6379:6379 redis:7-alpine
```

---

## Demo Commands

### 1. Start the gateway

```bash
uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verify health

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{
  "status": "healthy",
  "backends": {
    "backend_0": {"state": "CLOSED", "healthy": true},
    "backend_1": {"state": "CLOSED", "healthy": true},
    "backend_2": {"state": "CLOSED", "healthy": true}
  }
}
```

### 3. Check full gateway status

```bash
curl http://localhost:8000/status | python -m json.tool
```

Expected: routing strategy, backend states, queue depth, rate limiter stats.

### 4. Open dashboard

```
http://localhost:8000/ui
```

Screenshot pending.

### 5. Inject a circuit breaker failure (chaos test)

```bash
# Force trip backend_0
curl -X POST http://localhost:8000/admin/circuit-breaker/backend_0/open

# Verify it is OPEN
curl http://localhost:8000/health

# Requests to backend_0 are now fast-rejected
# After configured timeout, state automatically moves to HALF_OPEN
# On successful probe, returns to CLOSED

# Force close (reset)
curl -X POST http://localhost:8000/admin/circuit-breaker/backend_0/close
```

### 6. Check queue depth by tier

```bash
curl http://localhost:8000/admin/queue/depth
```

### 7. View Prometheus metrics

```bash
curl http://localhost:8000/metrics | grep hermes_
```

### 8. Run load test

```bash
locust -f load_tests/locustfile.py --host http://localhost:8000
# Open http://localhost:8089 for Locust UI
```

### 9. Run chaos test script

```bash
python load_tests/chaos.py
```

### 10. Run full Docker stack (Prometheus + Grafana)

```bash
docker compose up --build
open http://localhost:3000   # Grafana (admin / admin)
```

---

## Expected Output Summary

| Check | Expected |
|-------|----------|
| `/health` | All backends CLOSED (healthy=true) |
| `/status` | Routing strategy, queue depth, rate limiter |
| `/metrics` | hermes_* counters and gauges populated |
| `/ui` | Live dashboard with backend status |
| Circuit breaker trip | Backend moves to OPEN, requests fast-rejected |
| Load test | Requests distributed across backends per routing strategy |

---

## Known Limitations

- Full inference (actual LLM text generation) requires Ollama running with a model loaded. Without Ollama, the gateway returns 503s from backends but all routing, circuit breaker, rate limiting, and queue logic still exercises correctly.
- Priority queue routing is opt-in (not the default strategy).
