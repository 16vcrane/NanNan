import uuid

import pytest
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user


@pytest.mark.asyncio
async def test_repeated_login_reuses_stable_user_identity() -> None:
    open_id = f"phase1-test-{uuid.uuid4()}"
    async with SessionLocal() as db:
        try:
            first_user = await get_or_create_user(db, open_id)
            second_user = await get_or_create_user(db, open_id)

            assert second_user.id == first_user.id
        finally:
            await db.execute(
                delete(UserProfile).where(UserProfile.wechat_open_id == open_id)
            )
            await db.commit()
