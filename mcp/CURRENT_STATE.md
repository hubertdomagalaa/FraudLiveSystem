# Current State (updated: 2026-03-06, backend + UI MVP pass)

Source of truth:
- Runtime code under `services/*`, `libs/shared/shared`, `ui/*`.
- Infra under `docker-compose.yml` and `infra/k8s`.

Current platform status:
- Monorepo with multiple FastAPI services, shared platform library and a React/TypeScript UI console.
- Event-driven flow is active on Redis Streams (no direct service->orchestrator call).
- Durable storage is active on PostgreSQL with append-only audit tables.
- Orchestrator auto-processes `case.created` and drives agent command streams.
- Human Review is auto-wired for `REVIEW` recommendations via command stream.
- Retry + DLQ (`fraud.dlq.v1`) are implemented in shared stream worker.
- Dedicated `dlq-ops-api` consumes DLQ and exposes replay endpoints.
- Prometheus / Grafana observability is active.
- Write endpoints are protected with JWT scope validation.
- Auth layer supports enterprise JWT validation via issuer/audience + JWKS or local static secret mode.
- Write endpoints have in-memory rate limiting and rejection metrics.
- Trace context is propagated over HTTP (`traceparent`) and persisted in case events.
- OTLP tracing is wired through `otel-collector` to `tempo` with Grafana datasource and Prometheus alert rules.
- Backend APIs expose CORS for configured UI origins.
- UI MVP supports case list/details, timeline, manual review and DLQ replay operations.
- Kubernetes manifests include rolling strategy, resource limits, HPA and PDB.
- Agent logic is versioned/configurable (model artifact, policy ruleset, explainer provider abstraction).

Validated locally in this environment:
- Python lint, compile, shared tests and service tests.
- Backend E2E tests for ALLOW / REVIEW / BLOCK / retry -> DLQ -> replay.
- UI `npm test` and `npm run build`.

Main open gaps:
- Production rollout still requires sizing/retention decisions for the OTEL Collector + Tempo trace stack.
- Production rollout still requires real IdP values and secret-manager backed environment injection.
- Full docker-compose smoke could not be executed here because Docker is unavailable in the current environment.
