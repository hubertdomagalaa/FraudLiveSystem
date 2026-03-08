# Master Summary - Fraud Decision Support Platform

## Cel dokumentu
Ten dokument zbiera w jednym miejscu najwazniejsze informacje z:
- `README.md`
- `mcp/CURRENT_STATE.md`
- `docs/raport_stanu_projektu.md`
- `docs/ONBOARDING_60_MIN.md`
- `docs/KROKI_DOMKNIECIA_PROJEKTU.md`

Jego cel jest podwojny:
1. przygotowanie do pracy operacyjnej nad projektem,
2. przygotowanie do technicznego interview, na ktorym trzeba obronic architekture, decyzje techniczne i poziom seniorski.

## 1. Executive Summary
Projekt to event-driven Fraud Decision Support Platform z human-in-the-loop.

Najwazniejsze cechy systemu:
- backend jest oparty o FastAPI,
- komunikacja wewnetrzna odbywa sie przez Redis Streams,
- PostgreSQL jest systemem rekordowym i trzyma append-only audit trail,
- orchestration jest realizowane przez dedykowany `decision-orchestrator`,
- rekomendacje `REVIEW` sa konczone przez czlowieka, nie przez automat,
- sa zaimplementowane retry, DLQ i replay,
- jest observability przez Prometheus + Grafana + OTEL Collector + Tempo,
- write endpointy sa chronione JWT + scope,
- istnieje UI MVP dla fraud operations.

To nie jest juz proof-of-concept. To jest production-ready MVP backendu z dzialajacym UI operacyjnym, z jednym glownym brakujacym krokiem operacyjnym: koncowy smoke `docker compose` w srodowisku z dostepnym Dockerem.

## 2. Problem biznesowy
System wspiera decyzje fraudowe dla pojedynczego przypadku transakcji.

W praktyce znaczy to:
- przyjmujemy transakcje,
- budujemy case,
- uruchamiamy pipeline agentow analitycznych,
- agregujemy wynik,
- jesli wynik jest niejednoznaczny, eskalujemy do czlowieka,
- zapisujemy caly przebieg jako audytowalny timeline,
- dajemy mozliwosc odzyskiwania bledow przez DLQ replay.

To jest kluczowa wartosc architektury: system nie tylko daje decyzje, ale daje tez odpornosc, audytowalnosc i kontrolowalnosc operacyjna.

## 3. Architektura systemu

### 3.1 Glowne komponenty
- `ingestion-api`
- `decision-orchestrator`
- `agent-context`
- `agent-risk-ml`
- `agent-policy`
- `agent-llm-explainer`
- `agent-aggregate`
- `human-review-api`
- `dlq-ops-api`
- `ui`

### 3.2 Zasada architektoniczna
Najwazniejsza regula architektury:
- nie ma direct service-to-orchestrator RPC,
- orchestracja odbywa sie tylko przez eventy i streamy.

To jest bardzo wazne na interview, bo pokazuje:
- loose coupling,
- odpornosc na awarie,
- mozliwosc retry i replay,
- czytelny audit trail,
- latwiejsze skalowanie niezaleznych workerow.

### 3.3 Backbone eventowy
Glowne streamy:
- `fraud.case.events.v1`
- `fraud.agent.context.cmd.v1`
- `fraud.agent.risk.cmd.v1`
- `fraud.agent.policy.cmd.v1`
- `fraud.agent.explain.cmd.v1`
- `fraud.agent.aggregate.cmd.v1`
- `fraud.human_review.cmd.v1`
- `fraud.dlq.v1`

### 3.4 Model danych
Append-only audit trail obejmuje:
- `cases`
- `case_events`
- `agent_runs`
- `decision_records`
- `human_review_actions`
- `consumer_dedup`

Senior-level uzasadnienie:
- append-only upraszcza audyt i forensic analysis,
- mozna odtworzyc timeline bez zgadywania,
- replay jest bezpieczniejszy,
- latwiej obronic zgodnosc procesowa i traceability decyzji.

