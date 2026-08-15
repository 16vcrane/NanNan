import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api import auth as auth_api
from app.schemas.auth import WechatLoginRequest


def make_user():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        created_at=now,
        last_active_at=now,
        ai_reflection_enabled=True,
        anniversary_reminder_enabled=False,
        third_person_unlocked=False,
        wechat_open_id="must-not-be-returned",
    )


@pytest.mark.asyncio
async def test_login_returns_token_and_public_user_only(monkeypatch) -> None:
    user = make_user()
    monkeypatch.setattr(
        auth_api,
        "exchange_code_for_openid",
        AsyncMock(return_value="openid-1"),
    )
    get_user = AsyncMock(return_value=user)
    monkeypatch.setattr(auth_api, "get_or_create_user", get_user)
    monkeypatch.setattr(auth_api, "create_access_token", lambda _user_id: "access-token")

    response = await auth_api.login(WechatLoginRequest(code="wx-code"), AsyncMock())
    payload = response.model_dump(by_alias=True, mode="json")

    assert payload["data"]["accessToken"] == "access-token"
    assert payload["data"]["user"]["id"] == str(user.id)
    assert "wechatOpenId" not in payload["data"]["user"]
    get_user.assert_awaited_once()
