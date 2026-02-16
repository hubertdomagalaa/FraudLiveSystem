# Plan domkniecia projektu (dla Codex)

## Cel
Domknac projekt do stanu "production-ready MVP" zgodnie z zasadami:
1. Event-driven orchestration przez Redis Streams.
2. Append-only audit trail w PostgreSQL.
3. Human-in-the-loop jako finalna odpowiedzialnosc decyzyjna.

## Data odniesienia
Stan planu na: 2026-02-16.

## Tryb pracy Codex (wymagany)
1. Realizuj zadania od najwyzszego priorytetu (P0 -> P1 -> P2 -> P3).
2. Nie zaczynaj kolejnego zadania, dopoki poprzednie nie ma `DoD = DONE`.
3. Dla kazdego zadania wykonaj cykl:
   1. analiza kodu i dokumentacji,
   2. implementacja minimalnej zmiany pionowej,
   3. walidacja komendami,
   4. aktualizacja dokumentacji,
   5. wpis statusu do sekcji "Postep realizacji".
4. Nie lam zasad architektury z `mcp/ARCHITECTURE_RULES.md`.
5. Przy kazdym PR-like kroku podawaj: co zmieniono, ryzyko regresji, jak zweryfikowano.

## Priorytety i backlog

## P0 - Krytyczne do domkniecia

### P0.1 Ujednolicenie dokumentacji stanu
- Problem: `mcp/CURRENT_STATE.md` jest niezgodny z faktycznym kodem.
- Zakres:
  1. Zaktualizowac `mcp/CURRENT_STATE.md`.
  2. Zaktualizowac `docs/raport_stanu_projektu.md`.
  3. Dodac date aktualizacji i zrodlo stanu.
- DoD:
  1. Dokumenty nie przecza sobie i odzwierciedlaja dzialajacy event-driven flow.
  2. Jest jawna lista "otwartych brakow", nie "brak event broker".

### P0.2 Migracje bazy danych (zamiast runtime schema init)
- Problem: schema jest tworzona przez `ensure_schema()` przy starcie serwisu.
- Zakres:
  1. Dodac Alembic i pierwsza migracje inicjalna.
  2. Usunac odpowiedzialnosc tworzenia schematu ze startupu runtime.
  3. Dodac instrukcje migracji lokalnie i na K8s.
- DoD:
  1. `alembic upgrade head` buduje aktualny schemat.
  2. Serwisy startuja bez `ensure_schema()` i bez side-effectow DDL.
  3. README opisuje proces migracji.

### P0.3 Idempotencja na wejsciu ingestion
- Problem: losowy `transaction_id` utrudnia bezpieczny retry klienta.
- Zakres:
  1. Dodac idempotency key z requestu (np. naglowek `Idempotency-Key`).
  2. Utrwalic mapowanie idempotency key -> case/transaction.
  3. Zwracac ten sam wynik dla retry tego samego zgloszenia.
- DoD:
  1. Powtorzony request z tym samym kluczem nie tworzy nowego case.
  2. Event `case.created` nie jest duplikowany dla tego samego klucza.
  3. Sa testy integracyjne dla retry.

### P0.4 Testy i CI baseline
- Problem: brak realnych testow i brak pipeline CI.
- Zakres:
  1. Testy jednostkowe dla agentow i helperow eventow.
  2. Test integracyjny E2E: ingest -> orchestrator -> agents -> decision/human review.
  3. Minimalny pipeline CI (lint + test + compile).
- DoD:
  1. Testy uruchamiaja sie komenda jednego wejscia.
  2. CI odpala sie automatycznie na push/PR.
  3. Sa artefakty logow i jasny status pass/fail.

## P1 - Bezpieczenstwo i operacje

### P1.1 Security baseline API
- Zakres:
  1. AuthN/AuthZ (minimum JWT dla endpointow write).
  2. Rate limiting dla endpointow publicznych.
  3. Twarde walidacje payload i bezpieczne logowanie (bez wrazliwych danych).
- DoD:
  1. Endpointy write nie sa publicznie otwarte.
  2. Limit ruchu dziala i jest metryka odrzuconych zadan.

### P1.2 Observability+Tracing
- Zakres:
  1. Propagacja trace id/traceparent miedzy eventami i HTTP.
  2. OpenTelemetry exporter (minimum lokalny collector lub stdout).
  3. Dashboard + runbook diagnostyczny.
- DoD:
  1. Jeden case ma spojny trace przez wszystkie kroki.
  2. Mozna odtworzyc przyczyne bledu z trace i case_events.

### P1.3 K8s hardening
- Zakres:
  1. Resource requests/limits dla deploymentow.
  2. HPA dla krytycznych serwisow.
  3. PDB i strategy rollout.
- DoD:
  1. Manifests zawieraja limity i autoscaling.
  2. Deployment jest powtarzalny i bez recznego "gaszenia pozarow".

### P1.4 DLQ operations
- Zakres:
  1. Konsument DLQ (`cg.dlq.ops`) z API/replay tool.
  2. Procedura replay i quarantine.
  3. Alerty na wzrost DLQ.
- DoD:
  1. Da sie bezpiecznie replayowac event z DLQ.
  2. Jest runbook incydentu.

## P2 - Jakosc domenowa

### P2.1 Urealnienie agentow
- Zakres:
  1. Risk-ML: wersjonowane features + model artifact strategy.
  2. Policy: konfiguracja reguł poza kodem (versioned ruleset).
  3. Explainer: provider abstraction i fallback.
- DoD:
  1. Agenci nie sa "stub-only".
  2. Kazdy wynik ma versioning i deterministyczny audit context.

### P2.2 Contract tests miedzy serwisami
- Zakres:
  1. Testy kontraktow event payload.
  2. Kontrola kompatybilnosci wstecznej.
- DoD:
  1. Zmiana kontraktu bez aktualizacji testow blokuje CI.

## P3 - Final polish

### P3.1 Runbooki i onboarding
- Zakres:
  1. Incident response.
  2. Disaster recovery.
  3. FAQ pod rozmowe techniczna.
- DoD:
  1. Nowa osoba uruchamia system i rozumie przeplyw w < 60 min.

## Kolejnosc realizacji (rekomendowana)
1. P0.1 -> P0.2 -> P0.3 -> P0.4
2. P1.1 -> P1.2 -> P1.3 -> P1.4
3. P2.1 -> P2.2
4. P3.1

## Standard walidacji po kazdym kroku
1. `python -m compileall libs/shared/shared services`
2. Testy jednostkowe/integracyjne (po ich dodaniu): `pytest -q`
3. Smoke lokalny: `docker-compose up --build` + ingest przykadowej transakcji.
4. Weryfikacja timeline:
   1. `/v1/cases`
   2. `/v1/cases/{case_id}/events`
   3. `/v1/cases/{case_id}/decisions`

## Postep realizacji
- [x] P0.1 Ujednolicenie dokumentacji stanu
- [x] P0.2 Migracje bazy danych
- [x] P0.3 Idempotencja ingestion
- [x] P0.4 Testy i CI baseline
- [x] P1.1 Security baseline API
- [x] P1.2 Observability+Tracing
- [x] P1.3 K8s hardening
- [x] P1.4 DLQ operations
- [x] P2.1 Urealnienie agentow
- [x] P2.2 Contract tests
- [x] P3.1 Runbooki i onboarding
