import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ai_reflection_enabled: bool = Field(alias="aiReflectionEnabled")
    personal_memory_enabled: bool = Field(alias="personalMemoryEnabled")
    anniversary_reminder_enabled: bool = Field(alias="anniversaryReminderEnabled")
    third_person_unlocked: bool = Field(alias="thirdPersonUnlocked")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    created_at: datetime = Field(alias="createdAt")
    last_active_at: datetime = Field(alias="lastActiveAt")
    settings: UserSettingsResponse

    @classmethod
    def from_user(cls, user: object) -> "UserResponse":
        return cls(
            id=user.id,
            createdAt=user.created_at,
            lastActiveAt=user.last_active_at,
            settings=UserSettingsResponse(
                aiReflectionEnabled=user.ai_reflection_enabled,
                personalMemoryEnabled=bool(user.personal_memory_enabled),
                anniversaryReminderEnabled=user.anniversary_reminder_enabled,
                thirdPersonUnlocked=user.third_person_unlocked,
            ),
        )


class LoginData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    user: UserResponse


class LoginResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: LoginData


class CurrentUserResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: UserResponse
