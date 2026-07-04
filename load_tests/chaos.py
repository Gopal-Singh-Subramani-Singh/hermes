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
