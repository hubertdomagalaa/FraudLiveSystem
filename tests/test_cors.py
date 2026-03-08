from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from shared.cors import add_cors_middleware, parse_allowed_origins


def test_parse_allowed_origins_list() -> None:
    origins, allow_all = parse_allowed_origins(' http://localhost:5173, http://127.0.0.1:5173 ,, ')
    assert origins == ['http://localhost:5173', 'http://127.0.0.1:5173']
    assert allow_all is False


def test_parse_allowed_origins_wildcard() -> None:
    origins, allow_all = parse_allowed_origins('*')
    assert origins == ['*']
    assert allow_all is True


def test_cors_middleware_allows_configured_origin() -> None:
    app = FastAPI()
    add_cors_middleware(app, 'http://localhost:5173,http://127.0.0.1:5173')

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    client = TestClient(app)
    preflight = client.options(
        '/health',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
        },
    )
    response = client.get('/health', headers={'Origin': 'http://localhost:5173'})

    assert preflight.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert response.headers['access-control-expose-headers'] == 'traceparent, X-Trace-Id'


def test_cors_middleware_keeps_wildcard_explicit() -> None:
    app = FastAPI()
    add_cors_middleware(app, '*')

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    client = TestClient(app)
    response = client.options(
        '/health',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
        },
    )

    assert response.headers['access-control-allow-origin'] == '*'
