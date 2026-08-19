import hashlib
import time
import uuid
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.memory_extraction import PROMPT_VERSION, extract_memories
from app.ai.provider import LLMProviderError, get_llm_provider
from app.models.diary import DiaryEntry
from app.models.memory import MemoryExtraction, MemoryItem
from app.core.database import SessionLocal

_locks: defaultdict[uuid.UUID, object] = defaultdict(object)


async def create_memory_extraction(db: AsyncSession, diary: DiaryEntry) -> MemoryExtraction:
    extraction = MemoryExtraction(
        diary_entry_id=diary.id,
        user_id=diary.user_id,
        extractor_version=PROMPT_VERSION,
        source_content_hash=hashlib.sha256(diary.content.encode("utf-8")).hexdigest(),
        status="pending",
    )
    db.add(extraction)
    await db.flush()
    return extraction


async def run_memory_extraction_task(
    extraction_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
) -> None:
    async with session_factory() as db:
        result = await db.execute(
            select(MemoryExtraction, DiaryEntry)
            .join(DiaryEntry, DiaryEntry.id == MemoryExtraction.diary_entry_id)
            .where(
                MemoryExtraction.id == extraction_id,
                MemoryExtraction.status == "pending",
                DiaryEntry.deleted_at.is_(None),
            )
        )
        row = result.one_or_none()
        if row is None:
            return
        extraction, diary = row
        current_hash = hashlib.sha256(diary.content.encode("utf-8")).hexdigest()
        if current_hash != extraction.source_content_hash:
            extraction.status = "blocked"
            extraction.error_code = "SOURCE_CHANGED"
            await db.commit()
            return
        extraction.status = "processing"
        extraction.attempt_count += 1
        content = diary.content
        await db.commit()

    started = time.perf_counter()
    status = "failed"
    error_code = "EXTRACTION_FAILED"
    model_name = None
    token_usage = None
    items = []
    try:
        if len(content.strip()) < 2:
            status, error_code = "blocked", "CONTENT_TOO_SHORT"
        else:
            output, provider_result = await extract_memories(content, get_llm_provider())
            items = output.items
            status = "success"
            error_code = None
            model_name = provider_result.model_name
            token_usage = provider_result.token_usage
    except (LLMProviderError, ValueError):
        pass
    except Exception:
        error_code = "INTERNAL_ERROR"

    async with session_factory() as db:
        result = await db.execute(
            select(MemoryExtraction, DiaryEntry)
            .join(DiaryEntry, DiaryEntry.id == MemoryExtraction.diary_entry_id)
            .where(MemoryExtraction.id == extraction_id, DiaryEntry.deleted_at.is_(None))
        )
        row = result.one_or_none()
        if row is None:
            return
        extraction, diary = row
        if hashlib.sha256(diary.content.encode("utf-8")).hexdigest() != extraction.source_content_hash:
            extraction.status = "blocked"
            extraction.error_code = "SOURCE_CHANGED"
            await db.commit()
            return
        if status == "success":
            await db.execute(delete(MemoryItem).where(MemoryItem.extraction_id == extraction.id))
            db.add_all(
                MemoryItem(
                    extraction_id=extraction.id,
                    diary_entry_id=diary.id,
                    user_id=diary.user_id,
                    type=item.type,
                    label=item.label,
                    normalized_value=item.normalized_value,
                    evidence_text=item.evidence,
                    evidence_start=item.start_offset,
                    evidence_end=item.end_offset,
                    confidence=item.confidence,
                    occurred_on=item.occurred_on,
                    attributes_json=item.attributes,
                )
                for item in items
            )
        extraction.status = status
        extraction.error_code = error_code
        extraction.model_name = model_name
        extraction.token_usage = token_usage
        extraction.latency_ms = int((time.perf_counter() - started) * 1000)
        await db.commit()
