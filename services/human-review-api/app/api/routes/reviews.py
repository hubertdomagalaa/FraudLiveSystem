from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from shared.database import PlatformDatabase
from shared.events import EventType, StreamName, build_event, deterministic_uuid
from shared.rate_limit import enforce_write_rate_limit
from shared.security import require_write_access
from shared.schemas.reviews import ReviewDecisionIn, ReviewDecisionRecord
from shared.tracing import request_trace_context

router = APIRouter(tags=["reviews"])


def _db(request: Request) -> PlatformDatabase:
    return request.app.state.db


@router.get("/cases/{case_id}/actions")
async def get_case_actions(case_id: str, request: Request):
    case = await _db(request).get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _db(request).list_human_review_actions(case_id)


@router.post("/cases/{case_id}/decision", response_model=ReviewDecisionRecord, status_code=status.HTTP_201_CREATED)
async def add_decision(case_id: str, payload: ReviewDecisionIn, request: Request):
    await require_write_access(request)
    await enforce_write_rate_limit(request)
    db = _db(request)
    broker = request.app.state.broker
    trace_id, traceparent = request_trace_context(request)

    case = await db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    review_decision_id = deterministic_uuid(case_id, "human-review-decision", payload.reviewer_id, payload.outcome.value)

    completed_event = build_event(
        event_type=EventType.CASE_HUMAN_REVIEW_COMPLETED,
        case_id=case_id,
        transaction_id=case["transaction_id"],
        producer="human-review-api",
        trace_id=trace_id,
        traceparent=traceparent,
        event_id=deterministic_uuid(case_id, EventType.CASE_HUMAN_REVIEW_COMPLETED, review_decision_id),
        idempotency_key=f"{case_id}:human-review:{review_decision_id}",
        payload={
            "review_decision_id": review_decision_id,
            "reviewer_id": payload.reviewer_id,
            "action": payload.outcome.value,
            "comment": payload.comment,
            "labels": payload.labels,
        },
    )

    await db.append_human_review_action(
        review_action_id=review_decision_id,
        case_id=case_id,
        reviewer_id=payload.reviewer_id,
        action=payload.outcome.value,
        reason_code=",".join(payload.labels) if payload.labels else None,
        notes=payload.comment,
        source_event_id=completed_event.event_id,
    )
    await db.append_decision_record(
        decision_id=deterministic_uuid(case_id, "human-review-record", review_decision_id),
        case_id=case_id,
        decision_kind="HUMAN_REVIEW",
        decision=payload.outcome.value,
        confidence=None,
        reason_summary="Human reviewer action",
        reason_details={
            "reviewer_id": payload.reviewer_id,
            "labels": payload.labels,
            "comment": payload.comment,
        },
        decided_by="human-review-api",
        source_event_id=completed_event.event_id,
    )

    message_id = await broker.publish(StreamName.CASE_EVENTS, completed_event)
    await db.append_case_event(
        event=completed_event,
        stream_name=StreamName.CASE_EVENTS,
        stream_message_id=message_id,
    )

    return ReviewDecisionRecord(
        review_decision_id=review_decision_id,
        decided_at=datetime.now(timezone.utc),
        reviewer_id=payload.reviewer_id,
        outcome=payload.outcome,
        comment=payload.comment,
        labels=payload.labels,
    )
