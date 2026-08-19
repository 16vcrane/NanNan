import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import security
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.models.diary import DiaryEntry
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user
from app.services.memory_service import find_on_this_day


def auth_settings() -> Settings:
    return Settings(jwt_secret="phase-one-test-secret-at-least-32-characters")


def local_utc(year: int, month: int, day: int, hour: int = 8) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(
        timezone.utc
    )


@pytest.mark.asyncio
async def test_on_this_day_service_prefers_same_date_and_respects_timezone(monkeypatch):
    monkeypatch.setattr(security, "get_settings", auth_settings)
    suffix = uuid.uuid4()
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = await get_or_create_user(db, f"on-this-day-{suffix}")
        user_id = user.id
        db.add_all(
            [
                DiaryEntry(
                    user_id=user_id,
                    content="2023 同月同日",
                    energy_score=82,
                    mood_label="明亮",
                    privacy_status="private",
                    created_at=local_utc(2023, 3, 1, 10),
                    updated_at=local_utc(2023, 3, 1, 10),
                ),
                DiaryEntry(
                    user_id=user_id,
                    content="2022 同月同日",
                    energy_score=61,
                    mood_label="平静",
                    privacy_status="private",
                    created_at=local_utc(2022, 3, 1, 10),
                    updated_at=local_utc(2022, 3, 1, 10),
                ),
                DiaryEntry(
                    user_id=user_id,
                    content="30 天前",
                    energy_score=55,
                    mood_label="平静",
                    privacy_status="private",
                    created_at=local_utc(2024, 1, 31, 10),
                    updated_at=local_utc(2024, 1, 31, 10),
                ),
                DiaryEntry(
                    user_id=user_id,
                    content="已删除",
                    energy_score=55,
                    mood_label="平静",
                    privacy_status="private",
                    created_at=local_utc(2023, 3, 1, 9),
                    updated_at=local_utc(2023, 3, 1, 9),
                    deleted_at=local_utc(2023, 3, 2, 9),
                ),
            ]
        )
        await db.commit()

        today, candidates = await find_on_this_day(
            db,
            user_id,
            "Asia/Shanghai",
            now=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert today.isoformat() == "2024-03-01"
        assert [candidate.diary.content for candidate in candidates] == [
            "2023 同月同日",
            "2022 同月同日",
            "30 天前",
        ]
        assert [candidate.source for candidate in candidates] == [
            "same_date",
            "same_date",
            "30d",
        ]
        assert candidates[0].distance_days == 366
        assert candidates[2].distance_days == 30

    async with session_factory() as db:
        await db.execute(delete(UserProfile).where(UserProfile.id == user_id))
        await db.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_on_this_day_endpoint_validates_timezone(monkeypatch) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    suffix = uuid.uuid4()
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = await get_or_create_user(db, f"on-this-day-api-{suffix}")
        user_id = user.id

    async def override_get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    headers = {"Authorization": f"Bearer {security.create_access_token(user_id)}"}
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/memories/on-this-day?timezone=Not/A_Zone",
                headers=headers,
            )
            assert response.status_code == 400
            assert response.json()["code"] == "TIMEZONE_INVALID"
    finally:
        app.dependency_overrides.pop(get_db, None)
        async with session_factory() as db:
            await db.execute(delete(UserProfile).where(UserProfile.id == user_id))
            await db.commit()
        await engine.dispose()
