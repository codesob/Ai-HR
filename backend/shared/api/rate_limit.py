import logging
import time

from fastapi import Request

from shared.core.config import get_settings

logger = logging.getLogger(__name__)

_memory_buckets: dict[str, tuple[int, int]] = {}
_redis = None
_redis_failed_at = 0.0


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def _get_redis():
    global _redis
    if _redis is None:
        from redis.asyncio import from_url

        _redis = from_url(get_settings().redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
    return _redis


async def _hit_redis(key: str, window: int) -> int:
    redis = _get_redis()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = await pipe.execute()
    return int(count)


def _hit_memory(key: str, window: int) -> int:
    now = int(time.time())
    count, reset_at = _memory_buckets.get(key, (0, now + window))
    if now >= reset_at:
        count, reset_at = 0, now + window
    count += 1
    _memory_buckets[key] = (count, reset_at)
    return count


async def is_rate_limited(request: Request, *, bucket: str, limit: int) -> bool:
    """Fixed-window limiter shared across replicas via Redis; per-process fallback if Redis is down."""
    global _redis_failed_at
    if limit <= 0:
        return False
    window = get_settings().rate_limit_window_seconds
    key = f"rl:{bucket}:{client_ip(request)}:{int(time.time()) // window}"
    if time.monotonic() - _redis_failed_at > 30:
        try:
            return await _hit_redis(key, window) > limit
        except Exception:
            _redis_failed_at = time.monotonic()
            logger.warning("Redis unavailable for rate limiting; using in-memory fallback")
    return _hit_memory(key, window) > limit
