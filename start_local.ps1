# ======================================================================
# NYAYAVARTA - LOCAL FACULTY DEMO LAUNCHER (PowerShell)
# ======================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "             NYAYAVARTA - LOCAL FACULTY DEMO LAUNCHER                " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Start Backend in separate window
Write-Host "[1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
$backendCmd = "cd '$scriptDir\backend'; & '.\venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 2. Start Frontend in separate window
Write-Host "[2/3] Starting Next.js Frontend on http://localhost:3000 ..." -ForegroundColor Yellow
$frontendCmd = "cd '$scriptDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# 3. Wait and open browser
Write-Host "[3/3] Waiting for servers to spin up..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Opening Nyayavarta in browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"
Start-Process "http://127.0.0.1:8000/docs"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " Nyayavarta is running locally on your laptop!" -ForegroundColor Green
Write-Host " - Frontend UI:       http://localhost:3000" -ForegroundColor White
Write-Host " - Backend API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " Close the two PowerShell windows when your viva demo is finished." -ForegroundColor Gray
Write-Host "======================================================================`n" -ForegroundColor Cyan
