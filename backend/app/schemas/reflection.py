import uuid
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ReflectionOutput(BaseModel):
    reflection: str = Field(min_length=30, max_length=80)
    keywords: list[str] = Field(default_factory=list, max_length=5)
    tone: Literal["warm"]

    @field_validator("reflection")
    @classmethod
    def normalize_reflection(cls, value: str) -> str:
        value = " ".join(value.split())
        if not 30 <= len(value) <= 80:
            raise ValueError("reflection must contain 30-80 characters")
        return value

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))[:5]


class ReflectionData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    diary_id: uuid.UUID = Field(
        alias="diaryId",
        validation_alias=AliasChoices("diaryId", "diary_entry_id"),
    )
    status: Literal["pending", "success", "failed", "blocked"]
    content: str | None = None
    safety_status: Literal["safe", "sensitive", "blocked"] = Field(alias="safetyStatus")
    can_retry: bool = Field(default=False, alias="canRetry")
    attempt_count: int = Field(alias="attemptCount")


class ReflectionResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: ReflectionData


class RetryReflectionData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["pending"] = "pending"
    attempt_count: int = Field(alias="attemptCount")


class RetryReflectionResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: RetryReflectionData
