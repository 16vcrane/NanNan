from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MemoryItemType = Literal[
    "person",
    "event",
    "place",
    "achievement",
    "relationship",
    "life_stage",
]


class MemoryExtractionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MemoryItemType
    label: str = Field(min_length=1, max_length=96)
    normalized_value: str = Field(alias="normalizedValue", min_length=1, max_length=96)
    evidence: str = Field(min_length=1, max_length=512)
    start_offset: int = Field(alias="startOffset", ge=0)
    end_offset: int = Field(alias="endOffset", gt=0)
    confidence: float = Field(ge=0, le=1)
    occurred_on: date | None = Field(default=None, alias="occurredOn")
    attributes: dict[str, str] = Field(default_factory=dict, max_length=8)

    @field_validator("label", "normalized_value", "evidence")
    @classmethod
    def field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("memory fields must not be blank")
        return value


class MemoryExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MemoryExtractionItem] = Field(default_factory=list, max_length=12)
