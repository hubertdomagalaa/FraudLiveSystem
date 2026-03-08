from shared.tracing import (
    otlp_traces_endpoint_from_env,
    parse_or_create_traceparent,
    trace_id_from_traceparent,
)


def test_traceparent_is_created_when_missing() -> None:
    traceparent = parse_or_create_traceparent(None)
    assert traceparent.startswith("00-")
    assert len(traceparent) == 55


def test_trace_id_extraction() -> None:
    traceparent = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    assert trace_id_from_traceparent(traceparent) == "0123456789abcdef0123456789abcdef"


def test_otlp_endpoint_prefers_traces_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://collector:4318/v1/traces")
    assert otlp_traces_endpoint_from_env() == "http://collector:4318/v1/traces"


def test_otlp_endpoint_falls_back_to_generic_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    assert otlp_traces_endpoint_from_env() == "http://collector:4318"
