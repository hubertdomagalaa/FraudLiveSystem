# Raport stanu projektu - Fraud Decision Support Platform

## Data raportu
2026-02-16

## Zrodlo raportu
Raport przygotowany na podstawie aktualnego kodu:
- `services/*`
- `libs/shared/shared/*`
- `docker-compose.yml`
- `infra/k8s/*`

## Executive summary
Projekt jest na etapie production-ready MVP (wersja techniczna):
1. Ingestion zapisuje case w PostgreSQL i publikuje `case.created` do Redis Streams.
2. Decision Orchestrator steruje pipeline agentow przez komendy streamowe.
3. Agenci publikuja eventy `agent.*.completed` i zapisują `agent_runs`.
4. Dla rekomendacji `REVIEW` system automatycznie kieruje sprawe do human review.
5. Finalna decyzja czlowieka publikuje `case.human_review.completed` i zamyka case.
6. Endpointy write sa zabezpieczone JWT + scope.
7. Jest rate limiting write endpointow.
8. Tracing HTTP + trace context eventow jest zaimplementowany.
9. Jest dedykowany serwis `dlq-ops-api` do operacji DLQ/replay.

## Co dziala produkcyjnie w architekturze
1. Event backbone: Redis Streams + consumer groups + `XAUTOCLAIM`.
2. System of record: PostgreSQL, append-only audit trail.
3. Odpornosc: deduplikacja consumerow (`consumer_dedup`), retry, DLQ.
4. Observability: endpoint `/metrics`, Prometheus, Grafana.
5. Infra: lokalny stack docker-compose oraz manifesty K8s.

## Aktualny przeplyw case (realny)
1. `POST /v1/transactions` -> `ingestion-api`.
2. Insert do `cases` + event `case.created`.
3. Orchestrator konsumuje event i emituje kolejno komendy:
   1. `context`
   2. `risk`
   3. `policy`
   4. `explain`
   5. `aggregate`
4. Agenci zwracaja eventy completion do `fraud.case.events.v1`.
5. Orchestrator zapisuje `SYSTEM_RECOMMENDATION`.
6. Jesli `REVIEW`:
   1. emituje `case.human_review.required`,
   2. emituje komende do `fraud.human_review.cmd.v1`.
7. Human Review API zapisuje review request.
8. Recenzent wysyla finalna decyzje (`/v1/cases/{case_id}/decision`).
9. Human Review API emituje `case.human_review.completed`.
10. Orchestrator zapisuje decyzje `FINAL`.

## Otwarte luki (stan na dzis)
1. Integracja auth z docelowym IdP i polityka rotacji sekretow.
2. Podpiecie OTel do docelowego backendu trace (obecnie console exporter).
3. Dalsze dojrzewanie modeli domenowych i ewaluacja offline/online.
4. Operacyjne procedury rolloutu migracji na wielu srodowiskach.

## Status planu domkniecia
1. P0 - DONE
2. P1 - DONE
3. P2 - DONE
4. P3 - DONE
