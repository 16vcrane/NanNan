import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend, StorageError
from app.models.image import DiaryImage
from app.models.user import UserProfile


class UserDataDeleteError(Exception):
    pass


async def delete_user_data(
    db: AsyncSession,
    user_id: uuid.UUID,
    storage: StorageBackend,
) -> None:
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserDataDeleteError

        image_result = await db.execute(
            select(DiaryImage.storage_key).where(DiaryImage.user_id == user_id)
        )
        storage_keys = list(dict.fromkeys(image_result.scalars().all()))
    except SQLAlchemyError as exc:
        await db.rollback()
        raise UserDataDeleteError from exc
    try:
        for storage_key in storage_keys:
            await storage.delete(storage_key)
    except StorageError as exc:
        await db.rollback()
        raise UserDataDeleteError from exc

    try:
        await db.delete(user)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise UserDataDeleteError from exc
