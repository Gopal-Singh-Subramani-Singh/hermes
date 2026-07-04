from __future__ import annotations
import time
from typing import Optional, Tuple
import redis.asyncio as aioredis
import structlog

from gateway.metrics import RATE_LIMIT_REJECTIONS, TOKEN_BUCKET_REMAINING
from config.settings import get_config

logger = structlog.get_logger(__name__)

# Atomic token bucket: check-and-consume in a single Redis round-trip.
# Returns [allowed (0/1), remaining_tokens (int)]
_LUA_CONSUME = """
local key          = KEYS[1]
local capacity     = tonumber(ARGV[1])
local refill_rate  = tonumber(ARGV[2])
local now          = tonumber(ARGV[3])
local requested    = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens      = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, math.floor(tokens)}
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {0, math.floor(tokens)}
end
"""


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._sha: Optional[str] = None

    async def _load_script(self) -> Optional[str]:
        """Load Lua script into Redis. Returns SHA, '__fallback__' if Lua unsupported."""
        if self._sha is None:
            try:
                self._sha = await self._redis.script_load(_LUA_CONSUME)
            except (aioredis.ResponseError, Exception):
                # fakeredis without lupa, or Redis without Lua — use pure-Redis fallback
                self._sha = "__fallback__"
        return self._sha

    async def _consume_fallback(self, key: str, capacity: int,
                                refill_rate: float, now: float,
                                requested: int = 1) -> Tuple[bool, int]:
        """Pure-Redis token bucket (non-atomic, safe for single-node tests)."""
        raw = await self._redis.hmget(key, "tokens", "last_refill")
        tokens = float(raw[0]) if raw[0] is not None else float(capacity)
        last_refill = float(raw[1]) if raw[1] is not None else now

        elapsed = max(0.0, now - last_refill)
        tokens = min(float(capacity), tokens + elapsed * refill_rate)

        if tokens >= requested:
            tokens -= requested
            allowed = True
        else:
            allowed = False

        await self._redis.hset(key, mapping={"tokens": tokens, "last_refill": now})
        await self._redis.expire(key, 3600)
        return allowed, int(tokens)

    async def _evalsha(self, key: str, capacity: int,
                       refill_rate: float, now: float,
                       requested: int = 1) -> Tuple[bool, int]:
        sha = await self._load_script()

        if sha == "__fallback__":
            return await self._consume_fallback(key, capacity, refill_rate, now, requested)

        try:
            result = await self._redis.evalsha(
                sha, 1, key, capacity, refill_rate, now, requested
            )
        except aioredis.ResponseError as exc:
            if "NOSCRIPT" in str(exc):
                self._sha = None
                sha = await self._load_script()
                if sha == "__fallback__":
                    return await self._consume_fallback(key, capacity, refill_rate, now, requested)
                result = await self._redis.evalsha(
                    sha, 1, key, capacity, refill_rate, now, requested
                )
            else:
                raise
        return bool(int(result[0])), int(result[1])

    async def is_allowed(
        self,
        tier: str = "standard",
        key_suffix: str = "global",
    ) -> bool:
        cfg = get_config().rate_limiting
        if not cfg.enabled:
            return True

        rpm = getattr(cfg.tiers, tier, cfg.default_rpm)
        capacity = int(rpm * cfg.burst_multiplier)
        refill_rate = rpm / 60.0
        redis_key = f"hermes:rl:{tier}:{key_suffix}"

        allowed, remaining = await self._evalsha(
            redis_key, capacity, refill_rate, time.time()
        )

        TOKEN_BUCKET_REMAINING.labels(tier=tier).set(remaining)
        if not allowed:
            RATE_LIMIT_REJECTIONS.labels(tier=tier).inc()
            logger.debug(
                "rate_limit.rejected",
                tier=tier,
                remaining=remaining,
                key=redis_key,
            )
        return allowed

    async def get_remaining(
        self, tier: str = "standard", key_suffix: str = "global"
    ) -> int:
        redis_key = f"hermes:rl:{tier}:{key_suffix}"
        raw = await self._redis.hget(redis_key, "tokens")
        if raw is None:
            cfg = get_config().rate_limiting
            rpm = getattr(cfg.tiers, tier, cfg.default_rpm)
            return int(rpm * cfg.burst_multiplier)
        return int(float(raw))

    async def reset(
        self, tier: str = "standard", key_suffix: str = "global"
    ) -> None:
        redis_key = f"hermes:rl:{tier}:{key_suffix}"
        await self._redis.delete(redis_key)
        logger.info("rate_limit.reset", tier=tier, key=redis_key)
