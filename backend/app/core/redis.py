from redis.asyncio import Redis
from app.core.config import get_settings

redis = Redis.from_url(get_settings().redis_url, decode_responses=True)

async def redis_status() -> str:
    try:
        await redis.ping()
        return "ok"
    except Exception:
        return "unavailable"
