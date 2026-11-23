# ======================================================================
# NYAYAVARTA - FULL DOCKER STACK LAUNCHER (PowerShell)
# ======================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "             NYAYAVARTA - FULL DOCKER STACK LAUNCHER                 " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. Start Docker Containers
Write-Host "[1/3] Spinning up Neo4j, Backend, and Frontend containers..." -ForegroundColor Yellow
docker compose up -d

# 2. Check Container Health
Write-Host "`n[2/3] Checking container status..." -ForegroundColor Yellow
docker compose ps

# 3. Seed Knowledge Graph
Write-Host "`n[3/3] Seeding Neo4j Knowledge Graph with 38 Supreme Court Precedents..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
docker exec nyayavarta-backend python -m app.services.dataset_loader --all

# 4. Open in Browser
Write-Host "`nOpening endpoints in your default browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"
Start-Process "http://localhost:8000/docs"
Start-Process "http://localhost:7474"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " Nyayavarta Full Docker Stack is Running Locally!" -ForegroundColor Green
Write-Host " - Frontend UI:        http://localhost:3000" -ForegroundColor White
Write-Host " - Backend API Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Neo4j Browser:      http://localhost:7474" -ForegroundColor White
Write-Host "                       Username: neo4j | Password: nyayavarta_secret_2024" -ForegroundColor Gray
Write-Host " To stop when finished: docker compose down" -ForegroundColor Yellow
Write-Host "======================================================================`n" -ForegroundColor Cyan
