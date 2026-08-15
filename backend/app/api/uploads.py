import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import StorageBackend, StorageError, get_storage_backend
from app.models.user import UserProfile
from app.schemas.upload import (
    DeleteImageData,
    DeleteImageResponse,
    ImageResponse,
    UploadImageResponse,
)
from app.services.image_service import (
    MAX_UPLOAD_BYTES,
    ImageAlreadyAttachedError,
    ImageNotFoundError,
    ImageValidationError,
    create_image,
    delete_unattached_image,
    get_owned_image,
)

router = APIRouter(prefix="/uploads/images", tags=["uploads"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
Storage = Annotated[StorageBackend, Depends(get_storage_backend)]


def image_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "IMAGE_NOT_FOUND", "message": "图片不存在"},
    )


@router.post("", response_model=UploadImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    current_user: CurrentUser,
    storage: Storage,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> UploadImageResponse:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        image = await create_image(db, current_user.id, content, storage)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "IMAGE_INVALID", "message": str(exc)},
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IMAGE_UPLOAD_FAILED", "message": "图片上传失败"},
        ) from exc
    return UploadImageResponse(data=ImageResponse.model_validate(image))


@router.get("/{image_id}/content")
async def get_image_content(
    image_id: uuid.UUID,
    current_user: CurrentUser,
    storage: Storage,
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        image = await get_owned_image(
            db, current_user.id, image_id, require_success=True
        )
        content = await storage.read(image.storage_key)
    except (ImageNotFoundError, StorageError):
        raise image_not_found() from None
    return Response(
        content=content,
        media_type=image.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete("/{image_id}", response_model=DeleteImageResponse)
async def delete_image(
    image_id: uuid.UUID,
    current_user: CurrentUser,
    storage: Storage,
    db: AsyncSession = Depends(get_db),
) -> DeleteImageResponse:
    try:
        await delete_unattached_image(db, current_user.id, image_id, storage)
    except ImageNotFoundError:
        raise image_not_found() from None
    except ImageAlreadyAttachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "IMAGE_ALREADY_ATTACHED", "message": "图片已关联日记"},
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IMAGE_DELETE_FAILED", "message": "图片删除失败"},
        ) from exc
    return DeleteImageResponse(data=DeleteImageData(deleted=True))
