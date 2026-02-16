# Onboarding 60 minut

## 0-10 min
1. Przeczytaj `README.md`.
2. Przeczytaj `docs/STAN_PROJEKTU_I_FLOW_TECHNICZNY.md`.

## 10-25 min
1. Przejdz `services/ingestion-api/app/api/routes/transactions.py`.
2. Przejdz `services/decision-orchestrator/app/orchestration/worker.py`.

## 25-40 min
1. Przejdz jeden pelny agent: `stream_worker.py` + `services/agent.py`.
2. Przejdz `libs/shared/shared/worker.py`, `events.py`, `database.py`.

## 40-50 min
1. Przejdz `services/human-review-api/app/api/routes/reviews.py`.
2. Przejdz `services/dlq-ops-api/app/api/routes/dlq.py`.

## 50-60 min
1. Uruchom stack i wykonaj:
   1. ingest transakcji,
   2. odczyt timeline,
   3. decyzja manualna (gdy `REVIEW`),
   4. podglad DLQ.

## Efekt
Po 60 minutach nowa osoba rozumie:
1. architekture event-driven,
2. append-only audit model,
3. flow human-in-the-loop,
4. operacyjne replay i recovery.
