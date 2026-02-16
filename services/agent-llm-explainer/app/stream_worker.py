from __future__ import annotations

import asyncio

from app.config import LLMExplainerSettings
from app.services.agent import LLMExplanationAgent
from shared.broker import RedisStreamBroker
from shared.database import PlatformDatabase
from shared.events import EventType, StepName, StreamName, build_event, deterministic_uuid
from shared.schemas.agents import LLMExplanationRequest
from shared.schemas.transactions import TransactionStored
from shared.worker import StreamWorker


class ExplainStreamWorker:
    def __init__(self, settings: LLMExplainerSettings, db: PlatformDatabase, broker: RedisStreamBroker) -> None:
        self.settings = settings
        self.db = db
        self.broker = broker
        self.agent = LLMExplanationAgent()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._worker = StreamWorker(
            service_name=settings.service_name,
            stream_name=StreamName.AGENT_EXPLAIN_COMMANDS,
            consumer_group=settings.consumer_group,
            consumer_name=settings.consumer_name,
            broker=broker,
            db=db,
            handler=self._handle,
            block_ms=settings.redis_block_ms,
            read_count=settings.redis_read_count,
            claim_idle_ms=settings.redis_claim_idle_ms,
            max_retry_attempts=settings.max_retry_attempts,
        )

    async def start(self) -> None:
        self._task = asyncio.create_task(self._worker.run(self._stop_event), name="explain-stream-worker")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _handle(self, event, message_id: str) -> None:
        await self.db.append_case_event(
            event=event,
            stream_name=StreamName.AGENT_EXPLAIN_COMMANDS,
            stream_message_id=message_id,
        )

        if event.event_type != EventType.STEP_RUN_REQUESTED:
            return
        if event.payload.get("step") != StepName.EXPLAIN:
            return

        input_payload = event.payload.get("input", {})
        risk = input_payload.get("risk", {})
        policy = input_payload.get("policy", {})

        request = LLMExplanationRequest(
            transaction=TransactionStored.model_validate(input_payload["transaction"]),
            risk_score=float(risk.get("risk_score", 0.0)),
            policy_action=policy.get("action", "REVIEW"),
            reason_codes=policy.get("violations", []),
            trace_id=event.trace_id or event.correlation_id,
        )
        response = await self.agent.execute(request)

        completed_event = build_event(
            event_type=EventType.AGENT_EXPLAIN_COMPLETED,
            case_id=event.case_id,
            transaction_id=event.transaction_id,
            producer=self.settings.service_name,
            causation_id=event.event_id,
            trace_id=event.trace_id,
            traceparent=event.traceparent,
            event_id=deterministic_uuid(event.case_id, EventType.AGENT_EXPLAIN_COMPLETED, event.event_id),
            idempotency_key=f"{event.case_id}:explain:{event.event_id}",
            payload=response.model_dump(mode="json"),
        )
        out_message_id = await self.broker.publish(StreamName.CASE_EVENTS, completed_event)
        await self.db.append_case_event(
            event=completed_event,
            stream_name=StreamName.CASE_EVENTS,
            stream_message_id=out_message_id,
        )
        await self.db.append_agent_run(
            agent_run_id=deterministic_uuid(event.case_id, "agent-run-explain", event.event_id),
            case_id=event.case_id,
            agent_name=self.settings.service_name,
            step_name=StepName.EXPLAIN,
            attempt=event.attempt,
            status="COMPLETED",
            started_at=response.metadata.started_at,
            finished_at=response.metadata.completed_at,
            latency_ms=response.metadata.latency_ms,
            agent_version=self.settings.prompt_version,
            input_event_id=event.event_id,
            output_event_id=completed_event.event_id,
            error_code=None,
            error_message=None,
        )
