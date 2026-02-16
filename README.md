# Fraud Decision Support Platform

Production-grade, event-driven backend platform for fraud case decision support with mandatory human review.

## System Guarantees

- Redis Streams is the execution backbone.
- Ingestion API only publishes `case.created` events.
- Decision Orchestrator only consumes events and emits step commands.
- No service calls orchestrator directly.
- PostgreSQL is the system of record.
- Writes are append-only (`cases`, `case_events`, `agent_runs`, `decision_records`, `human_review_actions`, `consumer_dedup`).
- One transaction equals one case lifecycle.

## Architecture (ASCII)

```text
[Ingestion API]
   |  insert case (Postgres)
   |  XADD case.created
   v
Redis: fraud.case.events.v1  (cg.orchestrator)
   |
   |--> orchestrator emits step.run.requested -> fraud.agent.context.cmd.v1   -> [agent-context]
   |--> orchestrator emits step.run.requested -> fraud.agent.risk.cmd.v1      -> [agent-risk-ml]
   |--> orchestrator emits step.run.requested -> fraud.agent.policy.cmd.v1    -> [agent-policy]
   |--> orchestrator emits step.run.requested -> fraud.agent.explain.cmd.v1   -> [agent-llm-explainer]
   |--> orchestrator emits step.run.requested -> fraud.agent.aggregate.cmd.v1 -> [agent-aggregate]
   |--> if REVIEW: orchestrator emits human command -> fraud.human_review.cmd.v1 -> [human-review-api]

[All agents + human-review-api]
   |  append agent_runs / human_review_actions (Postgres)
   |  XADD completion events to fraud.case.events.v1
   v
[Decision Orchestrator]
   |  appends decision_records
   |  publishes case.finalized (or waits for case.human_review.completed)

[DLQ Ops API]
   |  consumes fraud.dlq.v1 (cg.dlq.ops)
   |  lists/replays dead-letter events
```

## Event Streams and Consumer Groups

- `fraud.case.events.v1` -> `cg.orchestrator`
- `fraud.agent.context.cmd.v1` -> `cg.agent.context`
- `fraud.agent.risk.cmd.v1` -> `cg.agent.risk`
- `fraud.agent.policy.cmd.v1` -> `cg.agent.policy`
- `fraud.agent.explain.cmd.v1` -> `cg.agent.explain`
- `fraud.agent.aggregate.cmd.v1` -> `cg.agent.aggregate`
- `fraud.human_review.cmd.v1` -> `cg.human.review`
- `fraud.dlq.v1` -> `cg.dlq.ops`

## PostgreSQL Data Model

- `cases`: immutable case root (transaction to case mapping).
- `case_events`: immutable event log for full timeline reconstruction.
- `agent_runs`: immutable per-step execution metadata.
- `decision_records`: immutable system and human decisions.
- `human_review_actions`: immutable human-review queue and reviewer actions.
- `consumer_dedup`: immutable consumer idempotency ledger.

## Local Run

1. Start infrastructure:

```bash
docker compose up -d postgres redis
```

2. Run DB migrations:

```bash
pip install -r requirements-dev.txt
POSTGRES_DSN=postgresql://fraud:fraud@localhost:5432/fraud_platform alembic upgrade head
```

3. Start application stack:

```bash
docker compose up --build
```

4. Generate JWT for write endpoints:

```bash
python - <<'PY'
import jwt, datetime
token = jwt.encode(
    {"sub":"demo-user","scope":"fraud.write","exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
    "dev-secret-change-me",
    algorithm="HS256",
)
print(token)
PY
```

Use token as `TOKEN` in commands below.

5. Ingest a transaction:

```bash
curl -X POST http://localhost:8001/v1/transactions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-case-001" \
  -d '{
    "amount": 1200.50,
    "currency": "USD",
    "merchant_id": "merchant-1",
    "card_id": "card-xyz",
    "timestamp": "2026-02-08T10:00:00Z",
    "metadata": {"device_trust": "unverified", "new_device": true}
  }'
```

6. Inspect case timeline:

```bash
curl http://localhost:8002/v1/cases
curl http://localhost:8002/v1/cases/<case_id>/events
curl http://localhost:8002/v1/cases/<case_id>/agent-runs
curl http://localhost:8002/v1/cases/<case_id>/decisions
```

7. Submit human review decision (for REVIEW cases):

```bash
curl -X POST http://localhost:8003/v1/cases/<case_id>/decision \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"reviewer_id":"reviewer-1","outcome":"ALLOW","comment":"verified","labels":["manual_ok"]}'
```

8. Inspect/replay DLQ:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8004/v1/dlq/events
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8004/v1/dlq/replay/<event_id>
```

## Failure and Recovery Behavior

- Service restart: consumers rejoin consumer groups and reclaim stale pending messages with `XAUTOCLAIM`.
- Duplicate events: suppressed by `consumer_dedup` and deterministic event IDs.
- Retry policy: failed events are re-published with incremented attempt count up to `MAX_RETRY_ATTEMPTS`.
- Dead-letter policy: exhausted events are published to `fraud.dlq.v1`.
- Auditability: every step output and decision action is append-only and replayable from `case_events`.

## Observability

- Prometheus metrics endpoint: `/metrics` on every service.
- Dashboard: `infra/grafana/dashboards/fraud_platform_overview.json`.
- Key metrics:
  - `stream_group_lag`
  - `agent_execution_duration_seconds`
  - `stream_retry_total`
  - `stream_dlq_total`

## Kubernetes

Apply manifests under `infra/k8s`.

>>> MANUAL STEP REQUIRED <<<

Before deploy, set real values in `infra/k8s/secrets.yaml` for:

- `POSTGRES_PASSWORD`
- `POSTGRES_DSN`

Run migrations before service deployments:

```bash
# example from CI runner or operator workstation:
# 1) create DB + Redis first
kubectl apply -f infra/k8s/namespaces.yaml
kubectl apply -f infra/k8s/configmaps.yaml
kubectl apply -f infra/k8s/secrets.yaml
kubectl apply -f infra/k8s/services/postgres.yaml
kubectl apply -f infra/k8s/deployments/postgres.yaml

# 2) run migrations against POSTGRES_DSN from secret
POSTGRES_DSN='postgresql://fraud:<password>@<postgres-host>:5432/fraud_platform' alembic upgrade head
```

Then apply:

```bash
kubectl apply -f infra/k8s/services
kubectl apply -f infra/k8s/deployments
kubectl apply -f infra/k8s/hpa
kubectl apply -f infra/k8s/pdb
```
