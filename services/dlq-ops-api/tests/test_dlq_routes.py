from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.routes.dlq import DlqReplayRequest, replay_dlq_event
from shared.events import EventType


class FakeAuth:
    def verify_write_access(self, request):
        return {"sub": "ops-user", "scope": "fraud.write"}


class FakeRateLimiter:
    service_name = "dlq-ops-api"

    async def allow(self, key: str) -> bool:
        return True


class FakeBroker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def publish(self, stream: str, event) -> str:
        self.calls.append((stream, event.event_id))
        return "9-0"


class FakeDB:
    async def list_dlq_events(self, limit: int = 100):
        return []

    async def get_case_event(self, event_id: str):
        return {
            "event_id": event_id,
            "event_type": EventType.DEAD_LETTER_EVENT,
            "payload": {
                "source_stream": "fraud.case.events.v1",
                "failed_event": {
                    "event_id": "11111111-1111-1111-1111-111111111111",
                    "event_type": EventType.CASE_CREATED,
                    "case_id": "00000000-0000-0000-0000-000000000001",
                    "transaction_id": "tx-1",
                    "occurred_at": "2026-02-16T10:00:00Z",
                    "producer": "ingestion-api",
                    "correlation_id": "00000000-0000-0000-0000-000000000001",
                    "trace_id": "trace-1",
                    "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
                    "causation_id": None,
                    "idempotency_key": "case.created:idem-1",
                    "attempt": 3,
                    "payload": {"transaction": {"transaction_id": "tx-1"}},
                },
            },
        }

    async def append_case_event(self, *, event, stream_name: str, stream_message_id: str | None):
        return True


def build_request() -> SimpleNamespace:
    state = SimpleNamespace(
        db=FakeDB(),
        broker=FakeBroker(),
        auth=FakeAuth(),
        rate_limiter=FakeRateLimiter(),
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=state),
        headers={},
        url=SimpleNamespace(path="/v1/dlq/replay/event-1"),
        method="POST",
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(),
    )
    return request


@pytest.mark.asyncio
async def test_replay_dlq_event_resets_attempt_and_publishes() -> None:
    request = build_request()
    response = await replay_dlq_event("event-1", DlqReplayRequest(reset_attempt=True), request)

    assert response.source_stream == "fraud.case.events.v1"
    assert response.attempt == 1
    assert request.app.state.broker.calls
