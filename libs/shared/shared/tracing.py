from __future__ import annotations

import os
import re
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


TRACE_ID_CTX: ContextVar[str | None] = ContextVar("trace_id", default=None)
TRACEPARENT_CTX: ContextVar[str | None] = ContextVar("traceparent", default=None)
TRACEPARENT_RE = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-0[0-3]$")
_TRACING_INITIALIZED = False


def _random_hex(length: int) -> str:
    value = uuid4().hex + uuid4().hex
    return value[:length]


def generate_traceparent() -> str:
    return f"00-{_random_hex(32)}-{_random_hex(16)}-01"


def parse_or_create_traceparent(incoming: str | None) -> str:
    if incoming and TRACEPARENT_RE.match(incoming):
        return incoming
    return generate_traceparent()


def trace_id_from_traceparent(traceparent: str) -> str:
    return traceparent.split("-")[1]


def configure_tracing(service_name: str, enabled: bool) -> None:
    global _TRACING_INITIALIZED
    if not enabled or _TRACING_INITIALIZED:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _TRACING_INITIALIZED = True


def build_tracing_middleware(service_name: str):
    tracer = trace.get_tracer(service_name)

    async def middleware(request: Request, call_next):
        raw_traceparent = request.headers.get("traceparent")
        traceparent = parse_or_create_traceparent(raw_traceparent)
        trace_id = trace_id_from_traceparent(traceparent)

        token_trace = TRACE_ID_CTX.set(trace_id)
        token_parent = TRACEPARENT_CTX.set(traceparent)
        request.state.trace_id = trace_id
        request.state.traceparent = traceparent

        try:
            with tracer.start_as_current_span(f"http {request.method} {request.url.path}") as span:
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.target", request.url.path)
                span.set_attribute("trace_id", trace_id)
                response = await call_next(request)
        finally:
            TRACE_ID_CTX.reset(token_trace)
            TRACEPARENT_CTX.reset(token_parent)

        response.headers["traceparent"] = traceparent
        response.headers["X-Trace-Id"] = trace_id
        return response

    return middleware


def current_trace_id() -> str | None:
    return TRACE_ID_CTX.get()


def current_traceparent() -> str | None:
    return TRACEPARENT_CTX.get()


def request_trace_context(request: Request) -> tuple[str, str]:
    traceparent = parse_or_create_traceparent(request.headers.get("traceparent"))
    trace_id = getattr(request.state, "trace_id", None) or trace_id_from_traceparent(traceparent)
    return trace_id, traceparent


def tracing_enabled_from_env(default: bool) -> bool:
    raw = os.getenv("TRACING_ENABLED")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
