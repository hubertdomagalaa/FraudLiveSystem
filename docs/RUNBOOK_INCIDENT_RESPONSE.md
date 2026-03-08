# Runbook: Incident Response

## Cel
Szybko wykryc, odizolowac i usunac problem bez utraty audytu case'ow.

## Szybki triage (5-10 min)
1. Sprawdz `/health` i `/metrics` dla:
   1. `ingestion-api`
   2. `decision-orchestrator`
   3. `human-review-api`
   4. `dlq-ops-api`
2. Sprawdz metryki:
   1. `stream_group_lag`
   2. `stream_retry_total`
   3. `stream_dlq_total`
   4. `rate_limit_rejected_total`
   5. `auth_rejected_total`
3. Zweryfikuj, czy nowe case'y trafiaja do `/v1/cases`.

## Typowe scenariusze

## 1) Rosnacy lag consumer group
1. Sprawdz obciazenie CPU/RAM podow.
2. Skaluj deployment (HPA lub recznie).
3. Zweryfikuj `XAUTOCLAIM` i PEL.
4. Potwierdz spadek lag po 5-10 min.

## 2) Rosnacy DLQ
1. Pobierz eventy DLQ: `GET /v1/dlq/events`.
2. Wyodrebnij najczestszy error z `payload.error`.
3. Napraw przyczyne w serwisie zrodlowym.
4. Replay przez `POST /v1/dlq/replay/{event_id}`.
5. Potwierdz finalizacje case po replay.

## 3) Auth failures po deploy
1. Zweryfikuj aktywny tryb auth:
   - local/static secret: `JWT_SECRET`
   - production/IdP: `JWT_JWKS_URL` + `JWT_ISSUER` + `JWT_AUDIENCE`
2. Potwierdz zgodnosc `JWT_ALGORITHM` z trybem auth (`HS*` dla secret, `RS*` dla JWKS).
3. Potwierdz zgodnosc tokena z `JWT_REQUIRED_SCOPE`.
4. Sprawdz `auth_rejected_total` wg powodow (`invalid_issuer`, `invalid_audience`, `jwks_unavailable`, `missing_scope`).

## Kryterium zamkniecia incydentu
1. Lag wraca do baseline.
2. DLQ przestaje rosnac.
3. Nowe case przechodza caly flow.
4. Incydent ma wpis w changelogu operacyjnym.
