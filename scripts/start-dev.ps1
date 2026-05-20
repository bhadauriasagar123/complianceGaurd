# Start ComplianceGuard backend + frontend (SQLite dev mode, no Docker required)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$DbPath = Join-Path $Backend "dev.db"

# Load .env
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

# Dev overrides (no Postgres/Redis required for API + UI)
$env:DATABASE_URL = "sqlite+aiosqlite:///$($DbPath -replace '\\','/')"
$env:APP_ENV = "development"
$env:APP_DEBUG = "false"

Write-Host "Initializing database at $DbPath ..." -ForegroundColor Yellow
Set-Location $Backend
python -c @"
import asyncio
from app.core.database import Base, engine
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables ready')
asyncio.run(init())
"@

Write-Host "Starting API on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $Backend "run-api.ps1") -WorkingDirectory $Backend

Start-Sleep -Seconds 5

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $Frontend "run-dev.ps1") -WorkingDirectory $Frontend

Start-Sleep -Seconds 6

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 10
    Write-Host "API health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "API not ready yet: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "ComplianceGuard is running:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:5173"
Write-Host "  API:       http://localhost:8000"
Write-Host "  API Docs:  http://localhost:8000/api/docs"
Write-Host ""
Write-Host "Register a new account at http://localhost:5173/register"
Write-Host "Scans run in dev mock mode (SQLite) — no Docker or scanner tools required."
