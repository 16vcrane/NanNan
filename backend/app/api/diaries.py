import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    MarkerResponse,
)
from app.schemas.upload import ImageResponse
from app.services.diary_service import (
    DiaryNotFoundError,
    DiaryDeleteError,
    DiaryImageInvalidError,
    create_diary,
    delete_diary,
    get_diary,
    list_diaries,
)
from app.services.image_service import list_diary_images, list_images_for_diaries
from app.api.reflections import serialize_reflection
from app.services.reflection_service import (
    ReflectionNotFoundError,
    get_reflection,
    run_reflection_task,
)
from app.services.marker_service import list_markers_for_diaries

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
    background_tasks: BackgroundTasks,
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
    task_sessions = async_sessionmaker(db.bind, expire_on_commit=False)
    background_tasks.add_task(
        run_reflection_task, diary.ai_reflection_id, task_sessions
    )
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
    marker_groups = await list_markers_for_diaries(
        db, current_user.id, [diary.id for diary in diaries]
    )
    image_groups = await list_images_for_diaries(
        db, current_user.id, [diary.id for diary in diaries]
    )
    diary_responses = []
    for diary in diaries:
        response = DiaryResponse.model_validate(diary)
        response.markers = [
            MarkerResponse.model_validate(marker)
            for marker in marker_groups.get(diary.id, [])
        ]
        response.images = [
            ImageResponse.model_validate(image)
            for image in image_groups.get(diary.id, [])
        ]
        diary_responses.append(response)
    return DiaryListResponse(
        data=DiaryListData(
            list=diary_responses,
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
    marker_groups = await list_markers_for_diaries(
        db, current_user.id, [diary.id]
    )
    markers = [
        MarkerResponse.model_validate(marker)
        for marker in marker_groups.get(diary.id, [])
    ]
    try:
        reflection = serialize_reflection(
            await get_reflection(db, current_user.id, diary.id)
        ).model_dump(by_alias=True)
    except ReflectionNotFoundError:
        reflection = None
    return DiaryDetailResponse(
        data=DiaryDetailData(
            diary=DiaryResponse.model_validate(diary),
            images=images,
            reflection=reflection,
            markers=markers,
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
