import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.models.user import UserProfile
from app.services.auth_service import get_or_create_user


@pytest.mark.asyncio
async def test_repeated_login_reuses_stable_user_identity() -> None:
    open_id = f"phase1-test-{uuid.uuid4()}"
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            try:
                first_user = await get_or_create_user(db, open_id)
                second_user = await get_or_create_user(db, open_id)

                assert second_user.id == first_user.id
            finally:
                await db.execute(
                    delete(UserProfile).where(UserProfile.wechat_open_id == open_id)
                )
                await db.commit()
    finally:
        await engine.dispose()
