# Fraud Decision Support Platform

This repository contains the initial production-grade setup for a Fraud Decision Support Platform. It is a monorepo with multiple FastAPI services, shared libraries, and infrastructure scaffolding.

## Architecture
- Ingestion API: validates and stores transactions, emits transaction events
- Decision Orchestrator: state-machine pipeline calling agents sequentially
- Agent Services:
  - Context Agent
  - Risk ML Agent (placeholder model)
  - LLM Explanation Agent (provider-agnostic, structured output)
  - Policy Agent (rule-based)
- Human Review API: receives cases requiring manual review and records auditable outcomes
- Shared Libraries: schemas, logging, configuration, observability
- Infrastructure: Docker Compose, Kubernetes manifests, Prometheus, Grafana

## Decision Pipeline
1. A transaction is posted to the Ingestion API.
2. The transaction is stored and a transaction event is published to the queue.
3. The Decision Orchestrator runs a state-machine pipeline and calls agents in order.
4. Agent outputs are persisted and aggregated into a final decision.
5. Decisions requiring manual review are sent to the Human Review API.
6. Review outcomes are stored with an append-only audit trail.

## Local Development
- Requirements: Docker Desktop or compatible Docker engine
- Start all services:
  - `docker-compose up --build`
- Key endpoints:
  - Ingestion API: `http://localhost:8001`
  - Decision Orchestrator: `http://localhost:8002`
  - Human Review API: `http://localhost:8003`
  - Grafana: `http://localhost:3000`
  - Prometheus: `http://localhost:9090`

## Configuration
All services read configuration from environment variables. Examples are provided in `docker-compose.yml`. Shared settings live in `libs/shared/shared/config.py`.

## Observability
Each service exposes a Prometheus-compatible `/metrics` endpoint. Prometheus and Grafana are wired for local use with placeholder dashboards.

## Expansion Points
- Replace in-memory repositories with durable storage (PostgreSQL, Cassandra, etc.)
- Implement a real queue backend (Kafka, NATS, SQS, etc.)
- Swap placeholder ML scoring with a production model service
- Add authentication, authorization, rate limiting, and tracing
