import io
import uuid

import httpx
import pytest
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import security
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.storage import LocalStorageBackend, StorageError, get_storage_backend
from app.main import app
from app.models.diary import DiaryEntry
from app.models.image import DiaryImage
from app.models.marker import TimelineMarker
from app.models.reflection import AiReflection
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user
from app.services.diary_service import create_diary
from app.services.image_service import create_image
from app.services.user_service import UserDataDeleteError, delete_user_data


def auth_settings() -> Settings:
    return Settings(jwt_secret="phase-eight-test-secret-at-least-32-characters")


def make_png() -> bytes:
    image = Image.new("RGB", (24, 24), (120, 145, 132))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_delete_current_user_removes_all_owned_data_only(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    suffix = uuid.uuid4()
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalStorageBackend(str(tmp_path))

    async with session_factory() as db:
        owner = await get_or_create_user(db, f"phase8-owner-{suffix}")
        other = await get_or_create_user(db, f"phase8-other-{suffix}")
        owner_id = owner.id
        other_id = other.id
        image = await create_image(db, owner_id, make_png(), storage)
        image_id = image.id
        storage_key = image.storage_key
        diary = await create_diary(
            db,
            owner_id,
            content="今天完成了账户数据删除测试。",
            energy_score=60,
            mood_label="明亮",
            image_ids=[image.id],
        )
        diary_id = diary.id

    async def override_get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_backend] = lambda: storage
    headers = {"Authorization": f"Bearer {security.create_access_token(owner_id)}"}
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/users/me", headers=headers)
            assert response.status_code == 200
            assert response.json()["data"]["deleted"] is True

            expired = await client.get("/api/v1/users/me", headers=headers)
            assert expired.status_code == 401

        assert not storage.path_for_key(storage_key).exists()
        async with session_factory() as db:
            assert await db.get(UserProfile, owner_id) is None
            assert await db.get(UserProfile, other_id) is not None
            assert await db.get(DiaryEntry, diary_id) is None
            assert await db.get(DiaryImage, image_id) is None
            assert await db.scalar(
                select(AiReflection).where(AiReflection.user_id == owner_id)
            ) is None
            assert await db.scalar(
                select(TimelineMarker).where(TimelineMarker.user_id == owner_id)
            ) is None
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_storage_backend, None)
        async with session_factory() as db:
            await db.execute(delete(UserProfile).where(UserProfile.id == other_id))
            await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_storage_failure_keeps_account_for_retry() -> None:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = None

    class FailingStorage:
        async def delete(self, _key: str) -> None:
            raise StorageError("delete failed")

    try:
        async with session_factory() as db:
            user = await get_or_create_user(db, f"phase8-failure-{uuid.uuid4()}")
            user_id = user.id
            db.add(
                DiaryImage(
                    user_id=user_id,
                    storage_key=f"users/{user_id}/images/failure.jpg",
                    url="/private/failure.jpg",
                    content_type="image/jpeg",
                    size_bytes=1,
                    status="success",
                )
            )
            await db.commit()

            with pytest.raises(UserDataDeleteError):
                await delete_user_data(db, user_id, FailingStorage())

            assert await db.get(UserProfile, user_id) is not None
    finally:
        if user_id is not None:
            async with session_factory() as db:
                await db.execute(delete(UserProfile).where(UserProfile.id == user_id))
                await db.commit()
        await engine.dispose()
