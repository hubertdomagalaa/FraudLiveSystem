from __future__ import annotations

import importlib
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.events import ConsumerGroup, EventEnvelope, EventType, StreamName
from shared.schemas.transactions import TransactionIn
from shared.worker import StreamWorker


REPO_ROOT = Path(__file__).resolve().parents[1]


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def load_service_symbol(service_relative_path: str, module_name: str, symbol_name: str):
    service_path = str((REPO_ROOT / service_relative_path).resolve())
    purge_app_modules()
    sys.path.insert(0, service_path)
    try:
        module = importlib.import_module(module_name)
        return getattr(module, symbol_name)
    finally:
        sys.path.pop(0)


class FakeBroker:
    def __init__(self) -> None:
        self.counter = 0
        self.queue: deque[tuple[str, str, EventEnvelope]] = deque()

    async def publish(self, stream: str, event: EventEnvelope) -> str:
        self.counter += 1
        message_id = f"{self.counter}-0"
        self.queue.append((stream, message_id, event))
        return message_id

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        return None


class FakeDB:
    def __init__(self) -> None:
        self.cases_by_case_id: dict[str, dict] = {}
        self.cases_by_transaction_id: dict[str, dict] = {}
        self.cases_by_ingest_key: dict[str, dict] = {}
        self.case_events: list[dict] = []
        self.case_events_by_id: dict[str, dict] = {}
        self.agent_runs_by_case: dict[str, list[dict]] = {}
        self.decisions_by_case: dict[str, list[dict]] = {}
        self.review_actions_by_case: dict[str, list[dict]] = {}
        self.consumer_processed: set[tuple[str, str]] = set()

    async def get_case_by_ingest_idempotency_key(self, idempotency_key: str):
        return self.cases_by_ingest_key.get(idempotency_key)

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
        if case_id in self.cases_by_case_id:
            return False
        record = {
            "case_id": case_id,
            "transaction_id": transaction_id,
            "ingest_idempotency_key": ingest_idempotency_key,
            "source_system": source_system,
            "ingest_event_id": ingest_event_id,
            "initial_payload": initial_payload,
        }
        self.cases_by_case_id[case_id] = record
        self.cases_by_transaction_id[transaction_id] = record
        if ingest_idempotency_key:
            self.cases_by_ingest_key[ingest_idempotency_key] = record
        return True

    async def get_case_by_transaction(self, transaction_id: str):
        return self.cases_by_transaction_id.get(transaction_id)

    async def get_case(self, case_id: str):
        return self.cases_by_case_id.get(case_id)

    async def append_case_event(self, *, event: EventEnvelope, stream_name: str, stream_message_id: str | None):
        if event.event_id in self.case_events_by_id:
            return False
        row = {
            "event_id": event.event_id,
            "case_id": event.case_id,
            "transaction_id": event.transaction_id,
            "event_type": event.event_type,
            "producer_service": event.producer,
            "stream_name": stream_name,
            "stream_message_id": stream_message_id,
            "occurred_at": event.occurred_at,
            "recorded_at": event.occurred_at,
            "correlation_id": event.correlation_id,
            "trace_id": event.trace_id,
            "traceparent": event.traceparent,
            "causation_id": event.causation_id,
            "idempotency_key": event.idempotency_key,
            "attempt": event.attempt,
            "payload": event.payload,
        }
        self.case_events.append(row)
        self.case_events_by_id[event.event_id] = row
        return True

    async def get_latest_event_payload(self, *, case_id: str, event_type: str):
        for row in reversed(self.case_events):
            if row["case_id"] == case_id and row["event_type"] == event_type:
                return dict(row["payload"])
        return None

    async def append_agent_run(self, **kwargs):
        self.agent_runs_by_case.setdefault(kwargs["case_id"], []).append(kwargs)
        return True

    async def append_decision_record(self, **kwargs):
        self.decisions_by_case.setdefault(kwargs["case_id"], []).append(kwargs)
        return True

    async def append_human_review_action(self, **kwargs):
        self.review_actions_by_case.setdefault(kwargs["case_id"], []).append(kwargs)
        return True

    async def list_decisions(self, case_id: str):
        return list(self.decisions_by_case.get(case_id, []))

    async def list_human_review_actions(self, case_id: str):
        return list(self.review_actions_by_case.get(case_id, []))

    async def list_agent_runs(self, case_id: str):
        return list(self.agent_runs_by_case.get(case_id, []))

    async def list_case_events(self, case_id: str):
        return [row for row in self.case_events if row["case_id"] == case_id]

    async def get_case_event(self, event_id: str):
        return self.case_events_by_id.get(event_id)

    async def list_dlq_events(self, limit: int = 100):
        events = [row for row in self.case_events if row["event_type"] == EventType.DEAD_LETTER_EVENT]
        return list(reversed(events))[:limit]

    async def mark_consumer_processed(
        self,
        *,
        consumer_group: str,
        stream_name: str,
        event_id: str,
        idempotency_key: str,
        processing_result: str,
    ) -> bool:
        key = (consumer_group, event_id)
        if key in self.consumer_processed:
            return False
        self.consumer_processed.add(key)
        return True

    async def is_consumer_processed(self, *, consumer_group: str, event_id: str) -> bool:
        return (consumer_group, event_id) in self.consumer_processed


