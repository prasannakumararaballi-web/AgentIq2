<#
.SYNOPSIS
    AgentIQ v2 - Stage Demonstration Launcher (PowerShell)
.DESCRIPTION
    Starts the FastAPI backend (Uvicorn) and Next.js frontend concurrently for stage demonstration.
#>

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "                  AgentIQ v2 - Stage Demonstration Launcher                   " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

# 1. Check Python virtual environment
Write-Host "[1/4] Verifying Python virtual environment..." -ForegroundColor Yellow
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython. Please configure .venv."
    exit 1
}

# 2. Check Demo Dataset and Seed Data
Write-Host "[2/4] Verifying deterministic 1,000-row demo dataset and database seed..." -ForegroundColor Yellow
$demoCsv = Join-Path $repoRoot "storage\demo\demo_customers_1000.csv"
if (-not (Test-Path $demoCsv)) {
    Write-Host "Generating demo dataset..." -ForegroundColor Gray
    & $venvPython (Join-Path $repoRoot "scripts\generate_demo_dataset.py")
}
& $venvPython (Join-Path $repoRoot "scripts\seed_demo_data.py")

# 3. Start Backend
Write-Host "[3/4] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; & '$venvPython' -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload"

# 4. Start Frontend
Write-Host "[4/4] Launching Next.js Frontend on http://localhost:3000..." -ForegroundColor Green
$webDir = Join-Path $repoRoot "apps\web"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$webDir'; npm run dev"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Stage Demonstration Services Active!" -ForegroundColor Green
Write-Host " - Web Application:  http://localhost:3000" -ForegroundColor White
Write-Host " - Interactive Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Instant Auth:     Click 'One-Click Stage Demo' on login screen" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
