import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "path"],
)
STREAM_GROUP_LAG = Gauge(
    "stream_group_lag",
    "Redis stream consumer group lag",
    ["service", "stream", "consumer_group"],
)
STREAM_RETRY_COUNT = Counter(
    "stream_retry_total",
    "Total retries scheduled by stream consumers",
    ["service", "stream", "event_type"],
)
STREAM_DLQ_COUNT = Counter(
    "stream_dlq_total",
    "Total events sent to dead-letter stream",
    ["service", "stream", "event_type"],
)
EVENT_PROCESSED_COUNT = Counter(
    "stream_events_processed_total",
    "Total successfully processed stream events",
    ["service", "stream", "event_type"],
)
AGENT_LATENCY = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution latency in seconds",
    ["service", "agent"],
)
AUTH_REJECTED_COUNT = Counter(
    "auth_rejected_total",
    "Total rejected authenticated write requests",
    ["service", "path", "reason"],
)
RATE_LIMIT_REJECTED_COUNT = Counter(
    "rate_limit_rejected_total",
    "Total rate-limited requests",
    ["service", "path", "method"],
)


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def build_metrics_middleware(service_name: str):
    async def middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency = time.perf_counter() - start
        REQUEST_COUNT.labels(
            service=service_name,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            service=service_name,
            method=request.method,
            path=request.url.path,
        ).observe(latency)
        return response

    return middleware


def set_stream_lag(service: str, stream: str, consumer_group: str, lag: int) -> None:
    STREAM_GROUP_LAG.labels(service=service, stream=stream, consumer_group=consumer_group).set(max(lag, 0))


def inc_stream_retry(service: str, stream: str, event_type: str) -> None:
    STREAM_RETRY_COUNT.labels(service=service, stream=stream, event_type=event_type).inc()


def inc_stream_dlq(service: str, stream: str, event_type: str) -> None:
    STREAM_DLQ_COUNT.labels(service=service, stream=stream, event_type=event_type).inc()


def inc_event_processed(service: str, stream: str, event_type: str) -> None:
    EVENT_PROCESSED_COUNT.labels(service=service, stream=stream, event_type=event_type).inc()


def observe_agent_latency(service: str, agent: str, latency_seconds: float) -> None:
    AGENT_LATENCY.labels(service=service, agent=agent).observe(max(latency_seconds, 0.0))


def inc_auth_rejected(service: str, path: str, reason: str) -> None:
    AUTH_REJECTED_COUNT.labels(service=service, path=path, reason=reason).inc()


def inc_rate_limited(service: str, path: str, method: str) -> None:
    RATE_LIMIT_REJECTED_COUNT.labels(service=service, path=path, method=method).inc()
