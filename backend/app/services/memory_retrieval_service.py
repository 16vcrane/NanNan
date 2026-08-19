import re
import time
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryItem, RetrievalRun

RETRIEVER_VERSION = "memory_retrieval_v1"
MAX_CONTEXT_CHARS = 600
MAX_SELECTED = 3
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")


@dataclass(frozen=True)
class RetrievedMemory:
    item: MemoryItem
    score: float


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def _keyword_overlap(query: set[str], item: MemoryItem) -> float:
    value = _tokens(f"{item.label} {item.normalized_value} {item.evidence_text}")
    return len(query & value) / max(len(query), 1)


def _time_relevance(current: date | None, occurred: date | None) -> float:
    if not current or not occurred:
        return 0.0
    return max(0.0, 1.0 - min(abs((current - occurred).days), 3650) / 3650)


async def retrieve_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
    content: str,
    *,
    occurred_on: date | None = None,
    request_id: str | None = None,
) -> tuple[str, RetrievalRun]:
    started = time.perf_counter()
    query = _tokens(content)
    result = await db.execute(
        select(MemoryItem)
        .where(MemoryItem.user_id == user_id, MemoryItem.diary_entry_id != diary_id, MemoryItem.review_status.in_(("auto", "confirmed")))
        .order_by(MemoryItem.confidence.desc(), MemoryItem.created_at.desc())
        .limit(200)
    )
    candidates = list(result.scalars().all())
    ranked = []
    current_types = {item.type for item in candidates if _keyword_overlap(query, item) > 0}
    for item in candidates:
        overlap = _keyword_overlap(query, item)
        type_match = 1.0 if item.type in current_types and overlap > 0 else 0.0
        confirmed = 1.0 if item.review_status == "confirmed" else 0.0
        score = 0.35 * overlap + 0.25 * type_match + 0.20 * _time_relevance(occurred_on, item.occurred_on) + 0.15 * item.confidence + 0.05 * confirmed
        if score >= 0.20:
            ranked.append(RetrievedMemory(item, score))
    ranked.sort(key=lambda value: (-value.score, value.item.created_at))
    selected = []
    source_counts: dict[uuid.UUID, int] = {}
    for candidate in ranked:
        count = source_counts.get(candidate.item.diary_entry_id, 0)
        if count >= 2:
            continue
        selected.append(candidate)
        source_counts[candidate.item.diary_entry_id] = count + 1
        if len(selected) >= MAX_SELECTED:
            break
    lines = []
    for candidate in selected:
        item = candidate.item
        line = f"[{item.occurred_on or 'unknown date'}] {item.type}: {item.normalized_value} - {item.evidence_text}"
        remaining = MAX_CONTEXT_CHARS - sum(len(existing) + 1 for existing in lines)
        if remaining <= 0:
            break
        lines.append(line[:remaining])
    audit = RetrievalRun(
        request_id=request_id,
        user_id=user_id,
        diary_entry_id=diary_id,
        retriever_version=RETRIEVER_VERSION,
        candidate_count=len(candidates),
        selected_memory_ids=[str(candidate.item.id) for candidate in selected],
        latency_ms=int((time.perf_counter() - started) * 1000),
        status="success",
    )
    db.add(audit)
    await db.commit()
    return "\n".join(lines), audit
