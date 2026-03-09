# INTERVIEW CHECKLIST (Senior AI Engineer)

## 1. 60-second pitch

- Event-driven fraud decision support platform with Redis Streams orchestration.
- Append-only audit trail in PostgreSQL for full traceability.
- Human-in-the-loop for REVIEW, plus retry/DLQ/replay for operational resilience.
- UI supports transaction creation, pipeline visibility, and explainable decision view.

## 2. Co pokazaæ live

1. Create transaction from UI preset.
2. Pipeline status progression.
3. Why this decision? (signals, score, policy violations, explanation).
4. Manual review decision.
5. DLQ replay flow.

## 3. Pytania, na które musisz mieæ odpowiedŸ

- Dlaczego event-driven zamiast direct RPC?
- Jak dzia³a idempotencja ingestu?
- Jak gwarantujesz auditability i replayability?
- Jak oddzielasz recommendation od final decision w REVIEW?
- Jakie trade-offy ma ruleset + deterministic scoring?

## 4. Najwa¿niejsza narracja seniorska

- Priorytet: bezpieczeñstwo architektury i kompatybilnoœæ kontraktów eventowych.
- Ka¿da zmiana by³a addytywna i testowalna.
- Demo nie opiera siê na ukrytych trikach runtime, tylko na jawnych narzêdziach dev/demo.
