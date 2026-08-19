import asyncio
import logging
import time
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.guardrails import (
    FAILURE_FALLBACK,
    SAFETY_FALLBACK,
    OutputGuardrailError,
    check_input,
    validate_output,
)
from app.ai.provider import LLMProviderError, get_llm_provider
from app.ai.reflection import generate_memory_reflection, generate_reflection
from app.services.memory_retrieval_service import retrieve_context
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.redis import redis
from app.models.diary import DiaryEntry
from app.models.reflection import AiReflection
from app.models.user import UserProfile

logger = logging.getLogger(__name__)
_local_locks: defaultdict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


class ReflectionNotFoundError(Exception):
    pass


class ReflectionRetryNotAllowedError(Exception):
    pass


async def get_reflection(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
) -> AiReflection:
    result = await db.execute(
        select(AiReflection)
        .join(DiaryEntry, DiaryEntry.id == AiReflection.diary_entry_id)
        .where(
            AiReflection.diary_entry_id == diary_id,
            AiReflection.user_id == user_id,
            DiaryEntry.deleted_at.is_(None),
        )
    )
    reflection = result.scalar_one_or_none()
    if reflection is None:
        raise ReflectionNotFoundError
    return reflection


def can_retry(reflection: AiReflection) -> bool:
    return (
        reflection.status == "failed"
        and reflection.attempt_count < get_settings().reflection_max_attempts
    )


async def request_retry(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
) -> AiReflection:
    reflection = await get_reflection(db, user_id, diary_id)
    if not can_retry(reflection):
        raise ReflectionRetryNotAllowedError
    reflection.status = "pending"
    reflection.content = None
    reflection.error_code = None
    await db.commit()
    await db.refresh(reflection)
    return reflection


async def _acquire_distributed_lock(reflection_id: uuid.UUID) -> tuple[str, str] | None:
    key = f"reflection:{reflection_id}"
    token = uuid.uuid4().hex
    try:
        acquired = await redis.set(key, token, nx=True, ex=120)
    except Exception:
        return None
    return (key, token) if acquired else (key, "")


async def _release_distributed_lock(lock: tuple[str, str] | None) -> None:
    if not lock or not lock[1]:
        return
    key, token = lock
    try:
        await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            key,
            token,
        )
    except Exception:
        pass


async def run_reflection_task(
    reflection_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
) -> None:
    distributed_lock = await _acquire_distributed_lock(reflection_id)
    if distributed_lock is not None and not distributed_lock[1]:
        return

    local_lock = _local_locks[reflection_id]
    if local_lock.locked():
        await _release_distributed_lock(distributed_lock)
        return

    async with local_lock:
        try:
            await _run_reflection(reflection_id, session_factory)
        finally:
            await _release_distributed_lock(distributed_lock)
            _local_locks.pop(reflection_id, None)


async def _run_reflection(
    reflection_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
) -> None:
    started = time.perf_counter()
    async with session_factory() as db:
        result = await db.execute(
            select(AiReflection, DiaryEntry, UserProfile.personal_memory_enabled)
            .join(DiaryEntry, DiaryEntry.id == AiReflection.diary_entry_id)
            .join(UserProfile, UserProfile.id == AiReflection.user_id)
            .where(
                AiReflection.id == reflection_id,
                AiReflection.status == "pending",
                DiaryEntry.deleted_at.is_(None),
            )
        )
        row = result.one_or_none()
        if row is None:
            return
        reflection, diary, user_memory_enabled = row
        if reflection.attempt_count >= get_settings().reflection_max_attempts:
            reflection.status = "failed"
            reflection.content = FAILURE_FALLBACK
            reflection.error_code = "RETRY_LIMIT_REACHED"
            await db.commit()
            return

        reflection.attempt_count += 1
        diary_content = diary.content
        input_safety = check_input(diary_content)
        if not input_safety.safe:
            reflection.status = "blocked"
            reflection.safety_status = input_safety.safety_status
            reflection.content = SAFETY_FALLBACK
            reflection.error_code = "SENSITIVE_INPUT"
            reflection.latency_ms = int((time.perf_counter() - started) * 1000)
            await db.commit()
            return
        await db.commit()

    status = "failed"
    safety_status = "safe"
    content = FAILURE_FALLBACK
    error_code = "GENERATION_FAILED"
    model_name = None
    token_usage = None
    try:
        memory_context = ""
        use_memory = get_settings().personal_memory_enabled and bool(user_memory_enabled)
        if use_memory or get_settings().personal_memory_shadow:
            async with session_factory() as retrieval_db:
                memory_context, _ = await retrieve_context(
                    retrieval_db, reflection.user_id, reflection.diary_entry_id, diary_content,
                    occurred_on=diary.created_at.date(),
                )
        if use_memory:
            output, provider_result = await generate_memory_reflection(
                diary_content, memory_context, get_llm_provider()
            )
        else:
            output, provider_result = await generate_reflection(diary_content, get_llm_provider())
        validate_output(output.reflection, diary_content)
    except OutputGuardrailError:
        status = "blocked"
        safety_status = "blocked"
        error_code = "OUTPUT_BLOCKED"
    except (LLMProviderError, ValueError):
        pass
    except Exception:
        logger.exception(
            "Unexpected reflection generation error",
            extra={"reflection_id": str(reflection_id)},
        )
        error_code = "INTERNAL_ERROR"
    else:
        status = "success"
        content = output.reflection
        error_code = None
        model_name = provider_result.model_name
        token_usage = provider_result.token_usage

    async with session_factory() as db:
        result = await db.execute(
            select(AiReflection)
            .join(DiaryEntry, DiaryEntry.id == AiReflection.diary_entry_id)
            .where(
                AiReflection.id == reflection_id,
                AiReflection.status == "pending",
                DiaryEntry.deleted_at.is_(None),
            )
        )
        reflection = result.scalar_one_or_none()
        if reflection is None:
            return
        reflection.status = status
        reflection.safety_status = safety_status
        reflection.content = content
        reflection.error_code = error_code
        reflection.model_name = model_name
        reflection.token_usage = token_usage
        reflection.latency_ms = int((time.perf_counter() - started) * 1000)
        await db.commit()
