from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes.transactions import ingest_transaction
from shared.schemas.transactions import TransactionIn


class FakeBroker:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, stream: str, event) -> str:
        self.published.append((stream, event.event_id))
        return "1-0"


class FakeDB:
    def __init__(self) -> None:
        self.by_idempotency: dict[str, dict] = {}
        self.by_transaction: dict[str, dict] = {}
        self.events: list[str] = []

    async def get_case_by_ingest_idempotency_key(self, idempotency_key: str):
        return self.by_idempotency.get(idempotency_key)

    async def insert_case(
        self,
        *,
        case_id: str,
        transaction_id: str,
        ingest_idempotency_key: str | None,
        source_system: str,
        ingest_event_id: str,
        initial_payload: dict,
    ) -> bool:
        if not ingest_idempotency_key:
            return False
        if ingest_idempotency_key in self.by_idempotency:
            return False
        record = {
            "case_id": case_id,
            "transaction_id": transaction_id,
            "ingest_idempotency_key": ingest_idempotency_key,
            "source_system": source_system,
            "ingest_event_id": ingest_event_id,
            "initial_payload": initial_payload,
        }
        self.by_idempotency[ingest_idempotency_key] = record
        self.by_transaction[transaction_id] = record
        return True

    async def append_case_event(self, *, event, stream_name: str, stream_message_id: str | None) -> bool:
        self.events.append(event.event_id)
        return True


class FakeAuth:
    def verify_write_access(self, request):
        return {"sub": "test-user", "scope": "fraud.write"}


class FakeRateLimiter:
    service_name = "ingestion-api"

    async def allow(self, key: str) -> bool:
        return True


def make_request(db: FakeDB, broker: FakeBroker):
    state = SimpleNamespace(db=db, broker=broker, auth=FakeAuth(), rate_limiter=FakeRateLimiter())
    app = SimpleNamespace(state=state)
    request = SimpleNamespace(app=app, headers={}, url=SimpleNamespace(path="/v1/transactions"), method="POST")
    request.client = SimpleNamespace(host="127.0.0.1")
    request.state = SimpleNamespace(trace_id="trace-test")
    return request


def make_payload(amount: str = "1200.50", merchant_risk_score: float = 0.45) -> TransactionIn:
    return TransactionIn.model_validate(
        {
            "amount": amount,
            "currency": "USD",
            "merchant_id": "merchant-1",
            "card_id": "card-1",
            "timestamp": "2026-02-16T10:00:00Z",
            "country": "US",
            "ip": "203.0.113.10",
            "device_id": "dev-001",
            "prior_chargeback_flags": False,
            "merchant_risk_score": merchant_risk_score,
            "metadata": {"new_device": True},
        }
    )


@pytest.mark.asyncio
async def test_same_idempotency_key_returns_same_transaction_without_second_publish() -> None:
    db = FakeDB()
    broker = FakeBroker()
    request = make_request(db, broker)
    payload = make_payload()

    first = await ingest_transaction(payload=payload, request=request, idempotency_key="idem-1")
    second = await ingest_transaction(payload=payload, request=request, idempotency_key="idem-1")

    assert first.transaction_id == second.transaction_id
    assert len(broker.published) == 1
    assert len(db.events) == 1


@pytest.mark.asyncio
async def test_same_idempotency_key_with_different_payload_returns_conflict() -> None:
    db = FakeDB()
    broker = FakeBroker()
    request = make_request(db, broker)

    await ingest_transaction(payload=make_payload("1200.50", merchant_risk_score=0.45), request=request, idempotency_key="idem-2")

    with pytest.raises(HTTPException) as exc:
        await ingest_transaction(payload=make_payload("1200.50", merchant_risk_score=0.88), request=request, idempotency_key="idem-2")

    assert exc.value.status_code == 409
