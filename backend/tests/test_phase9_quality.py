import json
import logging

import httpx
import pytest

from app.core.config import Settings
from app.core.idempotency import IdempotencyState
from app.core.logging import JsonFormatter, request_id_context
from app.core.rate_limit import RateLimitResult
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, _key: str, _seconds: int) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, **options) -> bool | None:
        if options.get("nx") and key in self.values:
            return None
        self.values[key] = value
        return True

    async def eval(self, _script: str, _count: int, key: str, token: str) -> int:
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0


@pytest.mark.asyncio
async def test_fixed_window_rate_limit(monkeypatch) -> None:
    from app.core import rate_limit

    fake = FakeRedis()
    monkeypatch.setattr(rate_limit, "redis", fake)
    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: Settings(rate_limit_requests=2, rate_limit_window_seconds=60),
    )

    assert (await rate_limit.check_rate_limit("user-1")).allowed is True
    assert (await rate_limit.check_rate_limit("user-1")).allowed is True
    blocked = await rate_limit.check_rate_limit("user-1")
    assert blocked.allowed is False
    assert blocked.remaining == 0


@pytest.mark.asyncio
async def test_idempotency_claim_can_be_replayed(monkeypatch) -> None:
    from app.core import idempotency

    fake = FakeRedis()
    monkeypatch.setattr(idempotency, "redis", fake)
    scope = idempotency.build_scope("user-1", "request-key-123")

    first = await idempotency.begin(scope)
    assert first.state is IdempotencyState.ACQUIRED
    pending = await idempotency.begin(scope)
    assert pending.state is IdempotencyState.PENDING

    result = {"diaryId": "11111111-1111-1111-1111-111111111111", "reflectionStatus": "pending"}
    await idempotency.complete(first, result)
    replay = await idempotency.begin(scope)
    assert replay.state is IdempotencyState.COMPLETED
    assert replay.result == result


@pytest.mark.asyncio
async def test_request_id_and_validation_error_shape(monkeypatch) -> None:
    from app import main

    async def allow(_identifier: str) -> RateLimitResult:
        return RateLimitResult(True, 120, 119, 60)

    monkeypatch.setattr(main, "check_rate_limit", allow)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={},
            headers={"X-Request-ID": "phase9-request"},
        )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "phase9-request"
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["data"]["fields"] == ["code"]


def test_json_logs_include_request_id() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("phase9", logging.INFO, __file__, 1, "done", (), None)
    token = request_id_context.set("request-42")
    try:
        payload = json.loads(formatter.format(record))
    finally:
        request_id_context.reset(token)

    assert payload["request_id"] == "request-42"
    assert payload["message"] == "done"
