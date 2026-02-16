from __future__ import annotations

from typing import Any

import asyncpg

from shared.events import EventEnvelope, utc_now


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id UUID PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    ingest_idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    source_system TEXT NOT NULL,
    ingest_event_id UUID NOT NULL UNIQUE,
    initial_payload JSONB NOT NULL
);

ALTER TABLE cases
ADD COLUMN IF NOT EXISTS ingest_idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_cases_ingest_idempotency
ON cases(ingest_idempotency_key)
WHERE ingest_idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS case_events (
    event_id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(case_id),
    transaction_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    producer_service TEXT NOT NULL,
    stream_name TEXT NOT NULL,
    stream_message_id TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id UUID NOT NULL,
    trace_id TEXT,
    traceparent TEXT,
    causation_id UUID,
    idempotency_key TEXT NOT NULL,
    attempt INT NOT NULL,
    payload JSONB NOT NULL
);

ALTER TABLE case_events
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE case_events
ADD COLUMN IF NOT EXISTS traceparent TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_case_events_stream_message
ON case_events(stream_name, stream_message_id)
WHERE stream_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_case_events_case_time
ON case_events(case_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_case_events_type_time
ON case_events(event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_case_events_idempotency
ON case_events(idempotency_key);

CREATE INDEX IF NOT EXISTS ix_case_events_trace
ON case_events(trace_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS agent_runs (
    agent_run_id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(case_id),
    agent_name TEXT NOT NULL,
    step_name TEXT NOT NULL,
    attempt INT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    latency_ms INT NOT NULL,
    agent_version TEXT,
    input_event_id UUID REFERENCES case_events(event_id),
    output_event_id UUID REFERENCES case_events(event_id),
    error_code TEXT,
    error_message TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_runs_case_step_attempt
ON agent_runs(case_id, step_name, attempt);

CREATE INDEX IF NOT EXISTS ix_agent_runs_case_started
ON agent_runs(case_id, started_at);

CREATE TABLE IF NOT EXISTS decision_records (
    decision_id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(case_id),
    decision_kind TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence NUMERIC(5,4),
    reason_summary TEXT,
    reason_details JSONB NOT NULL,
    decided_by TEXT NOT NULL,
    source_event_id UUID REFERENCES case_events(event_id),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_decisions_case_kind_source
ON decision_records(case_id, decision_kind, source_event_id);

CREATE INDEX IF NOT EXISTS ix_decisions_case_created
ON decision_records(case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS human_review_actions (
    review_action_id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(case_id),
    reviewer_id TEXT,
    action TEXT NOT NULL,
    reason_code TEXT,
    notes TEXT,
    source_event_id UUID REFERENCES case_events(event_id),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_review_actions_case_created
ON human_review_actions(case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS consumer_dedup (
    consumer_dedup_id BIGSERIAL PRIMARY KEY,
    consumer_group TEXT NOT NULL,
    stream_name TEXT NOT NULL,
    event_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL,
    processing_result TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_consumer_dedup_event
ON consumer_dedup(consumer_group, event_id);

DROP INDEX IF EXISTS uq_consumer_dedup_idempotency;

CREATE INDEX IF NOT EXISTS ix_consumer_dedup_idempotency
ON consumer_dedup(consumer_group, idempotency_key);
"""


class PlatformDatabase:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def ensure_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

    async def insert_case(
        self,
        *,
        case_id: str,
        transaction_id: str,
        ingest_idempotency_key: str | None,
        source_system: str,
        ingest_event_id: str,
        initial_payload: dict[str, Any],
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO cases (
                    case_id,
                    transaction_id,
                    ingest_idempotency_key,
                    created_at,
                    source_system,
                    ingest_event_id,
                    initial_payload
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
                """,
                case_id,
                transaction_id,
                ingest_idempotency_key,
                utc_now(),
                source_system,
                ingest_event_id,
                initial_payload,
            )
        return result.endswith("1")

    async def get_case_by_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    case_id,
                    transaction_id,
                    ingest_idempotency_key,
                    created_at,
                    source_system,
                    ingest_event_id,
                    initial_payload
                FROM cases
                WHERE transaction_id = $1
                """,
                transaction_id,
            )
        return dict(row) if row else None

    async def get_case_by_ingest_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    case_id,
                    transaction_id,
                    ingest_idempotency_key,
                    created_at,
                    source_system,
                    ingest_event_id,
                    initial_payload
                FROM cases
                WHERE ingest_idempotency_key = $1
                """,
                idempotency_key,
            )
        return dict(row) if row else None

    async def get_case(self, case_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    case_id,
                    transaction_id,
                    ingest_idempotency_key,
                    created_at,
                    source_system,
                    ingest_event_id,
                    initial_payload
                FROM cases
                WHERE case_id = $1
                """,
                case_id,
            )
        return dict(row) if row else None

    async def append_case_event(
        self,
        *,
        event: EventEnvelope,
        stream_name: str,
        stream_message_id: str | None,
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO case_events (
                    event_id,
                    case_id,
                    transaction_id,
                    event_type,
                    producer_service,
                    stream_name,
                    stream_message_id,
                    occurred_at,
                    correlation_id,
                    trace_id,
                    traceparent,
                    causation_id,
                    idempotency_key,
                    attempt,
                    payload
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (event_id) DO NOTHING
                """,
                event.event_id,
                event.case_id,
                event.transaction_id,
                event.event_type,
                event.producer,
                stream_name,
                stream_message_id,
                event.occurred_at,
                event.correlation_id,
                event.trace_id,
                event.traceparent,
                event.causation_id,
                event.idempotency_key,
                event.attempt,
                event.payload,
            )
        return result.endswith("1")

    async def append_agent_run(
        self,
        *,
        agent_run_id: str,
        case_id: str,
        agent_name: str,
        step_name: str,
        attempt: int,
        status: str,
        started_at,
        finished_at,
        latency_ms: int,
        agent_version: str | None,
        input_event_id: str | None,
        output_event_id: str | None,
        error_code: str | None,
        error_message: str | None,
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO agent_runs (
                    agent_run_id,
                    case_id,
                    agent_name,
                    step_name,
                    attempt,
                    status,
                    started_at,
                    finished_at,
                    latency_ms,
                    agent_version,
                    input_event_id,
                    output_event_id,
                    error_code,
                    error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (case_id, step_name, attempt) DO NOTHING
                """,
                agent_run_id,
                case_id,
                agent_name,
                step_name,
                attempt,
                status,
                started_at,
                finished_at,
                latency_ms,
                agent_version,
                input_event_id,
                output_event_id,
                error_code,
                error_message,
            )
        return result.endswith("1")

    async def append_decision_record(
        self,
        *,
        decision_id: str,
        case_id: str,
        decision_kind: str,
        decision: str,
        confidence: float | None,
        reason_summary: str | None,
        reason_details: dict[str, Any],
        decided_by: str,
        source_event_id: str | None,
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO decision_records (
                    decision_id,
                    case_id,
                    decision_kind,
                    decision,
                    confidence,
                    reason_summary,
                    reason_details,
                    decided_by,
                    source_event_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (decision_id) DO NOTHING
                """,
                decision_id,
                case_id,
                decision_kind,
                decision,
                confidence,
                reason_summary,
                reason_details,
                decided_by,
                source_event_id,
                utc_now(),
            )
        return result.endswith("1")

    async def append_human_review_action(
        self,
        *,
        review_action_id: str,
        case_id: str,
        reviewer_id: str | None,
        action: str,
        reason_code: str | None,
        notes: str | None,
        source_event_id: str | None,
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO human_review_actions (
                    review_action_id,
                    case_id,
                    reviewer_id,
                    action,
                    reason_code,
                    notes,
                    source_event_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (review_action_id) DO NOTHING
                """,
                review_action_id,
                case_id,
                reviewer_id,
                action,
                reason_code,
                notes,
                source_event_id,
                utc_now(),
            )
        return result.endswith("1")

    async def mark_consumer_processed(
        self,
        *,
        consumer_group: str,
        stream_name: str,
        event_id: str,
        idempotency_key: str,
        processing_result: str,
    ) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO consumer_dedup (
                    consumer_group,
                    stream_name,
                    event_id,
                    idempotency_key,
                    processed_at,
                    processing_result
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (consumer_group, event_id) DO NOTHING
                """,
                consumer_group,
                stream_name,
                event_id,
                idempotency_key,
                utc_now(),
                processing_result,
            )
        return result.endswith("1")

    async def is_consumer_processed(self, *, consumer_group: str, event_id: str) -> bool:
        async with self.pool.acquire() as conn:
            found = await conn.fetchval(
                """
                SELECT 1
                FROM consumer_dedup
                WHERE consumer_group = $1
                  AND event_id = $2
                LIMIT 1
                """,
                consumer_group,
                event_id,
            )
        return bool(found)

    async def get_latest_event_payload(self, *, case_id: str, event_type: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT payload
                FROM case_events
                WHERE case_id = $1
                  AND event_type = $2
                ORDER BY occurred_at DESC, recorded_at DESC
                LIMIT 1
                """,
                case_id,
                event_type,
            )
        if not row:
            return None
        return dict(row["payload"])

    async def list_case_events(self, case_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    event_id,
                    event_type,
                    producer_service,
                    stream_name,
                    occurred_at,
                    recorded_at,
                    trace_id,
                    traceparent,
                    payload
                FROM case_events
                WHERE case_id = $1
                ORDER BY occurred_at ASC, recorded_at ASC
                """,
                case_id,
            )
        return [dict(row) for row in rows]

    async def get_case_event(self, event_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    event_id,
                    case_id,
                    transaction_id,
                    event_type,
                    producer_service,
                    stream_name,
                    stream_message_id,
                    occurred_at,
                    recorded_at,
                    correlation_id,
                    trace_id,
                    traceparent,
                    causation_id,
                    idempotency_key,
                    attempt,
                    payload
                FROM case_events
                WHERE event_id = $1
                """,
                event_id,
            )
        return dict(row) if row else None

    async def list_dlq_events(self, limit: int = 100) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    event_id,
                    case_id,
                    transaction_id,
                    stream_name,
                    producer_service,
                    occurred_at,
                    trace_id,
                    traceparent,
                    payload
                FROM case_events
                WHERE event_type = 'dead_letter.event'
                ORDER BY occurred_at DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(row) for row in rows]

    async def list_cases(self, limit: int = 100) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.case_id,
                    c.transaction_id,
                    c.created_at,
                    d.decision AS latest_decision,
                    d.created_at AS decision_time,
                    h.action AS latest_human_action,
                    h.created_at AS human_action_time
                FROM cases c
                LEFT JOIN LATERAL (
                    SELECT decision, created_at
                    FROM decision_records dr
                    WHERE dr.case_id = c.case_id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) d ON TRUE
                LEFT JOIN LATERAL (
                    SELECT action, created_at
                    FROM human_review_actions hra
                    WHERE hra.case_id = c.case_id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) h ON TRUE
                ORDER BY c.created_at DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(row) for row in rows]

    async def list_agent_runs(self, case_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    agent_run_id,
                    agent_name,
                    step_name,
                    attempt,
                    status,
                    started_at,
                    finished_at,
                    latency_ms,
                    agent_version,
                    error_code,
                    error_message
                FROM agent_runs
                WHERE case_id = $1
                ORDER BY started_at ASC
                """,
                case_id,
            )
        return [dict(row) for row in rows]

    async def list_decisions(self, case_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    decision_id,
                    decision_kind,
                    decision,
                    confidence,
                    reason_summary,
                    reason_details,
                    decided_by,
                    source_event_id,
                    created_at
                FROM decision_records
                WHERE case_id = $1
                ORDER BY created_at ASC
                """,
                case_id,
            )
        return [dict(row) for row in rows]

    async def list_human_review_actions(self, case_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    review_action_id,
                    reviewer_id,
                    action,
                    reason_code,
                    notes,
                    source_event_id,
                    created_at
                FROM human_review_actions
                WHERE case_id = $1
                ORDER BY created_at ASC
                """,
                case_id,
            )
        return [dict(row) for row in rows]
