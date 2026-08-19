from datetime import date, datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class OnThisDayItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    diary_id: uuid.UUID = Field(alias="diaryId")
    date: date
    created_at: datetime = Field(alias="createdAt")
    energy_score: int = Field(alias="energyScore")
    mood_label: str | None = Field(alias="moodLabel")
    summary: str
    source: str
    distance_days: int = Field(alias="distanceDays")


class OnThisDayData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    today: date
    timezone: str
    items: list[OnThisDayItem] = Field(default_factory=list)


class OnThisDayResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: OnThisDayData