## 4. Realny flow jednego case
1. Uzytkownik lub system zewnetrzny wywoluje `POST /v1/transactions`.
2. `ingestion-api` zapisuje case do PostgreSQL.
3. `ingestion-api` publikuje `case.created` do `fraud.case.events.v1`.
4. `decision-orchestrator` odbiera event i wysyla krok po kroku komendy do agentow.
5. Kazdy agent publikuje event completion.
6. Orchestrator zbiera wyniki i zapisuje `SYSTEM_RECOMMENDATION`.
7. Jezeli wynik to `ALLOW` albo `BLOCK`, orchestrator finalizuje case.
8. Jezeli wynik to `REVIEW`, orchestrator publikuje `case.human_review.required` i uruchamia human review flow.
9. `human-review-api` zapisuje akcje review i przyjmuje finalna decyzje recenzenta.
10. Orchestrator zapisuje `FINAL` decision.
11. UI odczytuje timeline, decyzje, agent runs i ewentualne eventy DLQ.

## 5. Security

### 5.1 Auth
Write endpointy sa chronione przez JWT.
System wspiera dwa tryby:
- `JWT_SECRET` dla local/dev,
- `JWT_JWKS_URL` + `JWT_ISSUER` + `JWT_AUDIENCE` dla produkcji.

To jest wazne, bo pokazuje dojrzalosc systemu:
- dev mode jest prosty lokalnie,
- prod mode wspiera integracje z prawdziwym IdP,
- jest scope-based authorization (`fraud.write`).

### 5.2 Dodatkowe zabezpieczenia
- rate limiting dla write endpointow,
- rejection metrics (`auth_rejected_total`, `rate_limit_rejected_total`),
- jawne rozroznienie bledow auth,
- CORS ograniczony do skonfigurowanych originow.

### 5.3 Co trzeba umiec obronic na interview
- dlaczego JWT scope jest lepszy niz samo sprawdzenie obecnosci tokena,
- po co issuer/audience,
- po co JWKS i key rotation,
- dlaczego CORS nie jest mechanizmem auth, tylko ograniczeniem przegladarkowym,
- dlaczego sekretow nie trzymamy finalnie w repo.

## 6. Reliability i recovery

### 6.1 Idempotencja
`ingestion-api` wymaga `Idempotency-Key`.
To chroni przed duplikacja case przy retry klienta.

### 6.2 Retry i DLQ
Wspolny worker obsluguje:
- retry z rosnacym `attempt`,
- odlozenie do `fraud.dlq.v1` po wyczerpaniu limitu,
- replay eventow przez `dlq-ops-api`.

### 6.3 Consumer recovery
Workerzy korzystaja z mechanizmow streamowych typu `XAUTOCLAIM`, wiec po restarcie moga przejmowac stare pending messages.

### 6.4 Co trzeba umiec obronic na interview
- roznica miedzy retry a replay,
- czym jest DLQ i po co jest oddzielny interfejs ops,
- dlaczego deduplikacja konsumenta jest potrzebna nawet przy event-driven pipeline,
- jak projekt minimalizuje skutki at-least-once delivery.

## 7. Observability

### 7.1 Metrics
Kazdy serwis ma `/metrics`.
Kluczowe metryki:
- `stream_group_lag`
- `agent_execution_duration_seconds`
- `stream_retry_total`
- `stream_dlq_total`
- `auth_rejected_total`
- `rate_limit_rejected_total`

### 7.2 Tracing
Traces sa wysylane przez OTLP HTTP do `otel-collector`, a potem do `tempo`.

Wazne atrybuty spanow:
- `fraud.case_id`
- `fraud.event_id`
- `fraud.step`
- `fraud.service`

### 7.3 Dlaczego to jest seniorskie
- nie ogranicza sie do logow,
- pozwala diagnozowac problemy przekrojowo po `case_id` i `trace_id`,
- spina HTTP i event processing w jeden obraz operacyjny.

## 8. UI MVP
UI jest zbudowane w:
- React
- TypeScript
- Vite
- Vitest
- Testing Library

Funkcje UI:
- lista spraw,
- szczegoly case,
- timeline eventow,
- panel decyzji,
- manual review form,
- panel DLQ z replay,
- loading states,
- error states.

To nie jest marketingowy frontend. To jest operacyjna konsola fraudowa.

