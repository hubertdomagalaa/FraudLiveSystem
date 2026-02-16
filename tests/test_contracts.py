from __future__ import annotations

from shared.events import EventType, build_event
from shared.schemas.agents import (
    AggregateAgentOutput,
    ContextAgentOutput,
    LLMExplanationOutput,
    PolicyAction,
    PolicyAgentOutput,
    RiskMLAgentOutput,
)


def test_context_completed_payload_contract() -> None:
    payload = {
        "metadata": {
            "execution_id": "e1",
            "service_name": "agent-context",
            "started_at": "2026-02-16T10:00:00Z",
            "completed_at": "2026-02-16T10:00:01Z",
            "latency_ms": 10,
            "trace_id": "trace-1",
        },
        "result": ContextAgentOutput(
            customer_segment="standard",
            device_trust="unverified",
            account_age_days=10,
            signals=["NEW_DEVICE"],
        ).model_dump(mode="json"),
    }
    event = build_event(
        event_type=EventType.AGENT_CONTEXT_COMPLETED,
        case_id="00000000-0000-0000-0000-000000000001",
        transaction_id="tx-1",
        producer="agent-context",
        payload=payload,
    )
    assert event.event_type == EventType.AGENT_CONTEXT_COMPLETED


def test_policy_output_contract() -> None:
    policy = PolicyAgentOutput(
        ruleset_version="v1",
        violations=["RISK_SCORE_HIGH"],
        action=PolicyAction.REVIEW,
    )
    assert policy.action.value == "REVIEW"


def test_aggregate_output_contract() -> None:
    _ = RiskMLAgentOutput(
        risk_score=0.7,
        model_version="m1",
        feature_version="f1",
        features_used=["amount_scaled"],
    )
    _ = LLMExplanationOutput(
        summary="summary",
        rationale="rationale",
        confidence=0.7,
        provider="template",
        model="stub",
        prompt_version="v1",
    )
    aggregate = AggregateAgentOutput(
        recommendation="REVIEW",
        requires_human_review=True,
        reason_codes=["HUMAN_REVIEW_REQUIRED"],
        confidence=0.7,
        summary="Aggregated recommendation",
    )
    assert aggregate.requires_human_review is True
