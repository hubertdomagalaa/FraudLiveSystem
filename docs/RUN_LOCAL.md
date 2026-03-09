# RUN LOCAL - Fraud Decision Support Platform

Ten dokument to najszybsza úcieøka uruchomienia lokalnego i sprawdzenia UI + ca≥ego pipeline.

## 1. Wymagania

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- Porty wolne: 5432, 6379, 8001-8004, 5173

## 2. Start backendu (PowerShell)

`powershell
cd C:\AntiGravity\FraudSeniorSystem\FraudLiveSystem
docker compose up -d postgres redis
pip install -r requirements-dev.txt
='postgresql://fraud:fraud@localhost:5432/fraud_platform'
alembic upgrade head
docker compose up --build
`

## 3. Start UI

Nowe okno terminala:

`powershell
cd C:\AntiGravity\FraudSeniorSystem\FraudLiveSystem\ui
cmd /c npm install
cmd /c npm run dev
`

UI: http://localhost:5173

## 4. JWT do operacji write

`powershell
python -c "import jwt, datetime; print(jwt.encode({'sub':'demo-user','scope':'fraud.write','exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, 'dev-local-fraud-secret', algorithm='HS256'))"
`

Wklej token do pola Bearer Token w UI.

## 5. Najszybszy test dzia≥ania

1. W UI wybierz preset Needs Review Demo.
2. Kliknij Create transaction.
3. Wejdü w case i sprawdü:
   - Pipeline Status
   - Why this decision?
4. Jeúli case ma REVIEW, wyúlij decyzjÍ w Manual Review.
5. Sprawdü DLQ Operations (jeúli sπ eventy DLQ) i przetestuj replay.

## 6. Seed gotowych scenariuszy demo

`powershell
cd C:\AntiGravity\FraudSeniorSystem\FraudLiveSystem
python scripts/demo_seed.py --token YOUR_JWT_TOKEN
`

Scenariusze: ALLOW, REVIEW, BLOCK.

## 7. Troubleshooting

- B≥πd CORS/auth w UI: sprawdü token i CORS_ALLOWED_ORIGINS.
- Brak case'Ûw: sprawdü logi ingestion-api i decision-orchestrator.
- Brak statusÛw krokÛw: sprawdü Redis streamy i worker logs.
- Brak write w UI: token musi mieÊ scope raud.write.

## 8. One-command demo startup

```powershell
cd C:\AntiGravity\FraudSeniorSystem\FraudLiveSystem
.\scripts\start_demo.ps1 -SeedDemoCases
```
