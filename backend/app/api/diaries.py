import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import StorageBackend, get_storage_backend
from app.models.user import UserProfile
from app.schemas.diary import (
    CreateDiaryData,
    CreateDiaryResponse,
    DeleteDiaryData,
    DeleteDiaryResponse,
    DiaryDetailData,
    DiaryDetailResponse,
    DiaryListData,
    DiaryListResponse,
    DiaryResponse,
    DiaryCreateRequest,
)
from app.services.diary_service import (
    DiaryNotFoundError,
    DiaryDeleteError,
    DiaryImageInvalidError,
    create_diary,
    delete_diary,
    get_diary,
    list_diaries,
)
from app.services.image_service import list_diary_images

router = APIRouter(prefix="/diaries", tags=["diaries"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
Storage = Annotated[StorageBackend, Depends(get_storage_backend)]


def diary_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "DIARY_NOT_FOUND", "message": "日记不存在"},
    )


@router.post("", response_model=CreateDiaryResponse, status_code=status.HTTP_201_CREATED)
async def create_diary_endpoint(
    payload: DiaryCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CreateDiaryResponse:
    try:
        diary = await create_diary(
            db,
            current_user.id,
            content=payload.content,
            energy_score=payload.energy_score,
            mood_label=payload.mood_label,
            image_ids=payload.image_ids,
        )
    except DiaryImageInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "DIARY_IMAGE_INVALID", "message": "图片无效或不属于当前用户"},
        ) from exc
    return CreateDiaryResponse(
        data=CreateDiaryData(diaryId=diary.id, reflectionStatus="pending")
    )


@router.get("", response_model=DiaryListResponse)
async def list_diary_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, le=100000),
    limit: int = Query(default=20, ge=1, le=100),
) -> DiaryListResponse:
    diaries, has_more = await list_diaries(db, current_user.id, page=page, limit=limit)
    return DiaryListResponse(
        data=DiaryListData(
            list=[DiaryResponse.model_validate(diary) for diary in diaries],
            page=page,
            limit=limit,
            hasMore=has_more,
        )
    )


@router.get("/{diary_id}", response_model=DiaryDetailResponse)
async def get_diary_endpoint(
    diary_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DiaryDetailResponse:
    try:
        diary = await get_diary(db, current_user.id, diary_id)
    except DiaryNotFoundError:
        raise diary_not_found() from None
    images = await list_diary_images(db, current_user.id, diary.id)
    return DiaryDetailResponse(
        data=DiaryDetailData(
            diary=DiaryResponse.model_validate(diary),
            images=images,
        )
    )


@router.delete("/{diary_id}", response_model=DeleteDiaryResponse)
async def delete_diary_endpoint(
    diary_id: uuid.UUID,
    current_user: CurrentUser,
    storage: Storage,
    db: AsyncSession = Depends(get_db),
) -> DeleteDiaryResponse:
    try:
        await delete_diary(db, current_user.id, diary_id, storage)
    except DiaryNotFoundError:
        raise diary_not_found() from None
    except DiaryDeleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DIARY_DELETE_FAILED", "message": "日记删除失败，请稍后重试"},
        ) from exc
    return DeleteDiaryResponse(data=DeleteDiaryData(deleted=True))
