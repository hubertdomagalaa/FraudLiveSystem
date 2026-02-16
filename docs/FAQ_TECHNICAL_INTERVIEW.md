# FAQ pod rozmowe techniczna

## 1) Dlaczego Redis Streams zamiast sync HTTP orchestration?
Bo daje trwaly backlog, consumer groups, replay i odpornosc na awarie bez utraty flow.

## 2) Jak zapewniona jest idempotencja?
1. Wejscie: `Idempotency-Key` mapowany trwale do case/transaction.
2. Konsumenci: `consumer_dedup` blokuje ponowne przetworzenie eventu.
3. Event IDs dla krokow sa deterministyczne.

## 3) Jak dziala human-in-the-loop?
`agent-aggregate` emituje rekomendacje, a orchestrator dla `REVIEW` routuje do `human-review-api`, gdzie czlowiek podejmuje finalna decyzje.

## 4) Co jest append-only?
`cases`, `case_events`, `agent_runs`, `decision_records`, `human_review_actions`, `consumer_dedup`.

## 5) Jak wyglada recovery po crashu konsumenta?
Consumer group + `XAUTOCLAIM` przejmuje pending messages, retry policy kieruje stale bledy do DLQ.

## 6) Co zrobiono pod security baseline?
1. JWT dla endpointow write.
2. Rate limiting endpointow write.
3. Metryki odrzuconych autoryzacji i rate-limit.

## 7) Jak monitorowac pipeline?
Prometheus + Grafana, metryki lag/retry/dlq/latency + endpointy timeline case.
