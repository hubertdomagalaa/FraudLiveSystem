Continue = 'Stop'

Write-Host "Stopping demo stack..." -ForegroundColor Cyan
docker compose down
Write-Host "Done." -ForegroundColor Green
