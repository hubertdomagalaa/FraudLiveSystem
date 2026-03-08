from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def parse_allowed_origins(raw_origins: str) -> tuple[list[str], bool]:
    items = [item.strip() for item in raw_origins.split(',')]
    origins = [item for item in items if item]
    allow_all = origins == ['*']
    return origins, allow_all


def add_cors_middleware(app: FastAPI, raw_origins: str) -> None:
    origins, allow_all = parse_allowed_origins(raw_origins)
    allow_origins = ['*'] if allow_all else origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=not allow_all,
        allow_methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['*'],
        expose_headers=['traceparent', 'X-Trace-Id'],
    )
