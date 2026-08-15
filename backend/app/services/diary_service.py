import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend, StorageError
from app.models.diary import DiaryEntry
from app.models.image import DiaryImage


class DiaryNotFoundError(Exception):
    pass


class DiaryImageInvalidError(Exception):
    pass


class DiaryDeleteError(Exception):
    pass


async def create_diary(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    content: str,
    energy_score: int,
    mood_label: str | None,
    image_ids: list[uuid.UUID],
) -> DiaryEntry:
    diary = DiaryEntry(
        user_id=user_id,
        content=content,
        energy_score=energy_score,
        mood_label=mood_label,
        privacy_status="private",
    )
    db.add(diary)
    await db.flush()

    if image_ids:
        result = await db.execute(
            select(DiaryImage)
            .where(
                DiaryImage.id.in_(image_ids),
                DiaryImage.user_id == user_id,
                DiaryImage.diary_id.is_(None),
                DiaryImage.status == "success",
                DiaryImage.deleted_at.is_(None),
            )
            .with_for_update()
        )
        images = {image.id: image for image in result.scalars().all()}
        if len(images) != len(image_ids):
            await db.rollback()
            raise DiaryImageInvalidError
        for sort_order, image_id in enumerate(image_ids):
            images[image_id].diary_id = diary.id
            images[image_id].sort_order = sort_order

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
    storage: StorageBackend,
) -> None:
    diary = await get_diary(db, user_id, diary_id)
    result = await db.execute(
        select(DiaryImage).where(
            DiaryImage.diary_id == diary.id,
            DiaryImage.user_id == user_id,
            DiaryImage.deleted_at.is_(None),
        )
    )
    images = list(result.scalars().all())
    try:
        for image in images:
            if image.status == "success":
                await storage.delete(image.storage_key)
    except StorageError as exc:
        await db.rollback()
        raise DiaryDeleteError from exc

    now = datetime.now(timezone.utc)
    diary.deleted_at = now
    diary.updated_at = now
    for image in images:
        image.status = "deleted"
        image.deleted_at = now
    await db.commit()
