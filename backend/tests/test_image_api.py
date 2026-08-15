import io
import uuid

import httpx
import pytest
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import security
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.storage import LocalStorageBackend, get_storage_backend
from app.main import app
from app.models.diary import DiaryEntry
from app.models.image import DiaryImage
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user


def auth_settings() -> Settings:
    return Settings(jwt_secret="phase-four-test-secret-at-least-32-characters")


def make_png() -> bytes:
    image = Image.new("RGB", (48, 32), (226, 151, 86))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_image_upload_permissions_attachment_and_cleanup(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    suffix = uuid.uuid4()
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalStorageBackend(str(tmp_path))

    async with session_factory() as db:
        first_user = await get_or_create_user(db, f"phase4-first-{suffix}")
        second_user = await get_or_create_user(db, f"phase4-second-{suffix}")
        first_user_id = first_user.id
        second_user_id = second_user.id

    async def override_get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_backend] = lambda: storage
    first_headers = {
        "Authorization": f"Bearer {security.create_access_token(first_user_id)}"
    }
    second_headers = {
        "Authorization": f"Bearer {security.create_access_token(second_user_id)}"
    }
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            invalid_upload = await client.post(
                "/api/v1/uploads/images",
                headers=first_headers,
                files={"file": ("note.txt", b"not-an-image", "text/plain")},
            )
            assert invalid_upload.status_code == 422
            assert invalid_upload.json()["code"] == "IMAGE_INVALID"

            oversized_upload = await client.post(
                "/api/v1/uploads/images",
                headers=first_headers,
                files={"file": ("large.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")},
            )
            assert oversized_upload.status_code == 422
            assert oversized_upload.json()["code"] == "IMAGE_INVALID"

            upload_response = await client.post(
                "/api/v1/uploads/images",
                headers=first_headers,
                files={"file": ("memory.png", make_png(), "image/png")},
            )
            assert upload_response.status_code == 201
            image_data = upload_response.json()["data"]
            image_id = image_data["id"]
            assert image_data["contentType"] == "image/jpeg"
            assert image_data["status"] == "success"

            own_content = await client.get(image_data["url"], headers=first_headers)
            assert own_content.status_code == 200
            assert own_content.headers["content-type"] == "image/jpeg"

            foreign_content = await client.get(image_data["url"], headers=second_headers)
            assert foreign_content.status_code == 404
            foreign_delete = await client.delete(
                f"/api/v1/uploads/images/{image_id}", headers=second_headers
            )
            assert foreign_delete.status_code == 404

            second_upload = await client.post(
                "/api/v1/uploads/images",
                headers=second_headers,
                files={"file": ("foreign.png", make_png(), "image/png")},
            )
            foreign_image_id = second_upload.json()["data"]["id"]
            invalid_attach = await client.post(
                "/api/v1/diaries",
                headers=first_headers,
                json={"content": "不能关联其他用户图片", "imageIds": [foreign_image_id]},
            )
            assert invalid_attach.status_code == 400
            assert invalid_attach.json()["code"] == "DIARY_IMAGE_INVALID"

            create_diary = await client.post(
                "/api/v1/diaries",
                headers=first_headers,
                json={"content": "带图片的日记", "imageIds": [image_id]},
            )
            assert create_diary.status_code == 201
            diary_id = create_diary.json()["data"]["diaryId"]

            detail = await client.get(
                f"/api/v1/diaries/{diary_id}", headers=first_headers
            )
            assert detail.status_code == 200
            assert [item["id"] for item in detail.json()["data"]["images"]] == [image_id]

            timeline = await client.get(
                "/api/v1/diaries?page=1&limit=20", headers=first_headers
            )
            timeline_item = next(
                item
                for item in timeline.json()["data"]["list"]
                if item["id"] == diary_id
            )
            assert [item["id"] for item in timeline_item["images"]] == [image_id]

            attached_delete = await client.delete(
                f"/api/v1/uploads/images/{image_id}", headers=first_headers
            )
            assert attached_delete.status_code == 409

            async with session_factory() as db:
                stored_image = await db.get(DiaryImage, uuid.UUID(image_id))
                storage_key = stored_image.storage_key
            assert storage.path_for_key(storage_key).exists()

            diary_delete = await client.delete(
                f"/api/v1/diaries/{diary_id}", headers=first_headers
            )
            assert diary_delete.status_code == 200
            assert not storage.path_for_key(storage_key).exists()

            async with session_factory() as db:
                deleted_image = await db.get(DiaryImage, uuid.UUID(image_id))
                assert deleted_image.status == "deleted"
                assert deleted_image.deleted_at is not None

            cleanup_foreign = await client.delete(
                f"/api/v1/uploads/images/{foreign_image_id}", headers=second_headers
            )
            assert cleanup_foreign.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_storage_backend, None)
        async with session_factory() as db:
            await db.execute(
                delete(DiaryImage).where(
                    DiaryImage.user_id.in_([first_user_id, second_user_id])
                )
            )
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
