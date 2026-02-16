# Kroki domkniecia projektu (backend -> gotowosc pod UI)

## Cel
Domknac backend do stabilnego production-ready MVP, a nastepnie przygotowac grunt pod budowe UI.

## Jak korzystac z tego dokumentu
1. Realizuj kroki po kolei.
2. Nie przechodz dalej, dopoki "Kryterium done" dla kroku nie jest spelnione.
3. Odhaczaj checklisty po wykonaniu.

## Etap 1 - Finalizacja repo i konfiguracji

### 1.1 Zweryfikuj aktualny stan kodu
- [ ] Sprawdz status zmian: `git status`
- [ ] Sprawdz plan: `docs/PLAN_DOMKNIECIA_PROJEKTU_CODEX.md`
- [ ] Potwierdz dokumentacje stanu:
  - `docs/raport_stanu_projektu.md`
  - `docs/STAN_PROJEKTU_I_FLOW_TECHNICZNY.md`

Kryterium done:
- Masz jasny obraz co jest juz zrobione i co jest "infra/operational follow-up".

### 1.2 Ustaw sekrety i polityke auth
- [ ] Ustaw realne wartosci dla:
  - `POSTGRES_DSN`
  - `POSTGRES_PASSWORD`
  - `JWT_SECRET`
- [ ] Ustaw docelowe parametry auth:
  - `AUTH_ENABLED=true`
  - `JWT_REQUIRED_SCOPE=fraud.write`
  - opcjonalnie issuer/audience przez ENV
- [ ] Przenies sekrety do managera sekretow (nie trzymaj finalnych wartosci w repo).

Kryterium done:
- Serwisy startuja na docelowych sekretach i odrzucaja write bez poprawnego JWT.

## Etap 2 - Walidacja backendu lokalnie

### 2.1 Instalacja i walidacja statyczna
- [ ] `pip install -r requirements-dev.txt`
- [ ] `pip install -e libs/shared`
- [ ] `ruff check libs/shared/shared services tests migrations`
- [ ] `python -m compileall libs/shared/shared services migrations tests`

Kryterium done:
- Brak bledow lint/compile.

### 2.2 Migracje bazy
- [ ] Uruchom PostgreSQL i Redis.
- [ ] Wykonaj migracje:
  - `POSTGRES_DSN=... alembic upgrade head`
- [ ] Zweryfikuj, ze migracje przechodza bez bledow.

Kryterium done:
- Schema jest postawiona przez Alembic, nie przez startup serwisow.

### 2.3 Testy automatyczne
- [ ] `PYTHONPATH=libs/shared pytest -q tests`
- [ ] Uruchom testy serwisowe analogicznie jak w CI (`.github/workflows/ci.yml`).

Kryterium done:
- Wszystkie testy przechodza.

## Etap 3 - Smoke E2E i operacje

### 3.1 End-to-end flow
- [ ] Uruchom stack (docker compose lub K8s dev).
- [ ] Wygeneruj JWT testowy.
- [ ] Wyslij ingest z `Idempotency-Key`.
- [ ] Sprawdz:
  - `/v1/cases`
  - `/v1/cases/{case_id}/events`
  - `/v1/cases/{case_id}/decisions`
- [ ] Dla przypadku REVIEW wykonaj manualna decyzje:
  - `POST /v1/cases/{case_id}/decision`

Kryterium done:
- Case przechodzi pelny flow od ingest do finalnej decyzji.

### 3.2 DLQ i replay
- [ ] Wymus awarie kroku (kontrolowany test).
- [ ] Sprawdz event w DLQ przez `dlq-ops-api`:
  - `GET /v1/dlq/events`
- [ ] Wykonaj replay:
  - `POST /v1/dlq/replay/{event_id}`
- [ ] Potwierdz, ze case rusza dalej.

Kryterium done:
- Operacyjnie umiesz odzyskac case z DLQ.

### 3.3 Monitoring i tracing
- [ ] Sprawdz dashboardy Grafana:
  - pipeline overview
  - security/trace
- [ ] Zweryfikuj metryki:
  - `stream_group_lag`
  - `stream_retry_total`
  - `stream_dlq_total`
  - `auth_rejected_total`
  - `rate_limit_rejected_total`
- [ ] Potwierdz obecny `traceparent` / `X-Trace-Id` w odpowiedziach HTTP.

Kryterium done:
- Mozesz diagnozowac problemy na podstawie metryk + trace context.

## Etap 4 - Wdrozenie i governance

### 4.1 Deploy K8s
- [ ] Apply:
  - `infra/k8s/namespaces.yaml`
  - `infra/k8s/configmaps.yaml`
  - `infra/k8s/secrets.yaml`
  - `infra/k8s/services`
  - `infra/k8s/deployments`
  - `infra/k8s/hpa`
  - `infra/k8s/pdb`
- [ ] Uruchom migracje na docelowym DB przed ruchem produkcyjnym.

Kryterium done:
- Serwisy dzialaja stabilnie po deployu, probe/readiness/liveness sa zielone.

### 4.2 CI i branch protection
- [ ] Wlacz wymagane checki CI na PR:
  - lint
  - compile
  - migrations dry-run
  - tests
- [ ] Wymus review przed merge.

Kryterium done:
- Regresja nie przechodzi do main bez czerwonych flag.

## Etap 5 - Formalne domkniecie backendu

- [ ] Uaktualnij changelog/release notes.
- [ ] Zatwierdz runbooki:
  - `docs/RUNBOOK_INCIDENT_RESPONSE.md`
  - `docs/RUNBOOK_DISASTER_RECOVERY.md`
  - `docs/RUNBOOK_DLQ_REPLAY.md`
  - `docs/RUNBOOK_OBSERVABILITY_TRACING.md`
- [ ] Potwierdz onboarding:
  - `docs/ONBOARDING_60_MIN.md`

Kryterium done:
- Backend uznany za domkniety technicznie i operacyjnie.

---

## Co dalej: etap UI (po domknieciu backendu)

Po zakonczeniu krokow powyzej zaczynamy UI:
1. Zdefiniowac user flows:
   - lista case'ow
   - szczegoly case + timeline eventow
   - panel human review
   - panel DLQ ops (readonly + replay action)
2. Uzgodnic kontrakty frontend-backend (endpointy, pola, paginacja, filtry).
3. Wybrac stack UI (np. React + TypeScript + TanStack Query + charting).
4. Zrobic MVP UI:
   - Case List
   - Case Details
   - Review Action Form
   - Ops Dashboard view
5. Dodac auth do UI (token handling + role-based pages).

Kryterium startu UI:
- Backend smoke i operacje DLQ/recovery sa potwierdzone.
