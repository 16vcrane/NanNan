from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import StorageBackend, get_storage_backend
from app.models.user import UserProfile
from app.schemas.auth import CurrentUserResponse, UserResponse
from app.schemas.user import (
    AiPreferencesData,
    AiPreferencesResponse,
    AiPreferencesUpdate,
    DeleteCurrentUserData,
    DeleteCurrentUserResponse,
)
from app.services.user_service import UserDataDeleteError, delete_user_data

router = APIRouter(prefix="/users", tags=["users"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
Storage = Annotated[StorageBackend, Depends(get_storage_backend)]


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(data=UserResponse.from_user(current_user))


@router.patch("/me/ai-preferences", response_model=AiPreferencesResponse)
async def update_ai_preferences(
    payload: AiPreferencesUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AiPreferencesResponse:
    current_user.personal_memory_enabled = payload.personal_memory_enabled
    await db.commit()
    return AiPreferencesResponse(
        data=AiPreferencesData(personalMemoryEnabled=current_user.personal_memory_enabled)
    )


@router.delete("/me", response_model=DeleteCurrentUserResponse)
async def delete_me(
    current_user: CurrentUser,
    storage: Storage,
    db: AsyncSession = Depends(get_db),
) -> DeleteCurrentUserResponse:
    try:
        await delete_user_data(db, current_user.id, storage)
    except UserDataDeleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "USER_DATA_DELETE_FAILED",
                "message": "数据删除失败，请稍后重试",
            },
        ) from exc
    return DeleteCurrentUserResponse(data=DeleteCurrentUserData(deleted=True))
