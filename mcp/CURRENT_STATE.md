# Current State (updated: 2026-02-16, post-P3 implementation pass)

Source of truth:
- Runtime code under `services/*`, `libs/shared/shared`.
- Infra under `docker-compose.yml` and `infra/k8s`.

Current platform status:
- Monorepo with multiple FastAPI services and shared platform library.
- Event-driven flow is active on Redis Streams (no direct service->orchestrator call).
- Durable storage is active on PostgreSQL with append-only audit tables.
- Orchestrator auto-processes `case.created` and drives agent command streams.
- Human Review is auto-wired for `REVIEW` recommendations via command stream.
- Retry + DLQ (`fraud.dlq.v1`) are implemented in shared stream worker.
- Dedicated `dlq-ops-api` consumes DLQ and exposes replay endpoints.
- Prometheus / Grafana observability is active.
- Write endpoints are protected with JWT scope validation.
- Write endpoints have in-memory rate limiting and rejection metrics.
- Trace context is propagated over HTTP (`traceparent`) and persisted in case events.
- Kubernetes manifests include rolling strategy, resource limits, HPA and PDB.
- Agent logic is versioned/configurable (model artifact, policy ruleset, explainer provider abstraction).

Main open gaps:
- Secret rotation and production-grade key management policy.
- External tracing backend wiring (collector/Jaeger/Tempo), currently console exporter baseline.
- Production rollout decisions for JWT issuer/audience and auth integration with enterprise IdP.
