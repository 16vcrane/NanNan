import logging
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.redis import redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


async def check_rate_limit(identifier: str) -> RateLimitResult:
    settings = get_settings()
    limit = max(1, settings.rate_limit_requests)
    window = max(1, settings.rate_limit_window_seconds)
    now = int(time.time())
    bucket = now // window
    key = f"rate-limit:{identifier}:{bucket}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window + 1)
    except Exception as exc:
        logger.warning("rate_limit_unavailable error_type=%s", type(exc).__name__)
        return RateLimitResult(True, limit, limit, window)
    retry_after = window - (now % window)
    return RateLimitResult(
        allowed=count <= limit,
        limit=limit,
        remaining=max(0, limit - count),
        retry_after=retry_after,
    )
