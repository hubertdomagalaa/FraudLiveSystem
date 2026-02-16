from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import Field

from shared.schemas.base import BaseSchema


class StreamName(StrEnum):
    CASE_EVENTS = "fraud.case.events.v1"
    AGENT_CONTEXT_COMMANDS = "fraud.agent.context.cmd.v1"
    AGENT_RISK_COMMANDS = "fraud.agent.risk.cmd.v1"
    AGENT_POLICY_COMMANDS = "fraud.agent.policy.cmd.v1"
    AGENT_EXPLAIN_COMMANDS = "fraud.agent.explain.cmd.v1"
    AGENT_AGGREGATE_COMMANDS = "fraud.agent.aggregate.cmd.v1"
    HUMAN_REVIEW_COMMANDS = "fraud.human_review.cmd.v1"
    DEAD_LETTER = "fraud.dlq.v1"


class ConsumerGroup(StrEnum):
    ORCHESTRATOR = "cg.orchestrator"
    AGENT_CONTEXT = "cg.agent.context"
    AGENT_RISK = "cg.agent.risk"
    AGENT_POLICY = "cg.agent.policy"
    AGENT_EXPLAIN = "cg.agent.explain"
    AGENT_AGGREGATE = "cg.agent.aggregate"
    HUMAN_REVIEW = "cg.human.review"
    DLQ_OPS = "cg.dlq.ops"


class EventType(StrEnum):
    CASE_CREATED = "case.created"
    STEP_RUN_REQUESTED = "step.run.requested"

    AGENT_CONTEXT_COMPLETED = "agent.context.completed"
    AGENT_RISK_COMPLETED = "agent.risk.completed"
    AGENT_POLICY_COMPLETED = "agent.policy.completed"
    AGENT_EXPLAIN_COMPLETED = "agent.explain.completed"
    AGENT_AGGREGATE_COMPLETED = "agent.aggregate.completed"

    CASE_HUMAN_REVIEW_REQUIRED = "case.human_review.required"
    CASE_HUMAN_REVIEW_COMPLETED = "case.human_review.completed"
    CASE_FINALIZED = "case.finalized"

    CASE_STEP_FAILED = "case.step.failed"
    DEAD_LETTER_EVENT = "dead_letter.event"


class StepName(StrEnum):
    CONTEXT = "context"
    RISK = "risk"
    POLICY = "policy"
    EXPLAIN = "explain"
    AGGREGATE = "aggregate"
    HUMAN_REVIEW = "human_review"


class EventEnvelope(BaseSchema):
    event_id: str
    event_type: str
    case_id: str
    transaction_id: str
    occurred_at: datetime
    producer: str
    correlation_id: str
    trace_id: str | None = None
    traceparent: str | None = None
    causation_id: str | None = None
    idempotency_key: str
    attempt: int = Field(default=1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def deterministic_uuid(*parts: str) -> str:
    material = "::".join(parts)
    return str(uuid5(NAMESPACE_URL, material))


def build_event(
    *,
    event_type: str,
    case_id: str,
    transaction_id: str,
    producer: str,
    payload: dict[str, Any],
    causation_id: str | None = None,
    trace_id: str | None = None,
    traceparent: str | None = None,
    event_id: str | None = None,
    idempotency_key: str | None = None,
    attempt: int = 1,
) -> EventEnvelope:
    generated_event_id = event_id or str(uuid4())
    generated_idempotency = idempotency_key or f"{event_type}:{generated_event_id}"
    return EventEnvelope(
        event_id=generated_event_id,
        event_type=event_type,
        case_id=case_id,
        transaction_id=transaction_id,
        occurred_at=utc_now(),
        producer=producer,
        correlation_id=case_id,
        trace_id=trace_id,
        traceparent=traceparent,
        causation_id=causation_id,
        idempotency_key=generated_idempotency,
        attempt=attempt,
        payload=payload,
    )


def retry_event(event: EventEnvelope, producer: str) -> EventEnvelope:
    next_attempt = event.attempt + 1
    return EventEnvelope(
        event_id=deterministic_uuid(event.event_id, producer, str(next_attempt)),
        event_type=event.event_type,
        case_id=event.case_id,
        transaction_id=event.transaction_id,
        occurred_at=utc_now(),
        producer=producer,
        correlation_id=event.correlation_id,
        trace_id=event.trace_id,
        traceparent=event.traceparent,
        causation_id=event.event_id,
        idempotency_key=event.idempotency_key,
        attempt=next_attempt,
        payload=event.payload,
    )
