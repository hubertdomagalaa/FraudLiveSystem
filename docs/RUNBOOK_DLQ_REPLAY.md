# Runbook: DLQ Replay

## Cel
Bezpiecznie ponowic przetwarzanie eventu, ktory trafil do `fraud.dlq.v1`.

## Krok po kroku
1. Pobierz liste DLQ:
   1. `GET /v1/dlq/events?limit=100`
2. Wybierz `event_id` i zweryfikuj:
   1. `payload.error`
   2. `payload.source_stream`
   3. `payload.failed_event`
3. Napraw przyczyne bledu (kod/config/infra).
4. Uruchom replay:
   1. `POST /v1/dlq/replay/{event_id}`
5. Potwierdz:
   1. event wraca na `source_stream`,
   2. case przechodzi dalej w pipeline,
   3. brak ponownego wzrostu DLQ dla tej samej przyczyny.

## Zasady bezpieczenstwa
1. Replay tylko po usunieciu przyczyny bledu.
2. Dla masowych replay wykonywac batchami i monitorowac lag.
3. Wszystkie operacje replay wymagaja JWT scope `fraud.write`.
