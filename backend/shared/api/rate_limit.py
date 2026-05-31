from time import monotonic

from fastapi import HTTPException, Request, status

from shared.core.config import get_settings

_buckets: dict[str, list[float]] = {}


async def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    if settings.rate_limit_requests <= 0:
        return
    forwarded = request.headers.get("x-forwarded-for", "")
    client = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = monotonic()
    window_start = now - settings.rate_limit_window_seconds
    bucket = [ts for ts in _buckets.get(client, []) if ts >= window_start]
    if len(bucket) >= settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    bucket.append(now)
    _buckets[client] = bucket
