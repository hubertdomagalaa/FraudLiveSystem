param(
  [switch],
  [switch]
)

Continue = 'Stop'

function Step() {
  Write-Host "
==> " -ForegroundColor Cyan
}

Step "Checking Docker"
docker --version | Out-Host

docker compose version | Out-Host

Step "Starting infrastructure (Postgres + Redis)"
docker compose up -d postgres redis

Step "Installing Python dependencies"
pip install -r requirements-dev.txt

Step "Running DB migrations"
 = 'postgresql://fraud:fraud@localhost:5432/fraud_platform'
alembic upgrade head

if () {
  Step "Starting app stack (without rebuild)"
  docker compose up -d
}
else {
  Step "Starting app stack (with rebuild)"
  docker compose up -d --build
}

Step "Generating demo JWT token"
 = python -c "import jwt, datetime; print(jwt.encode({'sub':'demo-user','scope':'fraud.write','exp': datetime.datetime.utcnow() + datetime.timedelta(hours=6)}, 'dev-local-fraud-secret', algorithm='HS256'))"

Write-Host "
================ DEMO READY ================" -ForegroundColor Green
Write-Host "UI:              http://localhost:5173"
Write-Host "Orchestrator API: http://localhost:8002/v1"
Write-Host "Grafana:         http://localhost:3000"
Write-Host "Prometheus:      http://localhost:9090"
Write-Host ""
Write-Host "Paste this Bearer token into UI:" -ForegroundColor Yellow
Write-Host 
Write-Host "============================================
" -ForegroundColor Green

if () {
  Step "Seeding demo ALLOW/REVIEW/BLOCK cases"
  python scripts/demo_seed.py --token 
}

Step "Helpful commands"
Write-Host "Logs (all):      docker compose logs -f"
Write-Host "Logs (one svc):  docker compose logs -f decision-orchestrator"
Write-Host "Stop stack:      docker compose down"
