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


def make_auth(**overrides) -> JwtAuth:
    params = {
        "service_name": "svc",
        "enabled": True,
        "secret": "secret",
        "jwks_url": None,
        "algorithm": "HS256",
        "required_scope": "fraud.write",
        "issuer": None,
        "audience": None,
        "leeway_seconds": 30,
    }
    params.update(overrides)
    return JwtAuth(**params)


def test_jwt_auth_accepts_valid_scope() -> None:
    token = jwt.encode({"sub": "u1", "scope": "fraud.write"}, "secret", algorithm="HS256")
    auth = make_auth()
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    claims = auth.verify_write_access(request)
    assert claims["sub"] == "u1"


def test_jwt_auth_rejects_missing_bearer() -> None:
    auth = make_auth()
    request = make_request(headers={}, app_state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        auth.verify_write_access(request)
    assert exc.value.status_code == 401


def test_jwt_auth_rejects_missing_scope() -> None:
    token = jwt.encode({"sub": "u1", "scope": "fraud.read"}, "secret", algorithm="HS256")
    auth = make_auth()
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        auth.verify_write_access(request)
    assert exc.value.status_code == 403


def test_jwt_auth_rejects_invalid_issuer() -> None:
    token = jwt.encode({"sub": "u1", "scope": "fraud.write", "iss": "issuer-a"}, "secret", algorithm="HS256")
    auth = make_auth(issuer="issuer-b")
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        auth.verify_write_access(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token issuer"


def test_jwt_auth_rejects_invalid_audience() -> None:
    token = jwt.encode(
        {"sub": "u1", "scope": "fraud.write", "aud": "fraud-api-a"},
        "secret",
        algorithm="HS256",
    )
    auth = make_auth(audience="fraud-api-b")
    request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        auth.verify_write_access(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token audience"


def test_jwt_auth_supports_jwks_resolver() -> None:
    token = "header.payload.signature"
    auth = make_auth(secret=None, jwks_url="https://idp.example.com/.well-known/jwks.json", algorithm="RS256")

    class FakeSigningKey:
        key = "jwks-key"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, encoded_token: str) -> FakeSigningKey:
            assert encoded_token == token
            return FakeSigningKey()

    auth._jwks_client = FakeJwksClient()
    original_decode = jwt.decode
    decode_calls: list[dict[str, object]] = []

    def fake_decode(encoded_token: str, **kwargs):
        decode_calls.append({"token": encoded_token, **kwargs})
        return {"sub": "u1", "scope": "fraud.write"}

    jwt.decode = fake_decode
    try:
        request = make_request(headers={"Authorization": f"Bearer {token}"}, app_state=SimpleNamespace())
        claims = auth.verify_write_access(request)
    finally:
        jwt.decode = original_decode

    assert claims["sub"] == "u1"
    assert decode_calls[0]["key"] == "jwks-key"
    assert decode_calls[0]["algorithms"] == ["RS256"]


def test_jwt_auth_requires_auth_material() -> None:
    with pytest.raises(ValueError):
        make_auth(secret=None, jwks_url=None)


def test_jwt_auth_requires_asymmetric_alg_for_jwks() -> None:
    with pytest.raises(ValueError):
        make_auth(secret=None, jwks_url="https://idp.example.com/jwks", algorithm="HS256")


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
