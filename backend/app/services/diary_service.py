import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diary import DiaryEntry


class DiaryNotFoundError(Exception):
    pass


async def create_diary(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    content: str,
    energy_score: int,
    mood_label: str | None,
) -> DiaryEntry:
    diary = DiaryEntry(
        user_id=user_id,
        content=content,
        energy_score=energy_score,
        mood_label=mood_label,
        privacy_status="private",
    )
    db.add(diary)
    await db.commit()
    await db.refresh(diary)
    return diary


async def list_diaries(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int,
    limit: int,
) -> tuple[list[DiaryEntry], bool]:
    statement: Select[tuple[DiaryEntry]] = (
        select(DiaryEntry)
        .where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.deleted_at.is_(None),
        )
        .order_by(DiaryEntry.created_at.desc(), DiaryEntry.id.desc())
        .offset((page - 1) * limit)
        .limit(limit + 1)
    )
    result = await db.execute(statement)
    entries = list(result.scalars().all())
    has_more = len(entries) > limit
    return entries[:limit], has_more


async def get_diary(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
) -> DiaryEntry:
    statement = select(DiaryEntry).where(
        DiaryEntry.id == diary_id,
        DiaryEntry.user_id == user_id,
        DiaryEntry.deleted_at.is_(None),
    )
    result = await db.execute(statement)
    diary = result.scalar_one_or_none()
    if diary is None:
        raise DiaryNotFoundError
    return diary


async def delete_diary(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
) -> None:
    diary = await get_diary(db, user_id, diary_id)
    now = datetime.now(timezone.utc)
    diary.deleted_at = now
    diary.updated_at = now
    await db.commit()
