from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from shared.database import PlatformDatabase
from shared.events import EventEnvelope, EventType, deterministic_uuid
from shared.rate_limit import enforce_write_rate_limit
from shared.security import require_write_access
from shared.tracing import annotate_current_span

router = APIRouter(tags=["dlq"])


class DlqReplayRequest(BaseModel):
    reset_attempt: bool = True


class DlqReplayResponse(BaseModel):
    replay_event_id: str
    source_stream: str
    stream_message_id: str
    attempt: int


def _db(request: Request) -> PlatformDatabase:
    return request.app.state.db


@router.get("/dlq/events")
async def list_dlq_events(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    await require_write_access(request)
    annotate_current_span(**{"fraud.dlq.limit": limit})
    return await _db(request).list_dlq_events(limit=limit)


@router.post("/dlq/replay/{event_id}", response_model=DlqReplayResponse, status_code=status.HTTP_201_CREATED)
async def replay_dlq_event(event_id: str, body: DlqReplayRequest, request: Request):
    await require_write_access(request)
    await enforce_write_rate_limit(request)

    db = _db(request)
    broker = request.app.state.broker
    row = await db.get_case_event(event_id)
    if not row:
        raise HTTPException(status_code=404, detail="DLQ event not found")
    if row.get("event_type") != EventType.DEAD_LETTER_EVENT:
        raise HTTPException(status_code=400, detail="Event is not a DLQ event")

    payload = dict(row.get("payload") or {})
    failed_event_payload: dict[str, Any] | None = payload.get("failed_event")
    source_stream: str | None = payload.get("source_stream")
    if not failed_event_payload or not source_stream:
        raise HTTPException(status_code=400, detail="DLQ payload missing failed_event/source_stream")

    failed_event = EventEnvelope.model_validate(failed_event_payload)
    replay_event = failed_event.model_copy(deep=True)
    replay_event.event_id = deterministic_uuid(failed_event.event_id, "dlq-replay", event_id)
    replay_event.producer = "dlq-ops-api"
    replay_event.causation_id = event_id
    if body.reset_attempt:
        replay_event.attempt = 1

    stream_message_id = await broker.publish(source_stream, replay_event)
    annotate_current_span(
        **{
            "fraud.case_id": replay_event.case_id,
            "fraud.event_id": replay_event.event_id,
            "fraud.source_event_id": event_id,
            "fraud.step": replay_event.payload.get("step") if isinstance(replay_event.payload, dict) else None,
            "fraud.dlq.source_stream": source_stream,
        }
    )
    await db.append_case_event(
        event=replay_event,
        stream_name=source_stream,
        stream_message_id=stream_message_id,
    )

    return DlqReplayResponse(
        replay_event_id=replay_event.event_id,
        source_stream=source_stream,
        stream_message_id=stream_message_id,
        attempt=replay_event.attempt,
    )
