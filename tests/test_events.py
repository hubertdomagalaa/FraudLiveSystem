from shared.events import EventType, build_event, deterministic_uuid, retry_event


def test_deterministic_uuid_is_stable() -> None:
    left = deterministic_uuid("case-1", "context", "cause-1")
    right = deterministic_uuid("case-1", "context", "cause-1")
    assert left == right


def test_retry_event_preserves_idempotency_and_increments_attempt() -> None:
    original = build_event(
        event_type=EventType.CASE_CREATED,
        case_id="case-1",
        transaction_id="tx-1",
        producer="ingestion-api",
        payload={"k": "v"},
        idempotency_key="case.created:tx-1",
        trace_id="trace-1",
        traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
    )
    retried = retry_event(original, producer="decision-orchestrator")

    assert retried.attempt == original.attempt + 1
    assert retried.idempotency_key == original.idempotency_key
    assert retried.causation_id == original.event_id
    assert retried.event_id != original.event_id
    assert retried.trace_id == original.trace_id
    assert retried.traceparent == original.traceparent
