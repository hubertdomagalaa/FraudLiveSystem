# Runbook: Disaster Recovery

## Zakres
Odtworzenie systemu po awarii klastra/hosta z zachowaniem danych audytowych.

## Zalozenia
1. PostgreSQL jest source-of-truth.
2. Redis Streams jest execution backbone.
3. Schemat DB jest odtwarzany przez Alembic.

## Procedura odtworzenia
1. Odtworz PostgreSQL z backupu.
2. Odtworz Redis (jesli wymagany) i deploymenty platformy.
3. Wykonaj migracje:
   1. `POSTGRES_DSN=... alembic upgrade head`
4. Wdroz serwisy:
   1. `kubectl apply -f infra/k8s/services`
   2. `kubectl apply -f infra/k8s/deployments`
   3. `kubectl apply -f infra/k8s/hpa`
   4. `kubectl apply -f infra/k8s/pdb`
5. Zweryfikuj health + metryki.
6. Przetestuj case end-to-end na danych testowych.

## Kontrola integralnosci po recovery
1. `cases` liczba rekordow zgodna z backupem.
2. `case_events` ma spojna os czasu dla probki case.
3. `decision_records` i `human_review_actions` sa spojne dla probki case.
4. Brak nieoczekiwanego przyrostu `stream_dlq_total`.
