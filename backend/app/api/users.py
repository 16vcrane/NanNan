from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.user import UserProfile
from app.schemas.auth import CurrentUserResponse, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(data=UserResponse.from_user(current_user))
