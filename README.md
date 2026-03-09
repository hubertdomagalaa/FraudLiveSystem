# Fraud Decision Support Platform

Production-grade, event-driven Fraud Decision Support platform with explainable AI recommendations and mandatory human-in-the-loop for sensitive cases.

## Why This Project Matters

- Solves a practical fraud operations problem: classify transactions as ALLOW, BLOCK, or REVIEW.
- Preserves auditability by design: append-only event and decision history in PostgreSQL.
- Demonstrates operational maturity: idempotency, retry, DLQ, replay, tracing, and metrics.
- Provides a real operator UI: create transactions, inspect workflow, explain decisions, run review and recovery.

## Core Guarantees

- Redis Streams is the orchestration backbone.
- No direct service -> orchestrator RPC.
- Orchestrator coordinates by emitting step commands only.
- PostgreSQL is the system of record with append-only audit tables.
- REVIEW paths require human decision to finalize.
- Retry + DLQ + replay remain active and test-covered.

## Architecture at a Glance

`	ext
ingestion-api -> case.created (Redis stream)
  -> decision-orchestrator
     -> agent-context -> agent-risk-ml -> agent-policy -> agent-llm-explainer -> agent-aggregate
     -> if REVIEW: human-review-api

All steps append immutable records to Postgres and publish events back to stream.
DLQ failures go to fraud.dlq.v1 and can be replayed from dlq-ops-api.
`

## 90-Second Quickstart

1. Open local run guide: docs/RUN_LOCAL.md
2. Start stack and UI (Docker + Compose).
3. Generate JWT and paste it into UI Bearer Token field.
4. In UI, use Create Transaction preset and submit.
5. Open case details and show:
   - Pipeline Status
   - Why this decision?
   - Manual Review (for REVIEW cases)
   - DLQ Operations replay panel

## Demo Assets

- Local runbook: docs/RUN_LOCAL.md
- 5-minute demo script: docs/DEMO_SCRIPT.md
- Interview checklist: docs/INTERVIEW_CHECKLIST.md
- Demo seed helper:

`powershell
python scripts/demo_seed.py --token YOUR_JWT_TOKEN
`

## Decision Transparency (v2)

- Additive explainability payloads: signals, isk_score, policy_violations, explanation.
- Policy uleset_v2 adds practical fraud signals:
  - merchant risk score,
  - prior chargeback history,
  - high-risk country + new device combinations.
- UI includes dedicated Why this decision? section so operator does not need to read raw JSON.

## Security and Observability

- JWT write protection supports JWT_SECRET (dev) and JWT_JWKS_URL (prod).
- Scope-aware access checks and write rate limiting.
- CORS origin controls for UI.
- OTLP tracing via collector -> Tempo and Prometheus metrics on each service.

## Testing and Quality

- Backend lint + compile + tests (shared + service suites).
- End-to-end pipeline tests include ALLOW/REVIEW/BLOCK and DLQ/replay recovery.
- Frontend tests and production build validation.

## Local Stack Endpoints

- UI: http://localhost:5173
- Ingestion API: http://localhost:8001
- Orchestrator API: http://localhost:8002
- Human Review API: http://localhost:8003
- DLQ Ops API: http://localhost:8004
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## Production Notes

Kubernetes manifests are in infra/k8s. Before real deployment, provide production secrets/IdP config and run migrations against target PostgreSQL.