class FakeAuth:
    def verify_write_access(self, request):
        return {"sub": "test-user", "scope": "fraud.write"}


class FakeRateLimiter:
    service_name = "test"

    async def allow(self, key: str) -> bool:
        return True


def make_request(db: FakeDB, broker: FakeBroker, path: str, method: str = "POST"):
    state = SimpleNamespace(db=db, broker=broker, auth=FakeAuth(), rate_limiter=FakeRateLimiter())
    app = SimpleNamespace(state=state)
    request = SimpleNamespace(
        app=app,
        headers={},
        url=SimpleNamespace(path=path),
        method=method,
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(trace_id="trace-test", traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"),
    )
    return request


def make_transaction_payload(*, amount: str, metadata: dict) -> TransactionIn:
    return TransactionIn.model_validate(
        {
            "amount": amount,
            "currency": "USD",
            "merchant_id": "merchant-1",
            "card_id": "card-1",
            "timestamp": "2026-02-16T10:00:00Z",
            "metadata": metadata,
        }
    )


def build_harness():
    ingest_transaction = load_service_symbol(
        "services/ingestion-api",
        "app.api.routes.transactions",
        "ingest_transaction",
    )
    add_decision = load_service_symbol(
        "services/human-review-api",
        "app.api.routes.reviews",
        "add_decision",
    )
    replay_dlq_event = load_service_symbol(
        "services/dlq-ops-api",
        "app.api.routes.dlq",
        "replay_dlq_event",
    )
    DlqReplayRequest = load_service_symbol(
        "services/dlq-ops-api",
        "app.api.routes.dlq",
        "DlqReplayRequest",
    )
    ReviewDecisionIn = load_service_symbol(
        "services/human-review-api",
        "app.api.routes.reviews",
        "ReviewDecisionIn",
    )

    OrchestratorSettings = load_service_symbol(
        "services/decision-orchestrator",
        "app.config",
        "OrchestratorSettings",
    )
    OrchestrationWorker = load_service_symbol(
        "services/decision-orchestrator",
        "app.orchestration.worker",
        "OrchestrationWorker",
    )
    ContextSettings = load_service_symbol("services/agent-context", "app.config", "ContextSettings")
    ContextStreamWorker = load_service_symbol(
        "services/agent-context",
        "app.stream_worker",
        "ContextStreamWorker",
    )
    RiskMLSettings = load_service_symbol("services/agent-risk-ml", "app.config", "RiskMLSettings")
    RiskStreamWorker = load_service_symbol("services/agent-risk-ml", "app.stream_worker", "RiskStreamWorker")
    PolicySettings = load_service_symbol("services/agent-policy", "app.config", "PolicySettings")
    PolicyStreamWorker = load_service_symbol("services/agent-policy", "app.stream_worker", "PolicyStreamWorker")
    LLMExplainerSettings = load_service_symbol(
        "services/agent-llm-explainer",
        "app.config",
        "LLMExplainerSettings",
    )
    ExplainStreamWorker = load_service_symbol(
        "services/agent-llm-explainer",
        "app.stream_worker",
        "ExplainStreamWorker",
    )
    AggregateSettings = load_service_symbol("services/agent-aggregate", "app.config", "AggregateSettings")
    AggregateStreamWorker = load_service_symbol(
        "services/agent-aggregate",
        "app.stream_worker",
        "AggregateStreamWorker",
    )
    HumanReviewSettings = load_service_symbol(
        "services/human-review-api",
        "app.config",
        "HumanReviewSettings",
    )
    HumanReviewStreamWorker = load_service_symbol(
        "services/human-review-api",
        "app.stream_worker",
        "HumanReviewStreamWorker",
    )
    DlqOpsSettings = load_service_symbol("services/dlq-ops-api", "app.config", "DlqOpsSettings")
    DlqOpsStreamWorker = load_service_symbol(
        "services/dlq-ops-api",
        "app.stream_worker",
        "DlqOpsStreamWorker",
    )

    db = FakeDB()
    broker = FakeBroker()
    return {
        "db": db,
        "broker": broker,
        "ingest_transaction": ingest_transaction,
        "add_decision": add_decision,
        "replay_dlq_event": replay_dlq_event,
        "DlqReplayRequest": DlqReplayRequest,
        "ReviewDecisionIn": ReviewDecisionIn,
        "orchestrator": OrchestrationWorker(OrchestratorSettings(), db, broker),
        "context": ContextStreamWorker(ContextSettings(), db, broker),
        "risk": RiskStreamWorker(RiskMLSettings(), db, broker),
        "policy": PolicyStreamWorker(PolicySettings(), db, broker),
        "explain": ExplainStreamWorker(LLMExplainerSettings(), db, broker),
        "aggregate": AggregateStreamWorker(AggregateSettings(), db, broker),
        "human_review": HumanReviewStreamWorker(HumanReviewSettings(), db, broker),
        "dlq_ops": DlqOpsStreamWorker(DlqOpsSettings(), db, broker),
    }


async def drain_events(harness: dict, *, fail_context: bool = False, max_retry_attempts: int = 2) -> None:
    class FailingContextHandler:
        async def __call__(self, event: EventEnvelope, message_id: str) -> None:
            raise RuntimeError("context unavailable")

    failing_worker = StreamWorker(
        service_name="agent-context",
        stream_name=StreamName.AGENT_CONTEXT_COMMANDS,
        consumer_group=ConsumerGroup.AGENT_CONTEXT,
        consumer_name="agent-context-failure",
        broker=harness["broker"],
        db=harness["db"],
        handler=FailingContextHandler(),
        block_ms=10,
        read_count=1,
        claim_idle_ms=10,
        max_retry_attempts=max_retry_attempts,
    )

    while harness["broker"].queue:
        stream, message_id, event = harness["broker"].queue.popleft()
        if stream == StreamName.CASE_EVENTS:
            await harness["orchestrator"]._handle_event(event, message_id)
        elif stream == StreamName.AGENT_CONTEXT_COMMANDS:
            if fail_context:
                record = SimpleNamespace(message_id=message_id, event=event)
                await failing_worker._process_record(record)
            else:
                await harness["context"]._handle(event, message_id)
        elif stream == StreamName.AGENT_RISK_COMMANDS:
            await harness["risk"]._handle(event, message_id)
        elif stream == StreamName.AGENT_POLICY_COMMANDS:
            await harness["policy"]._handle(event, message_id)
        elif stream == StreamName.AGENT_EXPLAIN_COMMANDS:
            await harness["explain"]._handle(event, message_id)
        elif stream == StreamName.AGENT_AGGREGATE_COMMANDS:
            await harness["aggregate"]._handle(event, message_id)
        elif stream == StreamName.HUMAN_REVIEW_COMMANDS:
            await harness["human_review"]._handle(event, message_id)
        elif stream == StreamName.DEAD_LETTER:
            await harness["dlq_ops"]._handle(event, message_id)
        else:
            raise AssertionError(f"Unhandled stream {stream}")


@pytest.mark.asyncio
async def test_pipeline_allow_path_finalizes_without_human_review() -> None:
    harness = build_harness()
    request = make_request(harness["db"], harness["broker"], "/v1/transactions")
    payload = make_transaction_payload(amount="100.00", metadata={"device_trust": "trusted", "account_age_days": 730})

    stored = await harness["ingest_transaction"](payload=payload, request=request, idempotency_key="allow-case")
    await drain_events(harness)

    case = await harness["db"].get_case_by_transaction(stored.transaction_id)
    decisions = await harness["db"].list_decisions(case["case_id"])
    assert [entry["decision_kind"] for entry in decisions] == ["SYSTEM_RECOMMENDATION", "FINAL"]
    assert decisions[-1]["decision"] == "ALLOW"
    assert await harness["db"].list_human_review_actions(case["case_id"]) == []


@pytest.mark.asyncio
async def test_pipeline_review_path_waits_for_human_then_finalizes() -> None:
    harness = build_harness()
    request = make_request(harness["db"], harness["broker"], "/v1/transactions")
    payload = make_transaction_payload(
        amount="7000.00",
        metadata={"new_device": True, "high_velocity": True, "device_trust": "unverified", "account_age_days": 3},
    )

    stored = await harness["ingest_transaction"](payload=payload, request=request, idempotency_key="review-case")
    await drain_events(harness)

    case = await harness["db"].get_case_by_transaction(stored.transaction_id)
    review_actions = await harness["db"].list_human_review_actions(case["case_id"])
    assert review_actions[0]["action"] == "REVIEW_REQUESTED"

    decision_request = make_request(
        harness["db"],
        harness["broker"],
        f"/v1/cases/{case['case_id']}/decision",
    )
    review_payload = harness["ReviewDecisionIn"].model_validate(
        {
            "reviewer_id": "reviewer-1",
            "outcome": "ALLOW",
            "comment": "verified",
            "labels": ["manual_ok"],
        }
    )
    await harness["add_decision"](case["case_id"], review_payload, decision_request)
    await drain_events(harness)

    decisions = await harness["db"].list_decisions(case["case_id"])
    assert [entry["decision_kind"] for entry in decisions] == [
        "SYSTEM_RECOMMENDATION",
        "HUMAN_REVIEW",
        "FINAL",
    ]
    assert decisions[-1]["decision"] == "ALLOW"


@pytest.mark.asyncio
async def test_pipeline_block_path_finalizes_with_block() -> None:
    harness = build_harness()
    request = make_request(harness["db"], harness["broker"], "/v1/transactions")
    payload = make_transaction_payload(
        amount="20000.00",
        metadata={
            "new_device": True,
            "high_velocity": True,
            "geo_mismatch": True,
            "device_trust": "unverified",
            "account_age_days": 0,
        },
    )

    stored = await harness["ingest_transaction"](payload=payload, request=request, idempotency_key="block-case")
    await drain_events(harness)

    case = await harness["db"].get_case_by_transaction(stored.transaction_id)
    decisions = await harness["db"].list_decisions(case["case_id"])
    assert decisions[-1]["decision"] == "BLOCK"


@pytest.mark.asyncio
async def test_retry_dlq_replay_recovers_case() -> None:
    harness = build_harness()
    request = make_request(harness["db"], harness["broker"], "/v1/transactions")
    payload = make_transaction_payload(
        amount="100.00",
        metadata={"device_trust": "trusted", "account_age_days": 730},
    )

    stored = await harness["ingest_transaction"](payload=payload, request=request, idempotency_key="replay-case")
    await drain_events(harness, fail_context=True, max_retry_attempts=2)

    case = await harness["db"].get_case_by_transaction(stored.transaction_id)
    dlq_events = await harness["db"].list_dlq_events()
    assert len(dlq_events) == 1
    assert not await harness["db"].list_decisions(case["case_id"])

    replay_request = make_request(
        harness["db"],
        harness["broker"],
        f"/v1/dlq/replay/{dlq_events[0]['event_id']}",
    )
    replay_body = harness["DlqReplayRequest"](reset_attempt=True)
    replay_response = await harness["replay_dlq_event"](dlq_events[0]["event_id"], replay_body, replay_request)
    assert replay_response.attempt == 1

    await drain_events(harness, fail_context=False)

    decisions = await harness["db"].list_decisions(case["case_id"])
    assert decisions[-1]["decision"] == "ALLOW"
