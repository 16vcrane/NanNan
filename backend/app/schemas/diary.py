import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.upload import ImageResponse


class DiaryCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(min_length=1, max_length=3000)
    energy_score: int = Field(default=50, alias="energyScore", ge=0, le=100)
    mood_label: str | None = Field(default=None, alias="moodLabel", max_length=32)
    image_ids: list[uuid.UUID] = Field(default_factory=list, alias="imageIds", max_length=3)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("日记内容不能为空")
        return value

    @field_validator("image_ids")
    @classmethod
    def image_ids_must_be_unique(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("不能重复选择同一张图片")
        return value


class DiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    content: str
    energy_score: int = Field(alias="energyScore")
    mood_label: str | None = Field(alias="moodLabel")
    privacy_status: str = Field(alias="privacyStatus")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CreateDiaryData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    diary_id: uuid.UUID = Field(alias="diaryId")
    reflection_status: str = Field(default="pending", alias="reflectionStatus")


class CreateDiaryResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: CreateDiaryData


class DiaryListData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[DiaryResponse]
    page: int
    limit: int
    has_more: bool = Field(alias="hasMore")


class DiaryListResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DiaryListData


class DiaryDetailData(BaseModel):
    diary: DiaryResponse
    images: list[ImageResponse] = Field(default_factory=list)
    reflection: dict | None = None
    markers: list[dict] = Field(default_factory=list)


class DiaryDetailResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DiaryDetailData


class DeleteDiaryData(BaseModel):
    deleted: bool = True


class DeleteDiaryResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DeleteDiaryData
