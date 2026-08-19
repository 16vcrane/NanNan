from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.schemas.memory import OnThisDayData, OnThisDayItem, OnThisDayResponse
from app.services.memory_service import InvalidTimezoneError, find_on_this_day, summarize_content

router = APIRouter(prefix="/memories", tags=["memories"])
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]


@router.get("/on-this-day", response_model=OnThisDayResponse)
async def get_on_this_day(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    timezone_name: str = Query(default="UTC", alias="timezone", min_length=1, max_length=64),
) -> OnThisDayResponse:
    try:
        today, candidates = await find_on_this_day(db, current_user.id, timezone_name)
    except InvalidTimezoneError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TIMEZONE_INVALID",
                "message": "时区无效，请使用 IANA 时区名称",
            },
        ) from exc

    items = [
        OnThisDayItem(
            diaryId=candidate.diary.id,
            date=candidate.local_date,
            createdAt=candidate.diary.created_at,
            energyScore=candidate.diary.energy_score,
            moodLabel=candidate.diary.mood_label,
            summary=summarize_content(candidate.diary.content),
            source=candidate.source,
            distanceDays=candidate.distance_days,
        )
        for candidate in candidates
    ]
    return OnThisDayResponse(
        data=OnThisDayData(today=today, timezone=timezone_name, items=items)
    )
