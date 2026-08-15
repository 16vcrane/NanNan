from fastapi import APIRouter
from app.core.database import database_status
from app.core.redis import redis_status

router = APIRouter(tags=["health"])

@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "nannan-api", "checks": {"database": await database_status(), "redis": await redis_status()}}
