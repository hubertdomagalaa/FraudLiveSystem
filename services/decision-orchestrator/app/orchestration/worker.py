from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import OrchestratorSettings
from shared.broker import RedisStreamBroker
from shared.database import PlatformDatabase
from shared.events import (
    EventType,
    StepName,
    StreamName,
    build_event,
    deterministic_uuid,
)
from shared.worker import StreamWorker

logger = logging.getLogger("decision-orchestrator")


class OrchestrationWorker:
    def __init__(self, settings: OrchestratorSettings, db: PlatformDatabase, broker: RedisStreamBroker) -> None:
        self.settings = settings
        self.db = db
        self.broker = broker
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._worker = StreamWorker(
            service_name=settings.service_name,
            stream_name=StreamName.CASE_EVENTS,
            consumer_group=settings.consumer_group,
            consumer_name=settings.consumer_name,
            broker=broker,
            db=db,
            handler=self._handle_event,
            block_ms=settings.redis_block_ms,
            read_count=settings.redis_read_count,
            claim_idle_ms=settings.redis_claim_idle_ms,
            max_retry_attempts=settings.max_retry_attempts,
            dlq_stream=StreamName.DEAD_LETTER,
        )

    async def start(self) -> None:
        self._task = asyncio.create_task(self._worker.run(self._stop_event), name="orchestrator-worker")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _handle_event(self, event, message_id: str) -> None:
        await self.db.append_case_event(
            event=event,
            stream_name=StreamName.CASE_EVENTS,
            stream_message_id=message_id,
        )

        if event.event_type == EventType.CASE_CREATED:
            transaction = event.payload.get("transaction", {})
            await self._publish_step_command(
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                step=StepName.CONTEXT,
                input_payload={"transaction": transaction},
                causation_id=event.event_id,
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            return

        if event.event_type == EventType.AGENT_CONTEXT_COMPLETED:
            transaction = await self._get_transaction(case_id=event.case_id)
            context = event.payload.get("result", {})
            await self._publish_step_command(
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                step=StepName.RISK,
                input_payload={"transaction": transaction, "context": context},
                causation_id=event.event_id,
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            return

        if event.event_type == EventType.AGENT_RISK_COMPLETED:
            transaction = await self._get_transaction(case_id=event.case_id)
            context_event = await self.db.get_latest_event_payload(
                case_id=event.case_id,
                event_type=EventType.AGENT_CONTEXT_COMPLETED,
            )
            risk = event.payload.get("result", {})
            await self._publish_step_command(
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                step=StepName.POLICY,
                input_payload={
                    "transaction": transaction,
                    "context": (context_event or {}).get("result", {}),
                    "risk": risk,
                },
                causation_id=event.event_id,
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            return

        if event.event_type == EventType.AGENT_POLICY_COMPLETED:
            transaction = await self._get_transaction(case_id=event.case_id)
            risk_event = await self.db.get_latest_event_payload(
                case_id=event.case_id,
                event_type=EventType.AGENT_RISK_COMPLETED,
            )
            policy = event.payload.get("result", {})
            await self._publish_step_command(
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                step=StepName.EXPLAIN,
                input_payload={
                    "transaction": transaction,
                    "risk": (risk_event or {}).get("result", {}),
                    "policy": policy,
                },
                causation_id=event.event_id,
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            return

        if event.event_type == EventType.AGENT_EXPLAIN_COMPLETED:
            transaction = await self._get_transaction(case_id=event.case_id)
            context_event = await self.db.get_latest_event_payload(
                case_id=event.case_id,
                event_type=EventType.AGENT_CONTEXT_COMPLETED,
            )
            risk_event = await self.db.get_latest_event_payload(
                case_id=event.case_id,
                event_type=EventType.AGENT_RISK_COMPLETED,
            )
            policy_event = await self.db.get_latest_event_payload(
                case_id=event.case_id,
                event_type=EventType.AGENT_POLICY_COMPLETED,
            )

            await self._publish_step_command(
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                step=StepName.AGGREGATE,
                input_payload={
                    "transaction": transaction,
                    "context": (context_event or {}).get("result", {}),
                    "risk": (risk_event or {}).get("result", {}),
                    "policy": (policy_event or {}).get("result", {}),
                    "explain": event.payload.get("result", {}),
                },
                causation_id=event.event_id,
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            return

        if event.event_type == EventType.AGENT_AGGREGATE_COMPLETED:
            recommendation = str(event.payload.get("recommendation", "REVIEW")).upper()
            reason_codes = event.payload.get("reason_codes", [])
            requires_review = bool(event.payload.get("requires_human_review", recommendation == "REVIEW"))

            await self.db.append_decision_record(
                decision_id=deterministic_uuid(event.case_id, "system-recommendation", event.event_id),
                case_id=event.case_id,
                decision_kind="SYSTEM_RECOMMENDATION",
                decision=recommendation,
                confidence=event.payload.get("confidence"),
                reason_summary=event.payload.get("summary"),
                reason_details={"reason_codes": reason_codes, "payload": event.payload},
                decided_by="decision-orchestrator",
                source_event_id=event.event_id,
            )

            if requires_review:
                await self._publish_case_event(
                    event_type=EventType.CASE_HUMAN_REVIEW_REQUIRED,
                    case_id=event.case_id,
                    transaction_id=event.transaction_id,
                    causation_id=event.event_id,
                    payload={
                        "recommendation": recommendation,
                        "reason_codes": reason_codes,
                    },
                    trace_id=event.trace_id,
                    traceparent=event.traceparent,
                )
                await self._publish_step_command(
                    case_id=event.case_id,
                    transaction_id=event.transaction_id,
                    step=StepName.HUMAN_REVIEW,
                    input_payload={
                        "recommendation": recommendation,
                        "reason_codes": reason_codes,
                        "decision_event_id": event.event_id,
                    },
                    causation_id=event.event_id,
                    trace_id=event.trace_id,
                    traceparent=event.traceparent,
                )
                return

            await self._publish_case_event(
                event_type=EventType.CASE_FINALIZED,
                case_id=event.case_id,
                transaction_id=event.transaction_id,
                causation_id=event.event_id,
                payload={
                    "final_decision": recommendation,
                    "finalized_by": "decision-orchestrator",
                    "reason_codes": reason_codes,
                },
                trace_id=event.trace_id,
                traceparent=event.traceparent,
            )
            await self.db.append_decision_record(
                decision_id=deterministic_uuid(event.case_id, "final-system", event.event_id),
                case_id=event.case_id,
                decision_kind="FINAL",
                decision=recommendation,
                confidence=event.payload.get("confidence"),
                reason_summary="Finalized without manual review",
                reason_details={"reason_codes": reason_codes},
                decided_by="decision-orchestrator",
                source_event_id=event.event_id,
            )
            return

        if event.event_type == EventType.CASE_HUMAN_REVIEW_COMPLETED:
            final_decision = str(event.payload.get("action", "REVIEW")).upper()
            await self.db.append_decision_record(
                decision_id=deterministic_uuid(event.case_id, "final-human", event.event_id),
                case_id=event.case_id,
                decision_kind="FINAL",
                decision=final_decision,
                confidence=None,
                reason_summary="Human reviewer final decision",
                reason_details={"review": event.payload},
                decided_by="human-review-api",
                source_event_id=event.event_id,
            )
            return

    async def _publish_step_command(
        self,
        *,
        case_id: str,
        transaction_id: str,
        step: str,
        input_payload: dict[str, Any],
        causation_id: str,
        trace_id: str | None,
        traceparent: str | None,
    ) -> None:
        command_stream = {
            StepName.CONTEXT: StreamName.AGENT_CONTEXT_COMMANDS,
            StepName.RISK: StreamName.AGENT_RISK_COMMANDS,
            StepName.POLICY: StreamName.AGENT_POLICY_COMMANDS,
            StepName.EXPLAIN: StreamName.AGENT_EXPLAIN_COMMANDS,
            StepName.AGGREGATE: StreamName.AGENT_AGGREGATE_COMMANDS,
            StepName.HUMAN_REVIEW: StreamName.HUMAN_REVIEW_COMMANDS,
        }[step]

        event = build_event(
            event_type=EventType.STEP_RUN_REQUESTED,
            case_id=case_id,
            transaction_id=transaction_id,
            producer=self.settings.service_name,
            causation_id=causation_id,
            trace_id=trace_id,
            traceparent=traceparent,
            event_id=deterministic_uuid(case_id, str(step), causation_id),
            idempotency_key=f"{case_id}:{step}:{causation_id}",
            payload={
                "step": step,
                "input": input_payload,
            },
        )
        stream_message_id = await self.broker.publish(command_stream, event)
        await self.db.append_case_event(
            event=event,
            stream_name=command_stream,
            stream_message_id=stream_message_id,
        )

    async def _publish_case_event(
        self,
        *,
        event_type: str,
        case_id: str,
        transaction_id: str,
        payload: dict[str, Any],
        causation_id: str,
        trace_id: str | None,
        traceparent: str | None,
    ) -> None:
        event = build_event(
            event_type=event_type,
            case_id=case_id,
            transaction_id=transaction_id,
            producer=self.settings.service_name,
            causation_id=causation_id,
            trace_id=trace_id,
            traceparent=traceparent,
            event_id=deterministic_uuid(case_id, event_type, causation_id),
            idempotency_key=f"{case_id}:{event_type}:{causation_id}",
            payload=payload,
        )
        stream_message_id = await self.broker.publish(StreamName.CASE_EVENTS, event)
        await self.db.append_case_event(
            event=event,
            stream_name=StreamName.CASE_EVENTS,
            stream_message_id=stream_message_id,
        )

    async def _get_transaction(self, *, case_id: str) -> dict[str, Any]:
        case = await self.db.get_case(case_id)
        if not case:
            raise RuntimeError(f"Case not found for case_id={case_id}")
        return dict(case["initial_payload"])
