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
