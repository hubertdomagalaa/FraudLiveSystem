"""Add trace context columns to case_events.

Revision ID: 20260216_0002
Revises: 20260216_0001
Create Date: 2026-02-16
"""
from __future__ import annotations

from alembic import op


revision = "20260216_0002"
down_revision = "20260216_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE case_events
        ADD COLUMN IF NOT EXISTS trace_id TEXT;

        ALTER TABLE case_events
        ADD COLUMN IF NOT EXISTS traceparent TEXT;

        CREATE INDEX IF NOT EXISTS ix_case_events_trace
        ON case_events(trace_id, occurred_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_case_events_trace;
        ALTER TABLE case_events DROP COLUMN IF EXISTS traceparent;
        ALTER TABLE case_events DROP COLUMN IF EXISTS trace_id;
        """
    )
