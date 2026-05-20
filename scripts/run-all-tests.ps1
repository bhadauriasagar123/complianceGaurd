# ComplianceGuard - Run all tests and builds (no Docker required for tests)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== ComplianceGuard Test Suite ===" -ForegroundColor Cyan

# Backend
Write-Host "`n[1/4] Installing backend dependencies..." -ForegroundColor Yellow
Set-Location "$Root\backend"
python -m pip install -r requirements.txt -q
python -m pip install pytest pytest-asyncio pytest-cov ruff bandit -q

Write-Host "[2/4] Backend lint (ruff)..." -ForegroundColor Yellow
python -m ruff check app tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] Backend tests (pytest + SQLite in-memory)..." -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Frontend
Write-Host "`n[4/4] Frontend build..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm ci }
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== All checks passed ===" -ForegroundColor Green
Set-Location $Root
