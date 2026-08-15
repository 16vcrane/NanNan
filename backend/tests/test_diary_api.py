import uuid

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import security
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.models.diary import DiaryEntry
from app.models.reflection import AiReflection
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user
from app.ai.provider import LLMProviderError
from app.services import reflection_service


def auth_settings() -> Settings:
    return Settings(jwt_secret="phase-two-test-secret-at-least-32-characters")


@pytest.mark.asyncio
async def test_diary_crud_and_user_isolation(monkeypatch) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)

    def unconfigured_provider():
        raise LLMProviderError("not configured in API test")

    monkeypatch.setattr(reflection_service, "get_llm_provider", unconfigured_provider)
    suffix = uuid.uuid4()
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        first_user = await get_or_create_user(db, f"phase2-first-{suffix}")
        second_user = await get_or_create_user(db, f"phase2-second-{suffix}")
        first_user_id = first_user.id
        second_user_id = second_user.id

    async def override_get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    first_headers = {
        "Authorization": f"Bearer {security.create_access_token(first_user_id)}"
    }
    second_headers = {
        "Authorization": f"Bearer {security.create_access_token(second_user_id)}"
    }
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/api/v1/diaries",
                headers=first_headers,
                json={
                    "content": "今天完成了 Phase 2。",
                    "energyScore": 72,
                    "moodLabel": "明亮",
                    "imageIds": [],
                },
            )
            assert create_response.status_code == 201
            diary_id = create_response.json()["data"]["diaryId"]

            second_create_response = await client.post(
                "/api/v1/diaries",
                headers=first_headers,
                json={"content": "用于验证分页。", "imageIds": []},
            )
            assert second_create_response.status_code == 201

            list_response = await client.get(
                "/api/v1/diaries?limit=1", headers=first_headers
            )
            assert list_response.status_code == 200
            assert len(list_response.json()["data"]["list"]) == 1
            assert list_response.json()["data"]["hasMore"] is True

            detail_response = await client.get(
                f"/api/v1/diaries/{diary_id}", headers=first_headers
            )
            assert detail_response.status_code == 200
            assert detail_response.json()["data"]["diary"]["energyScore"] == 72
            assert detail_response.json()["data"]["images"] == []

            foreign_response = await client.get(
                f"/api/v1/diaries/{diary_id}", headers=second_headers
            )
            assert foreign_response.status_code == 404
            assert foreign_response.json()["code"] == "DIARY_NOT_FOUND"

            foreign_delete_response = await client.delete(
                f"/api/v1/diaries/{diary_id}", headers=second_headers
            )
            assert foreign_delete_response.status_code == 404

            reflection_response = await client.get(
                f"/api/v1/diaries/{diary_id}/reflection", headers=first_headers
            )
            assert reflection_response.status_code == 200
            reflection_data = reflection_response.json()["data"]
            assert reflection_data["status"] == "failed"
            assert reflection_data["attemptCount"] == 1
            assert reflection_data["canRetry"] is True

            foreign_reflection = await client.get(
                f"/api/v1/diaries/{diary_id}/reflection", headers=second_headers
            )
            assert foreign_reflection.status_code == 404

            retry_response = await client.post(
                f"/api/v1/diaries/{diary_id}/reflection/retry", headers=first_headers
            )
            assert retry_response.status_code == 202
            retried_reflection = await client.get(
                f"/api/v1/diaries/{diary_id}/reflection", headers=first_headers
            )
            assert retried_reflection.json()["data"]["status"] == "failed"
            assert retried_reflection.json()["data"]["attemptCount"] == 2

            delete_response = await client.delete(
                f"/api/v1/diaries/{diary_id}", headers=first_headers
            )
            assert delete_response.status_code == 200
            assert delete_response.json()["data"]["deleted"] is True

            deleted_response = await client.get(
                f"/api/v1/diaries/{diary_id}", headers=first_headers
            )
            assert deleted_response.status_code == 404

            async with session_factory() as db:
                deleted_reflection = await db.scalar(
                    select(AiReflection).where(
                        AiReflection.diary_entry_id == uuid.UUID(diary_id)
                    )
                )
                assert deleted_reflection is None
    finally:
        app.dependency_overrides.pop(get_db, None)
        async with session_factory() as db:
            await db.execute(
                delete(DiaryEntry).where(
                    DiaryEntry.user_id.in_([first_user_id, second_user_id])
                )
            )
            await db.execute(
                delete(UserProfile).where(
                    UserProfile.id.in_([first_user_id, second_user_id])
                )
            )
            await db.commit()
        await engine.dispose()
