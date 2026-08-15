import hashlib
import json
import logging
import secrets
from dataclasses import dataclass
from enum import Enum

from app.core.config import get_settings
from app.core.redis import redis

logger = logging.getLogger(__name__)


class IdempotencyState(str, Enum):
    ACQUIRED = "acquired"
    PENDING = "pending"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class IdempotencyClaim:
    state: IdempotencyState
    scope: str
    token: str | None = None
    result: dict | None = None


def build_scope(user_id: object, key: str) -> str:
    digest = hashlib.sha256(f"{user_id}:{key}".encode()).hexdigest()
    return f"create-diary:{digest}"


async def begin(scope: str) -> IdempotencyClaim:
    settings = get_settings()
    result_key = f"idempotency:result:{scope}"
    lock_key = f"idempotency:lock:{scope}"
    try:
        cached = await redis.get(result_key)
        if cached:
            return IdempotencyClaim(
                IdempotencyState.COMPLETED, scope, result=json.loads(cached)
            )
        token = secrets.token_urlsafe(18)
        acquired = await redis.set(
            lock_key,
            token,
            ex=max(1, settings.idempotency_lock_seconds),
            nx=True,
        )
        if acquired:
            return IdempotencyClaim(IdempotencyState.ACQUIRED, scope, token=token)
        return IdempotencyClaim(IdempotencyState.PENDING, scope)
    except Exception as exc:
        logger.warning("idempotency_unavailable error_type=%s", type(exc).__name__)
        return IdempotencyClaim(IdempotencyState.UNAVAILABLE, scope)


async def complete(claim: IdempotencyClaim, result: dict) -> None:
    if claim.state is not IdempotencyState.ACQUIRED or not claim.token:
        return
    settings = get_settings()
    try:
        await redis.set(
            f"idempotency:result:{claim.scope}",
            json.dumps(result),
            ex=max(1, settings.idempotency_result_seconds),
        )
        await _release_lock(claim)
    except Exception as exc:
        logger.warning("idempotency_complete_failed error_type=%s", type(exc).__name__)


async def abort(claim: IdempotencyClaim) -> None:
    if claim.state is not IdempotencyState.ACQUIRED or not claim.token:
        return
    try:
        await _release_lock(claim)
    except Exception as exc:
        logger.warning("idempotency_abort_failed error_type=%s", type(exc).__name__)


async def _release_lock(claim: IdempotencyClaim) -> None:
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
      return redis.call('del', KEYS[1])
    end
    return 0
    """
    await redis.eval(script, 1, f"idempotency:lock:{claim.scope}", claim.token)
