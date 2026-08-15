import pytest

from app.core.config import Settings
from app.services import wechat_service


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeClient:
    payload = {}
    last_params = None

    def __init__(self, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def get(self, _url: str, params: dict) -> FakeResponse:
        type(self).last_params = params
        return FakeResponse(type(self).payload)


@pytest.mark.asyncio
async def test_exchange_code_returns_only_openid(monkeypatch) -> None:
    FakeClient.payload = {"openid": "openid-1", "session_key": "private-session-key"}
    monkeypatch.setattr(
        wechat_service,
        "get_settings",
        lambda: Settings(wechat_app_id="app-id", wechat_app_secret="app-secret"),
    )
    monkeypatch.setattr(wechat_service.httpx, "AsyncClient", FakeClient)

    open_id = await wechat_service.exchange_code_for_openid("temporary-code")

    assert open_id == "openid-1"
    assert FakeClient.last_params["js_code"] == "temporary-code"


@pytest.mark.asyncio
async def test_wechat_rejected_code_maps_to_auth_invalid(monkeypatch) -> None:
    FakeClient.payload = {"errcode": 40029, "errmsg": "invalid code"}
    monkeypatch.setattr(
        wechat_service,
        "get_settings",
        lambda: Settings(wechat_app_id="app-id", wechat_app_secret="app-secret"),
    )
    monkeypatch.setattr(wechat_service.httpx, "AsyncClient", FakeClient)

    with pytest.raises(wechat_service.WechatAuthError) as exc_info:
        await wechat_service.exchange_code_for_openid("invalid-code")

    assert exc_info.value.code == "AUTH_INVALID"
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_wechat_configuration_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(wechat_service, "get_settings", Settings)

    with pytest.raises(wechat_service.WechatAuthError) as exc_info:
        await wechat_service.exchange_code_for_openid("code")

    assert exc_info.value.code == "AUTH_NOT_CONFIGURED"
    assert exc_info.value.status_code == 503
