@echo off
title Nyayavarta Docker Stack Launcher
echo ======================================================================
echo           NYAYAVARTA - FULL DOCKER STACK LAUNCHER
echo ======================================================================
echo [1/3] Starting Neo4j, FastAPI Backend, and Next.js Frontend...
docker compose up -d

echo [2/3] Checking container status...
docker compose ps

echo [3/3] Seeding Neo4j Knowledge Graph with 38 Supreme Court Precedents...
timeout /t 5 /nobreak >nul
docker exec nyayavarta-backend python -m app.services.dataset_loader --all

echo Opening endpoints in default browser...
start http://localhost:3000
start http://localhost:8000/docs
start http://localhost:7474

echo ======================================================================
echo  Nyayavarta Full Docker Stack is Running!
echo  - Citizen Frontend:    http://localhost:3000
echo  - Backend API Docs:    http://localhost:8000/docs
echo  - Neo4j Graph Browser: http://localhost:7474 (User: neo4j / Pass: nyayavarta_secret_2024)
echo  To stop when finished: docker compose down
echo ======================================================================
pause
