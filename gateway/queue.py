from __future__ import annotations
import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
import redis.asyncio as aioredis
import structlog

from gateway.metrics import (
    QUEUE_DEPTH,
    QUEUE_ENQUEUED,
    QUEUE_DEQUEUED,
    QUEUE_WAIT_TIME,
)
from config.settings import get_config

logger = structlog.get_logger(__name__)

_QUEUE_KEY = "hermes:queue:zset"
_DATA_PREFIX = "hermes:queue:data:"
_PAYLOAD_TTL = 300  # 5 minutes


@dataclass
class QueuedRequest:
    request_id: str
    tier: str
    payload: Dict
    enqueued_at: float
    score: float


class RequestQueue:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _score(self, tier: str) -> float:
        cfg = get_config().queue
        tier_priority = getattr(cfg.tiers, tier, cfg.tiers.standard)
        # Higher tier_priority → higher score → dequeued first (zpopmax)
        # Subtract fractional timestamp so older requests win within same tier (FIFO)
        return tier_priority * 1e12 - time.time()

    async def enqueue(
        self, payload: Dict, tier: str = "standard"
    ) -> str:
        cfg = get_config().queue
        depth = await self._redis.zcard(_QUEUE_KEY)
        if depth >= cfg.max_depth:
            raise RuntimeError(
                f"Queue full: {depth}/{cfg.max_depth}"
            )

        request_id = str(uuid.uuid4())
        score = self._score(tier)
        now = time.time()

        data = json.dumps(
            {"tier": tier, "payload": payload, "enqueued_at": now}
        )

        pipe = self._redis.pipeline()
        pipe.zadd(_QUEUE_KEY, {request_id: score})
        pipe.setex(f"{_DATA_PREFIX}{request_id}", _PAYLOAD_TTL, data)
        await pipe.execute()

        QUEUE_ENQUEUED.labels(tier=tier).inc()
        await self._update_depth_gauge(tier)

        logger.debug(
            "queue.enqueued",
            request_id=request_id,
            tier=tier,
            queue_depth=depth + 1,
        )
        return request_id

    async def dequeue(self) -> Optional[QueuedRequest]:
        result = await self._redis.zpopmax(_QUEUE_KEY, count=1)
        if not result:
            return None

        raw_id, score = result[0]
        request_id = (
            raw_id if isinstance(raw_id, str) else raw_id.decode()
        )

        raw_data = await self._redis.getdel(
            f"{_DATA_PREFIX}{request_id}"
        )
        if raw_data is None:
            logger.warning(
                "queue.data_missing", request_id=request_id
            )
            return None

        data = json.loads(raw_data)
        tier = data["tier"]
        wait = time.time() - data["enqueued_at"]

        QUEUE_DEQUEUED.labels(tier=tier).inc()
        QUEUE_WAIT_TIME.labels(tier=tier).observe(wait)
        await self._update_depth_gauge(tier)

        return QueuedRequest(
            request_id=request_id,
            tier=tier,
            payload=data["payload"],
            enqueued_at=data["enqueued_at"],
            score=score,
        )

    async def depth(self) -> int:
        return await self._redis.zcard(_QUEUE_KEY)

    async def depth_by_tier(self) -> Dict[str, int]:
        return {
            "premium": await self._tier_count("premium"),
            "standard": await self._tier_count("standard"),
            "batch": await self._tier_count("batch"),
        }

    async def clear(self) -> None:
        await self._redis.delete(_QUEUE_KEY)

    async def _tier_count(self, tier: str) -> int:
        cfg = get_config().queue
        base = getattr(cfg.tiers, tier, cfg.tiers.standard) * 1e12
        return await self._redis.zcount(
            _QUEUE_KEY, base - 1e12, base
        )

    async def _update_depth_gauge(self, tier: str) -> None:
        count = await self._tier_count(tier)
        QUEUE_DEPTH.labels(tier=tier).set(count)
