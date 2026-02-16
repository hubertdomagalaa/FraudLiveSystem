from __future__ import annotations

from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException

from shared.rate_limit import InMemoryRateLimiter, enforce_write_rate_limit
from shared.security import JwtAuth


def make_request(*, headers: dict[str, str], app_state) -> SimpleNamespace:
    request = SimpleNamespace()
    request.headers = headers
    request.url = SimpleNamespace(path="/v1/transactions")
    request.method = "POST"
    request.client = SimpleNamespace(host="127.0.0.1")
    request.app = SimpleNamespace(state=app_state)
    request.state = SimpleNamespace()
    return request


def test_jwt_auth_accepts_valid_scope() -> None:
    token = jwt.encode({"sub": "u1", "scope": "fraud.write"}, "secret", algorithm="HS256")
    auth = JwtAuth(
        service_name="svc",
        enabled=True,
        secret="secret",
        algorithm="HS256",
        required_scope="fraud.write",
        issuer=None,
        audience=None,
    )
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    claims = auth.verify_write_access(request)
    assert claims["sub"] == "u1"


def test_jwt_auth_rejects_missing_scope() -> None:
    token = jwt.encode({"sub": "u1", "scope": "fraud.read"}, "secret", algorithm="HS256")
    auth = JwtAuth(
        service_name="svc",
        enabled=True,
        secret="secret",
        algorithm="HS256",
        required_scope="fraud.write",
        issuer=None,
        audience=None,
    )
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        auth.verify_write_access(request)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(service_name="svc", enabled=True, limit=1, window_seconds=60)
    request = make_request(
        headers={},
        app_state=SimpleNamespace(rate_limiter=limiter),
    )
    await enforce_write_rate_limit(request)
    with pytest.raises(HTTPException) as exc:
        await enforce_write_rate_limit(request)
    assert exc.value.status_code == 429
