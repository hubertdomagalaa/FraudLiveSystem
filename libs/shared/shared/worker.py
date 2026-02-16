from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from shared.broker import RedisStreamBroker, StreamRecord
from shared.database import PlatformDatabase
from shared.events import EventType, EventEnvelope, StreamName, build_event, retry_event
from shared.observability import (
    inc_event_processed,
    inc_stream_dlq,
    inc_stream_retry,
    set_stream_lag,
)


ProcessHandler = Callable[[EventEnvelope, str], Awaitable[None]]


class StreamWorker:
    def __init__(
        self,
        *,
        service_name: str,
        stream_name: str,
        consumer_group: str,
        consumer_name: str,
        broker: RedisStreamBroker,
        db: PlatformDatabase,
        handler: ProcessHandler,
        block_ms: int,
        read_count: int,
        claim_idle_ms: int,
        max_retry_attempts: int,
        dlq_stream: str = StreamName.DEAD_LETTER,
    ) -> None:
        self.service_name = service_name
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.broker = broker
        self.db = db
        self.handler = handler
        self.block_ms = block_ms
        self.read_count = read_count
        self.claim_idle_ms = claim_idle_ms
        self.max_retry_attempts = max_retry_attempts
        self.dlq_stream = dlq_stream
        self.logger = logging.getLogger(service_name)
        self._claim_start_id = "0-0"

    async def run(self, stop_event: asyncio.Event) -> None:
        await self.broker.create_consumer_group(self.stream_name, self.consumer_group)

        while not stop_event.is_set():
            try:
                self._claim_start_id, claimed = await self.broker.autoclaim(
                    stream=self.stream_name,
                    group=self.consumer_group,
                    consumer=self.consumer_name,
                    min_idle_ms=self.claim_idle_ms,
                    start_id=self._claim_start_id,
                    count=self.read_count,
                )
                records = claimed
                if not records:
                    records = await self.broker.read_group(
                        stream=self.stream_name,
                        group=self.consumer_group,
                        consumer=self.consumer_name,
                        count=self.read_count,
                        block_ms=self.block_ms,
                    )
                if not records:
                    continue

                lag = await self.broker.get_group_lag(self.stream_name, self.consumer_group)
                set_stream_lag(self.service_name, self.stream_name, self.consumer_group, lag)

                for record in records:
                    await self._process_record(record)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("stream_worker_loop_error", extra={"stream": self.stream_name})
                await asyncio.sleep(1)

    async def _process_record(self, record: StreamRecord) -> None:
        event = record.event

        if await self.db.is_consumer_processed(
            consumer_group=self.consumer_group,
            event_id=event.event_id,
        ):
            await self.broker.ack(self.stream_name, self.consumer_group, record.message_id)
            return

        try:
            await self.handler(event, record.message_id)
        except Exception as exc:
            failure_result = await self._handle_failure(event=event, error=exc)
            await self.db.mark_consumer_processed(
                consumer_group=self.consumer_group,
                stream_name=self.stream_name,
                event_id=event.event_id,
                idempotency_key=event.idempotency_key,
                processing_result=failure_result,
            )
            await self.broker.ack(self.stream_name, self.consumer_group, record.message_id)
            return

        await self.db.mark_consumer_processed(
            consumer_group=self.consumer_group,
            stream_name=self.stream_name,
            event_id=event.event_id,
            idempotency_key=event.idempotency_key,
            processing_result="success",
        )
        await self.broker.ack(self.stream_name, self.consumer_group, record.message_id)
        inc_event_processed(self.service_name, self.stream_name, event.event_type)

    async def _handle_failure(self, *, event: EventEnvelope, error: Exception) -> str:
        self.logger.exception(
            "stream_event_processing_failed",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "attempt": event.attempt,
                "case_id": event.case_id,
            },
        )

        if event.attempt < self.max_retry_attempts:
            next_event = retry_event(event, producer=self.service_name)
            await self.broker.publish(self.stream_name, next_event)
            inc_stream_retry(self.service_name, self.stream_name, event.event_type)
            return "retried"

        dlq_event = build_event(
            event_type=EventType.DEAD_LETTER_EVENT,
            case_id=event.case_id,
            transaction_id=event.transaction_id,
            producer=self.service_name,
            causation_id=event.event_id,
            trace_id=event.trace_id,
            traceparent=event.traceparent,
            payload={
                "failed_event": event.model_dump(mode="json"),
                "error": str(error),
                "source_stream": self.stream_name,
            },
        )
        await self.broker.publish(self.dlq_stream, dlq_event)
        inc_stream_dlq(self.service_name, self.stream_name, event.event_type)
        return "failed"
