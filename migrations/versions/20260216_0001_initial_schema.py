"""Initial platform schema.

Revision ID: 20260216_0001
Revises:
Create Date: 2026-02-16
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260216_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS consumer_dedup;
        DROP TABLE IF EXISTS human_review_actions;
        DROP TABLE IF EXISTS decision_records;
        DROP TABLE IF EXISTS agent_runs;
        DROP TABLE IF EXISTS case_events;
        DROP TABLE IF EXISTS cases;
        """
    )
