import asyncio
import io
import uuid
from datetime import datetime, timezone

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend, StorageError
from app.models.image import DiaryImage

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_SIDE = 2048
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageValidationError(Exception):
    pass


class ImageNotFoundError(Exception):
    pass


class ImageAlreadyAttachedError(Exception):
    pass


def normalize_image(content: bytes) -> bytes:
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ImageValidationError("图片大小不能超过 10MB")
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ImageValidationError("图片尺寸过大")
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            normalized = ImageOps.exif_transpose(source)
            normalized.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            if normalized.mode not in ("RGB", "L"):
                background = Image.new("RGB", normalized.size, "white")
                if "A" in normalized.getbands():
                    background.paste(normalized, mask=normalized.getchannel("A"))
                else:
                    background.paste(normalized)
                normalized = background
            elif normalized.mode == "L":
                normalized = normalized.convert("RGB")

            output = io.BytesIO()
            normalized.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("图片格式无效") from exc


async def create_image(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: bytes,
    storage: StorageBackend,
) -> DiaryImage:
    normalized = await asyncio.to_thread(normalize_image, content)
    image_id = uuid.uuid4()
    storage_key = f"users/{user_id}/images/{image_id}.jpg"
    image = DiaryImage(
        id=image_id,
        user_id=user_id,
        storage_key=storage_key,
        url=f"/api/v1/uploads/images/{image_id}/content",
        content_type="image/jpeg",
        size_bytes=len(normalized),
        status="uploading",
    )
    db.add(image)
    await db.commit()

    try:
        await storage.write(storage_key, normalized, "image/jpeg")
    except StorageError:
        image.status = "failed"
        await db.commit()
        raise

    image.status = "success"
    await db.commit()
    await db.refresh(image)
    return image


async def get_owned_image(
    db: AsyncSession,
    user_id: uuid.UUID,
    image_id: uuid.UUID,
    *,
    require_success: bool = False,
) -> DiaryImage:
    filters = [
        DiaryImage.id == image_id,
        DiaryImage.user_id == user_id,
        DiaryImage.deleted_at.is_(None),
    ]
    if require_success:
        filters.append(DiaryImage.status == "success")
    result = await db.execute(select(DiaryImage).where(*filters))
    image = result.scalar_one_or_none()
    if image is None:
        raise ImageNotFoundError
    return image


async def list_diary_images(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_id: uuid.UUID,
) -> list[DiaryImage]:
    result = await db.execute(
        select(DiaryImage)
        .where(
            DiaryImage.user_id == user_id,
            DiaryImage.diary_id == diary_id,
            DiaryImage.status == "success",
            DiaryImage.deleted_at.is_(None),
        )
        .order_by(DiaryImage.sort_order.asc())
    )
    return list(result.scalars().all())


async def list_images_for_diaries(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[DiaryImage]]:
    grouped = {diary_id: [] for diary_id in diary_ids}
    if not diary_ids:
        return grouped
    result = await db.execute(
        select(DiaryImage)
        .where(
            DiaryImage.user_id == user_id,
            DiaryImage.diary_id.in_(diary_ids),
            DiaryImage.status == "success",
            DiaryImage.deleted_at.is_(None),
        )
        .order_by(DiaryImage.diary_id, DiaryImage.sort_order.asc())
    )
    for image in result.scalars().all():
        grouped[image.diary_id].append(image)
    return grouped


async def delete_unattached_image(
    db: AsyncSession,
    user_id: uuid.UUID,
    image_id: uuid.UUID,
    storage: StorageBackend,
) -> None:
    image = await get_owned_image(db, user_id, image_id)
    if image.diary_id is not None:
        raise ImageAlreadyAttachedError
    if image.status == "success":
        await storage.delete(image.storage_key)
    image.status = "deleted"
    image.deleted_at = datetime.now(timezone.utc)
    await db.commit()
