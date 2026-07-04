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
