# Runbook: Observability i Tracing

## Cel
Sledzenie pojedynczego case przez HTTP -> eventy -> decyzje.

## Co jest zbierane
1. `traceparent` i `X-Trace-Id` na HTTP.
2. `trace_id` i `traceparent` w `case_events`.
3. Spany OTel exportowane do stdout (ConsoleSpanExporter).
4. Metryki auth/rate-limit i metryki pipeline.

## Diagnoza case krok po kroku
1. Wez `case_id` z `/v1/cases`.
2. Pobierz timeline `/v1/cases/{case_id}/events`.
3. Sprawdz `trace_id` i `traceparent` miedzy eventami.
4. Zweryfikuj decyzje `/v1/cases/{case_id}/decisions`.
5. Dla problemow write API sprawdz:
   1. `auth_rejected_total`
   2. `rate_limit_rejected_total`

## Co oznacza niespojnosc trace
1. Brak trace context na ingress (brak naglowka i brak middleware).
2. Niewlasciwa propagacja przy budowie eventu.
3. Dane historyczne sprzed migracji trace columns.
