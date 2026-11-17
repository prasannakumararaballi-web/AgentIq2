@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo                      AgentIQ v2 - Stage Demonstration Launcher
echo ==============================================================================
echo [1/4] Checking environment...

cd /d "%~dp0\.."

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Python virtual environment not found in .venv.
    echo Please create it: python -m venv .venv ^&^& .venv\Scripts\pip install -e packages/agentiq_core ^&^& pip install -r apps/api/requirements.txt
    exit /b 1
)

echo [2/4] Verifying Demo Dataset and Seed Assets...
if not exist "storage\demo\demo_customers_1000.csv" (
    echo Generating deterministic 1,000-row demo customer dataset...
    .venv\Scripts\python.exe scripts\generate_demo_dataset.py
)
.venv\Scripts\python.exe scripts\seed_demo_data.py

echo [3/4] Starting FastAPI Backend on port 8000...
start "AgentIQ v2 - FastAPI Backend (Port 8000)" cmd /k "cd /d %~dp0\.. && call .venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload"

echo [4/4] Starting Next.js Frontend on port 3000...
start "AgentIQ v2 - Next.js Frontend (Port 3000)" cmd /k "cd /d %~dp0\..\apps\web && npm run dev"

echo ==============================================================================
echo Stage Demo Services Launched!
echo - Backend API:  http://localhost:8000/docs
echo - Web Frontend: http://localhost:3000
echo - Demo Login:   Select 'One-Click Stage Demo' on login screen
echo ==============================================================================
echo Keep both terminal windows open during your presentation.
