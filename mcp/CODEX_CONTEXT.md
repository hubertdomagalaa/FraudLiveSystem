# Project Context — Fraud Decision Support Platform

## High-level goal
Build a **production-grade, live AI Decision Support Platform** for reviewing potentially fraudulent card transactions.

This is NOT:
- a demo
- a notebook project
- a single-model ML app
- a chatbot

This IS:
- a real-world, enterprise-style decision system
- human-in-the-loop by design
- audit-first and explainability-first
- infrastructure-driven, not model-driven

The system must look and behave like an internal platform used by a bank or fintech.

---

## Core business problem
Financial institutions must review suspicious transactions without:
- blocking legitimate users
- missing real fraud
- blindly trusting AI

Therefore:
- AI never makes final decisions
- AI provides **risk signals, explanations, and recommendations**
- A human reviewer is always accountable for the final action

---

## Architectural principles (VERY IMPORTANT)
- Every transaction is treated as a **case**
- Each case goes through a **deterministic decision pipeline**
- Each step is:
  - isolated
  - observable
  - auditable
- No component has global knowledge of the system
- No data is overwritten (append-only event style)

---

## Decision pipeline overview

1. Transaction ingestion
2. Context enrichment
3. Risk scoring (classical ML)
4. LLM-based explanation (structured output)
5. Policy rule evaluation
6. Decision aggregation
7. Human review (if required)
8. Audit & feedback loop

---

## Agent philosophy
Agents are NOT autonomous entities.

An agent:
- performs exactly one responsibility
- has a strict input/output contract
- produces structured output
- logs its execution metadata (latency, version, errors)

Agents must be deterministic where possible.

---

## Technology direction
Backend:
- Python
- FastAPI
- Pydantic v2
- Async-first

Infrastructure:
- Docker (multi-service)
- docker-compose for local dev
- Kubernetes-ready (manifests required)
- Cloud-agnostic (AWS friendly)

Data:
- PostgreSQL (primary store)
- Redis (queue / caching)
- Append-only event tables

Observability:
- Prometheus
- Grafana
- Structured logging

---

## Non-goals (do NOT implement yet)
- No real fraud models
- No real payment integrations
- No production credentials
- No UI styling polish

Focus on:
- correctness
- clarity
- production structure

---

## Audience
This project is designed to be:
- reviewed by technical recruiters
- understood by non-technical stakeholders
- discussed in senior-level interviews

Clarity, structure, and reasoning matter more than feature completeness.
