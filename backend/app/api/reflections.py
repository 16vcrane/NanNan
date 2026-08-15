import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.schemas.reflection import (
    ReflectionData,
    ReflectionResponse,
    RetryReflectionData,
    RetryReflectionResponse,
)
from app.services.reflection_service import (
    ReflectionNotFoundError,
    ReflectionRetryNotAllowedError,
    can_retry,
    get_reflection,
    request_retry,
    run_reflection_task,
)

router = APIRouter(prefix="/diaries", tags=["reflections"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]


def reflection_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "REFLECTION_NOT_FOUND", "message": "AI 回响不存在"},
    )


def serialize_reflection(reflection) -> ReflectionData:
    return ReflectionData(
        id=reflection.id,
        diaryId=reflection.diary_entry_id,
        status=reflection.status,
        content=reflection.content,
        safetyStatus=reflection.safety_status,
        canRetry=can_retry(reflection),
        attemptCount=reflection.attempt_count,
    )


@router.get("/{diary_id}/reflection", response_model=ReflectionResponse)
async def get_reflection_endpoint(
    diary_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ReflectionResponse:
    try:
        reflection = await get_reflection(db, current_user.id, diary_id)
    except ReflectionNotFoundError:
        raise reflection_not_found() from None
    return ReflectionResponse(data=serialize_reflection(reflection))


@router.post(
    "/{diary_id}/reflection/retry",
    response_model=RetryReflectionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_reflection_endpoint(
    diary_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RetryReflectionResponse:
    try:
        reflection = await request_retry(db, current_user.id, diary_id)
    except ReflectionNotFoundError:
        raise reflection_not_found() from None
    except ReflectionRetryNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFLECTION_RETRY_NOT_ALLOWED",
                "message": "当前回响不可重试或已达到重试上限",
            },
        ) from exc
    task_sessions = async_sessionmaker(db.bind, expire_on_commit=False)
    background_tasks.add_task(run_reflection_task, reflection.id, task_sessions)
    return RetryReflectionResponse(
        data=RetryReflectionData(attemptCount=reflection.attempt_count)
    )