Na interview warto podkreslac:
- UI nie obchodzi architektury eventowej, tylko korzysta z API read/write,
- CORS zostal domkniety celowo pod bezpieczne originy,
- UI sluzy do operacji manual review i recovery, a nie tylko do dashboardingu.

## 9. Co zostalo zwalidowane
Lokalnie przeszly:
- `ruff check libs/shared/shared services tests`
- `python -m compileall libs/shared/shared services migrations tests`
- `PYTHONPATH=libs/shared pytest -q -p no:cacheprovider tests`
- testy serwisowe w modelu zgodnym z `.github/workflows/ci.yml`
- `ui`: `npm test`
- `ui`: `npm run build`

Przeszly tez scenariusze backendowe E2E:
- `ALLOW`
- `REVIEW` -> decyzja czlowieka -> finalizacja
- `BLOCK`
- retry -> DLQ -> replay -> recovery

## 10. Co jeszcze zostalo do formalnego zamkniecia
Technicznie w kodzie projekt jest domkniety do poziomu MVP production-ready.
Operacyjnie zostaly:
1. koncowy smoke `docker compose`,
2. podstawienie realnych wartosci IdP i secret management dla produkcji,
3. sizing/retention dla OTEL Collector + Tempo.

## 11. Czego musisz sie nauczyc przed praca z Dockerem w tym projekcie
To jest lista zagadnien, ktore powinienes rozumiec, zanim odpalisz lokalny smoke albo zaczniesz bronienie deployu.

### 11.1 Podstawy kontenerow
- czym jest obraz (`image`),
- czym jest kontener,
- roznica miedzy build-time i run-time,
- czym sa warstwy obrazu,
- po co jest `Dockerfile`.

### 11.2 Docker Compose
- czym jest `docker-compose.yml`,
- jak dzialaja `services`, `ports`, `environment`, `depends_on`, `volumes`,
- kiedy uzywac `docker compose up`, `up --build`, `down`, `logs`, `ps`,
- jak czytac zaleznosci miedzy serwisami w compose.

### 11.3 Siec i porty
- roznica miedzy portem kontenera a portem hosta,
- co znaczy mapowanie `8001:8000`,
- jak serwisy w compose komunikuja sie po nazwach (`postgres`, `redis`, `otel-collector`),
- dlaczego z hosta laczysz sie przez `localhost`, a z kontenera przez nazwe serwisu.

### 11.4 Volumes i dane trwale
- po co jest volume dla Postgresa,
- co sie stanie po restarcie bez volume,
- kiedy dane zostaja w systemie po `docker compose down`,
- kiedy trzeba czyscic volume, a kiedy nie wolno.

