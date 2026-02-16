from __future__ import annotations

import asyncio

from app.config import HumanReviewSettings
from shared.broker import RedisStreamBroker
from shared.database import PlatformDatabase
from shared.events import EventType, StepName, StreamName, deterministic_uuid
from shared.worker import StreamWorker


class HumanReviewStreamWorker:
    def __init__(self, settings: HumanReviewSettings, db: PlatformDatabase, broker: RedisStreamBroker) -> None:
        self.settings = settings
        self.db = db
        self.broker = broker
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._worker = StreamWorker(
            service_name=settings.service_name,
            stream_name=StreamName.HUMAN_REVIEW_COMMANDS,
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
        self._task = asyncio.create_task(self._worker.run(self._stop_event), name="human-review-stream-worker")

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
            stream_name=StreamName.HUMAN_REVIEW_COMMANDS,
            stream_message_id=message_id,
        )

        if event.event_type != EventType.STEP_RUN_REQUESTED:
            return
        if event.payload.get("step") != StepName.HUMAN_REVIEW:
            return

        reason_codes = event.payload.get("input", {}).get("reason_codes", [])
        reason_code = ",".join(reason_codes) if reason_codes else None

        await self.db.append_human_review_action(
            review_action_id=deterministic_uuid(event.case_id, "review-request", event.event_id),
            case_id=event.case_id,
            reviewer_id=None,
            action="REVIEW_REQUESTED",
            reason_code=reason_code,
            notes="Case routed to human review queue.",
            source_event_id=event.event_id,
        )
