from __future__ import annotations

import asyncio

from app.config import RiskMLSettings
from app.services.agent import RiskMLAgent
from shared.broker import RedisStreamBroker
from shared.database import PlatformDatabase
from shared.events import EventType, StepName, StreamName, build_event, deterministic_uuid
from shared.schemas.agents import ContextAgentOutput, RiskMLAgentRequest
from shared.schemas.transactions import TransactionStored
from shared.worker import StreamWorker


class RiskStreamWorker:
    def __init__(self, settings: RiskMLSettings, db: PlatformDatabase, broker: RedisStreamBroker) -> None:
        self.settings = settings
        self.db = db
        self.broker = broker
        self.agent = RiskMLAgent()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._worker = StreamWorker(
            service_name=settings.service_name,
            stream_name=StreamName.AGENT_RISK_COMMANDS,
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
        self._task = asyncio.create_task(self._worker.run(self._stop_event), name="risk-stream-worker")

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
            stream_name=StreamName.AGENT_RISK_COMMANDS,
            stream_message_id=message_id,
        )

        if event.event_type != EventType.STEP_RUN_REQUESTED:
            return
        if event.payload.get("step") != StepName.RISK:
            return

        input_payload = event.payload.get("input", {})
        context_payload = input_payload.get("context")
        context = ContextAgentOutput.model_validate(context_payload) if context_payload else None

        request = RiskMLAgentRequest(
            transaction=TransactionStored.model_validate(input_payload["transaction"]),
            context=context,
            trace_id=event.trace_id or event.correlation_id,
        )
        response = await self.agent.execute(request)

        completed_event = build_event(
            event_type=EventType.AGENT_RISK_COMPLETED,
            case_id=event.case_id,
            transaction_id=event.transaction_id,
            producer=self.settings.service_name,
            causation_id=event.event_id,
            trace_id=event.trace_id,
            traceparent=event.traceparent,
            event_id=deterministic_uuid(event.case_id, EventType.AGENT_RISK_COMPLETED, event.event_id),
            idempotency_key=f"{event.case_id}:risk:{event.event_id}",
            payload=response.model_dump(mode="json"),
        )
        out_message_id = await self.broker.publish(StreamName.CASE_EVENTS, completed_event)
        await self.db.append_case_event(
            event=completed_event,
            stream_name=StreamName.CASE_EVENTS,
            stream_message_id=out_message_id,
        )
        await self.db.append_agent_run(
            agent_run_id=deterministic_uuid(event.case_id, "agent-run-risk", event.event_id),
            case_id=event.case_id,
            agent_name=self.settings.service_name,
            step_name=StepName.RISK,
            attempt=event.attempt,
            status="COMPLETED",
            started_at=response.metadata.started_at,
            finished_at=response.metadata.completed_at,
            latency_ms=response.metadata.latency_ms,
            agent_version=self.settings.model_version,
            input_event_id=event.event_id,
            output_event_id=completed_event.event_id,
            error_code=None,
            error_message=None,
        )