### 11.5 Zmienne srodowiskowe
- jak `environment` trafia do serwisu,
- jak dziala konfiguracja typu `POSTGRES_DSN`, `REDIS_URL`, `JWT_SECRET`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`,
- dlaczego dev secret moze byc w compose, ale produkcyjny sekret nie.

### 11.6 Health i start order
- co realnie daje `depends_on`,
- dlaczego `depends_on` nie oznacza, ze Postgres jest juz gotowy na polaczenie,
- czemu migracje sa osobnym krokiem i nie powinny byc ukryte w magicznym startupie.

### 11.7 Debugowanie kontenerow
- `docker compose logs -f <service>`,
- `docker compose ps`,
- `docker exec -it <container> sh` lub odpowiednik,
- jak sprawdzac env i polaczenia wewnatrz kontenera,
- jak odroznic problem aplikacji od problemu infra.

### 11.8 Docker a ten projekt
Musisz rozumiec, jak w praktyce uruchamiaja sie te grupy komponentow:
- data plane: `postgres`, `redis`,
- app plane: wszystkie FastAPI services,
- ops/observability plane: `prometheus`, `grafana`, `otel-collector`, `tempo`,
- presentation plane: `ui`.

### 11.9 Minimalny poziom zrozumienia, zanim odpalisz smoke
Powinienes umiec odpowiedziec:
- skad `ingestion-api` bierze DSN do bazy,
- jak `decision-orchestrator` laczy sie z Redis,
- gdzie trafia trace po wygenerowaniu przez serwis,
- jak UI znajduje backend,
- co oznacza blad CORS,
- co oznacza blad `connection refused`,
- co oznacza, ze kontener jest `running`, ale usluga jeszcze nie jest gotowa.

## 12. Kolejnosc nauki przed praktycznym Docker smoke
1. Docker basics: image, container, Dockerfile.
2. Docker Compose: services, ports, env, volumes, logs.
3. Networking w compose.
4. Postgres + Redis w kontenerach.
5. Zmienne srodowiskowe projektu.
6. Migracje bazy (`alembic upgrade head`).
7. Logi i debugowanie serwisow.
8. Observability stack: Prometheus, Grafana, OTEL Collector, Tempo.
9. Smoke flow projektu krok po kroku.

## 13. Jak bronic projekt na interview senior-level
Nie opowiadaj tylko, co jest w repo. Tlumacz decyzje.

### 13.1 Co warto podkreslac
- architektura jest event-driven, bo potrzebujemy odpornosci i auditability,
- append-only audit trail ulatwia traceability i forensic analysis,
- human-in-the-loop nie jest dodatkiem, tylko requirementem biznesowym,
- retry + DLQ + replay to cecha operacyjna, nie tylko implementacyjna,
- tracing i metrics sa zaprojektowane pod diagnozowanie pipeline, nie tylko pod "ladne dashboardy",
- UI obsluguje use cases operacyjne, a nie tylko prezentacje danych.

### 13.2 Pytania, ktore prawdopodobnie padna
- dlaczego Redis Streams, a nie synchroniczne wywolania miedzy serwisami,
- jak zapewniasz idempotencje,
- jak radzisz sobie z at-least-once delivery,
- jak odtwarzasz historie decyzji,
- gdzie sa granice odpowiedzialnosci orchestratora,
- dlaczego finalna decyzja w `REVIEW` nalezy do czlowieka,
- jak diagnozujesz opoznienia pipeline,
- jak bronisz wyboru append-only modelu,
- jak przechodzisz z dev secret do enterprise IdP,
- jak bys rozwinal ten system na multi-tenant production.

### 13.3 Jak odpowiadac po seniorsku
- zaczynaj od wymagania biznesowego,
- potem pokaz trade-off,
- potem uzasadnij decyzje architektoniczna,
- na koncu powiedz, jakie ryzyko zostalo i jak bys je kontrolowal.

Przyklad:
"Wybralem event-driven orchestration zamiast bezposrednich RPC, bo w tym systemie wazniejsze od minimalnego latency bylo auditability, retryability i recovery po awarii. Trade-off to wieksza zlozonosc operacyjna, dlatego dolozylem DLQ, replay, tracing i metryki lag/retry."

## 14. Plan przygotowania do interview
### Dzien 1
- przeczytaj ten dokument od poczatku do konca,
- narysuj samodzielnie architekture na kartce,
- opowiedz glosno flow jednego case od ingest do final decision.

### Dzien 2
- przejdz kod orchestratora i shared worker,
- przejdz security i tracing,
- przygotuj odpowiedzi na 10 pytan z sekcji 13.2.

### Dzien 3
- odpal lokalny smoke na Dockerze,
- wykonaj ingest, review i DLQ replay,
- sprawdz Grafane i traces,
- przygotuj 5-minutowy demo script.

## 15. Finalny status projektu
Stan na 2026-03-08:
- backend: gotowy na production-grade MVP,
- security: domkniete na poziomie secret/JWKS + scope,
- observability: domkniete na poziomie metrics + OTLP/Tempo,
- reliability: domkniete na poziomie idempotencji + retry + DLQ + replay,
- UI MVP: zaimplementowane i zwalidowane,
- dokumentacja: scalona i uaktualniona,
- otwarty krok operacyjny: wykonanie realnego `docker compose` smoke w srodowisku z Dockerem.

## 16. Najkrotsza wersja do zapamietania
Jesli masz zapamietac tylko jedno zdanie:

To jest event-driven platforma fraudowa z append-only audytem, human-in-the-loop, odporna operacyjnie przez retry/DLQ/replay, obserwowalna przez metrics i tracing, oraz domknieta UI MVP do pracy operacyjnej.
