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
