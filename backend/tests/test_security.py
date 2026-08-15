import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import security
from app.core.config import Settings


def auth_settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-that-is-at-least-32-characters",
        jwt_access_token_expire_minutes=30,
    )


def test_access_token_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    user_id = uuid.uuid4()

    token = security.create_access_token(user_id)

    assert security.decode_access_token(token) == user_id


def test_tampered_access_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    token = security.create_access_token(uuid.uuid4())
    header, payload, signature = token.split(".")
    signature = f"{'a' if signature[0] != 'a' else 'b'}{signature[1:]}"
    tampered = ".".join((header, payload, signature))

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(tampered)


@pytest.mark.asyncio
async def test_current_user_is_loaded_from_token(monkeypatch) -> None:
    monkeypatch.setattr(security, "get_settings", auth_settings)
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id)
    db = AsyncMock()
    db.get.return_value = user
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=security.create_access_token(user_id),
    )

    result = await security.get_current_user(credentials=credentials, db=db)

    assert result is user
    db.get.assert_awaited_once_with(security.UserProfile, user_id)


@pytest.mark.asyncio
async def test_current_user_requires_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await security.get_current_user(credentials=None, db=AsyncMock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "AUTH_INVALID"
