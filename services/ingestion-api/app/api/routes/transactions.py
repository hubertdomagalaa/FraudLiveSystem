import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, status

from shared.database import PlatformDatabase
from shared.events import EventType, StreamName, build_event, deterministic_uuid
from shared.rate_limit import enforce_write_rate_limit
from shared.security import require_write_access
from shared.schemas.transactions import TransactionIn, TransactionStored
from shared.tracing import request_trace_context

router = APIRouter(tags=["transactions"])
logger = logging.getLogger("ingestion-api")


def _db(request: Request) -> PlatformDatabase:
    return request.app.state.db


def _payload_conflicts_with_existing(payload: TransactionIn, existing: dict) -> bool:
    incoming = payload.model_dump(mode="json")
    existing_payload = dict(existing.get("initial_payload", {}))
    comparable_fields = ("amount", "currency", "merchant_id", "card_id", "timestamp", "metadata")
    for field in comparable_fields:
        if incoming.get(field) != existing_payload.get(field):
            return True
    return False


@router.post("/transactions", response_model=TransactionStored, status_code=status.HTTP_201_CREATED)
async def ingest_transaction(
    payload: TransactionIn,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    db = _db(request)
    broker = request.app.state.broker
    await require_write_access(request)
    await enforce_write_rate_limit(request)
    trace_id, traceparent = request_trace_context(request)

    existing = await db.get_case_by_ingest_idempotency_key(idempotency_key)
    if existing:
        if _payload_conflicts_with_existing(payload, existing):
            raise HTTPException(status_code=409, detail="Idempotency key already used with different payload")
        return TransactionStored.model_validate(existing["initial_payload"])

    case_id = deterministic_uuid("case", idempotency_key)
    transaction_id = deterministic_uuid("tx", idempotency_key)
    stored = TransactionStored(
        transaction_id=transaction_id,
        received_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )

    event = build_event(
        event_type=EventType.CASE_CREATED,
        case_id=case_id,
        transaction_id=transaction_id,
        producer="ingestion-api",
        trace_id=trace_id,
        traceparent=traceparent,
        event_id=deterministic_uuid(case_id, EventType.CASE_CREATED, idempotency_key),
        payload={"transaction": stored.model_dump(mode="json")},
        idempotency_key=f"case.created:{idempotency_key}",
    )

    inserted = await db.insert_case(
        case_id=case_id,
        transaction_id=transaction_id,
        ingest_idempotency_key=idempotency_key,
        source_system="ingestion-api",
        ingest_event_id=event.event_id,
        initial_payload=stored.model_dump(mode="json"),
    )
    if not inserted:
        existing = await db.get_case_by_ingest_idempotency_key(idempotency_key)
        if existing:
            if _payload_conflicts_with_existing(payload, existing):
                raise HTTPException(status_code=409, detail="Idempotency key already used with different payload")
            return TransactionStored.model_validate(existing["initial_payload"])
        raise HTTPException(status_code=409, detail="Transaction already exists")

    stream_message_id = await broker.publish(StreamName.CASE_EVENTS, event)
    await db.append_case_event(
        event=event,
        stream_name=StreamName.CASE_EVENTS,
        stream_message_id=stream_message_id,
    )

    logger.info(
        "transaction_ingested",
        extra={
            "transaction_id": transaction_id,
            "case_id": case_id,
            "event_id": event.event_id,
        },
    )
    return stored


@router.get("/transactions/{transaction_id}", response_model=TransactionStored)
async def get_transaction(transaction_id: str, request: Request):
    db = _db(request)
    case = await db.get_case_by_transaction(transaction_id)
    if not case:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionStored.model_validate(case["initial_payload"])
