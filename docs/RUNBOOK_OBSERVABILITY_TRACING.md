# Runbook: Observability i Tracing

## Cel
Sledzenie pojedynczego case przez HTTP -> eventy -> decyzje.

## Co jest zbierane
1. `traceparent` i `X-Trace-Id` na HTTP.
2. `trace_id` i `traceparent` w `case_events`.
3. Spany OTel exportowane po OTLP HTTP do `otel-collector`, a dalej do `Tempo`.
4. Spany maja stale atrybuty `fraud.case_id`, `fraud.event_id`, `fraud.step`, `fraud.service`.
5. Metryki auth/rate-limit i metryki pipeline.

## Diagnoza case krok po kroku
1. Wez `case_id` z `/v1/cases`.
2. Pobierz timeline `/v1/cases/{case_id}/events`.
3. Sprawdz `trace_id` i `traceparent` miedzy eventami.
4. Otworz trace w Grafanie przez datasource `Tempo`.
5. Zweryfikuj decyzje `/v1/cases/{case_id}/decisions`.
6. Dla problemow write API sprawdz:
   1. `auth_rejected_total`
   2. `rate_limit_rejected_total`
   3. alerty Prometheusa dla `stream_group_lag`, `stream_retry_total`, `stream_dlq_total`

## Co oznacza niespojnosc trace
1. Brak trace context na ingress (brak naglowka i brak middleware).
2. Niewlasciwa propagacja przy budowie eventu.
3. Dane historyczne sprzed migracji trace columns.
4. Nieprawidlowy endpoint `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` lub niedostepny `otel-collector`.
