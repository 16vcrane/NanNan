from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


async def get_or_create_user(db: AsyncSession, open_id: str) -> UserProfile:
    now = datetime.now(timezone.utc)
    statement = (
        insert(UserProfile)
        .values(wechat_open_id=open_id, last_active_at=now)
        .on_conflict_do_update(
            index_elements=[UserProfile.wechat_open_id],
            set_={"last_active_at": now},
        )
        .returning(UserProfile)
    )
    result = await db.execute(statement)
    await db.commit()
    return result.scalar_one()
