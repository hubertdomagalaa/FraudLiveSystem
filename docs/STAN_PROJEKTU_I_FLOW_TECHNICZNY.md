# Stan projektu i flow techniczny (material do nauki)

## O co chodzi w tym projekcie
To backendowa platforma decision support dla fraudu transakcji kartowych.
Najwazniejsze zalozenie biznesowe:
1. AI wspiera decyzje.
2. AI nie podejmuje finalnej decyzji bezwarunkowo.
3. Czlowiek jest wlascicielem finalnej odpowiedzialnosci dla przypadkow `REVIEW`.

System jest zaprojektowany jako:
1. Event-driven.
2. Audit-first.
3. Crash-safe.
4. Deterministyczny per case.

## Aktualny stan (2026-02-16)
## Co juz dziala
1. Ingestion zapisuje `case` do PostgreSQL i publikuje `case.created` do Redis Streams.
2. Decision Orchestrator konsumuje eventy i uruchamia kolejne kroki przez komendy streamowe.
3. Agenci (`context`, `risk`, `policy`, `explain`, `aggregate`) dzialaja jako konsumenci streamow.
4. Human Review API automatycznie dostaje komende dla case'ow wymagajacych review.
5. Audit trail jest append-only (`cases`, `case_events`, `agent_runs`, `decision_records`, `human_review_actions`, `consumer_dedup`).
6. Retry + DLQ sa zaimplementowane na poziomie wspolnego worker-a.
7. Metryki Prometheus i dashboard Grafana sa dostepne.
8. Ingestion wspiera request-level idempotency przez naglowek `Idempotency-Key`.
9. Jest baseline migracji DB przez Alembic (`alembic upgrade head`).
10. Docker Compose i podstawowe manifesty K8s istnieja.
11. Endpointy write sa zabezpieczone JWT + scope.
12. Endpointy write maja rate limiting i metryki odrzucen.
13. Trace context (`traceparent`, `X-Trace-Id`) jest propagowany i zapisywany w `case_events`.
14. Istnieje `dlq-ops-api` do podgladu i replay eventow DLQ.
15. Manifesty K8s maja resource limits, strategy, HPA i PDB.

## Co jest jeszcze otwarte
1. Dokumenty stanu sa miejscami niespojne (czesc opisow jest starsza od kodu).
2. Brak integracji auth z docelowym IdP i rotacja kluczy.
3. OTel jest na poziomie baseline (stdout), bez centralnego backendu trace.
4. Agenci sa nadal uproszczeni wzgledem pelnej logiki produkcyjnej.

## Komponenty i odpowiedzialnosci
1. `ingestion-api`
   1. Przyjmuje transakcje.
   2. Tworzy case.
   3. Emisja `case.created`.
2. `decision-orchestrator`
   1. Steruje pipeline eventami.
   2. Zapisuje decyzje systemowe/finalne.
   3. Kieruje do human review przy `REVIEW`.
3. `agent-context`
   1. Buduje sygnaly kontekstowe z metadanych transakcji.
4. `agent-risk-ml`
   1. Liczy score ryzyka.
5. `agent-policy`
   1. Zamienia sygnaly na akcje polityk (`ALLOW`, `REVIEW`, `BLOCK`).
6. `agent-llm-explainer`
   1. Tworzy uzasadnienie decyzji.
7. `agent-aggregate`
   1. Agreguje wyniki i buduje rekomendacje.
8. `human-review-api`
   1. Tworzy kolejke review.
   2. Przyjmuje finalna decyzje reczna i publikuje `case.human_review.completed`.
9. `dlq-ops-api`
   1. Konsumuje `fraud.dlq.v1`.
   2. Udostepnia API do podgladu i replay DLQ eventow.
10. `libs/shared`
   1. Kontrakty eventow i schematow.
   2. Wspolny worker streamowy.
   3. Wspolna observability i logging.
   4. Wspolna warstwa DB.

## Jak system dziala krok po kroku
1. Klient wysyla `POST /v1/transactions` do `ingestion-api`.
2. `ingestion-api` zapisuje case w `cases` i event `case.created` w `case_events`.
3. `ingestion-api` publikuje `case.created` na `fraud.case.events.v1`.
4. `decision-orchestrator` konsumuje `case.created`.
5. Orchestrator publikuje `step.run.requested` dla kroku `context` na `fraud.agent.context.cmd.v1`.
6. `agent-context` konsumuje komende, liczy wynik, zapisuje `agent_runs`, publikuje `agent.context.completed` do `fraud.case.events.v1`.
7. Orchestrator po `agent.context.completed` publikuje komende `risk`.
8. `agent-risk-ml` publikuje `agent.risk.completed`.
9. Orchestrator publikuje komende `policy`.
10. `agent-policy` publikuje `agent.policy.completed`.
11. Orchestrator publikuje komende `explain`.
12. `agent-llm-explainer` publikuje `agent.explain.completed`.
13. Orchestrator publikuje komende `aggregate`.
14. `agent-aggregate` publikuje `agent.aggregate.completed` z rekomendacja.
15. Orchestrator zapisuje `SYSTEM_RECOMMENDATION` w `decision_records`.
16. Jesli rekomendacja != `REVIEW`, orchestrator publikuje `case.finalized` i zapisuje final.
17. Jesli rekomendacja == `REVIEW`, orchestrator publikuje `case.human_review.required` i komende do `fraud.human_review.cmd.v1`.
18. `human-review-api` zapisuje `REVIEW_REQUESTED` w `human_review_actions`.
19. Recenzent wysyla finalna decyzje przez `POST /v1/cases/{case_id}/decision`.
20. `human-review-api` zapisuje akcje + `HUMAN_REVIEW` decision i publikuje `case.human_review.completed`.
21. Orchestrator konsumuje `case.human_review.completed` i zapisuje finalna decyzje `FINAL`.

## Co powiedziec na rozmowie technicznej (skrot)
1. "To event-driven fraud decision support, nie monolit RPC."
2. "Kazdy case jest audytowalny end-to-end przez append-only events i decision records."
3. "Orchestrator jest deterministyczny i steruje przeplywem krokow przez komendy streamowe."
4. "Mamy retry, idempotencje konsumenta i DLQ, wiec system jest odporny na awarie i duplikaty eventow."
5. "Human-in-the-loop jest wymuszony dla przypadkow REVIEW."
6. "Najwieksze remaining work to migracje DB, testy/CI, security i operacyjny hardening."

## Szybka sciezka nauki (60 minut)
1. 10 min: przeczytaj `README.md` i ten dokument.
2. 15 min: przejdz kod `ingestion-api` i `decision-orchestrator`.
3. 15 min: przejdz worker jednego agenta + `shared/worker.py`.
4. 10 min: przejdz flow human review.
5. 10 min: odpal lokalnie i przejdz timeline case przez endpointy `/v1/cases/...`.
