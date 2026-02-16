from shared.tracing import parse_or_create_traceparent, trace_id_from_traceparent


def test_traceparent_is_created_when_missing() -> None:
    traceparent = parse_or_create_traceparent(None)
    assert traceparent.startswith("00-")
    assert len(traceparent) == 55


def test_trace_id_extraction() -> None:
    traceparent = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    assert trace_id_from_traceparent(traceparent) == "0123456789abcdef0123456789abcdef"
