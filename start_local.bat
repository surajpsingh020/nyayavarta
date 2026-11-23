@echo off
title Nyayavarta Local Launcher
echo ======================================================================
echo              NYAYAVARTA - LOCAL FACULTY DEMO LAUNCHER
echo ======================================================================
echo [1/3] Starting Backend API (FastAPI) on http://127.0.0.1:8000 ...
start "Nyayavarta Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Starting Frontend (Next.js 14) on http://localhost:3000 ...
start "Nyayavarta Frontend (Next.js)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

echo Opening Nyayavarta in your default web browser...
start http://localhost:3000
start http://127.0.0.1:8000/docs

echo ======================================================================
echo  Nyayavarta is running locally!
echo  - Frontend Web App:     http://localhost:3000
echo  - Backend API Docs:     http://127.0.0.1:8000/docs
echo  Close the two opened command windows to stop the servers.
echo ======================================================================
pause
