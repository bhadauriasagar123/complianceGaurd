# ComplianceGuard - Local development (SQLite, no Docker required)
$ErrorActionPreference = "Stop"
$root = "$PSScriptRoot\.."

if (-not (Test-Path "$root\.env")) {
    Copy-Item "$root\.env.example" "$root\.env"
    Write-Host "Created .env from .env.example - update SECRET_KEY before production" -ForegroundColor Yellow
}

# Use SQLite for local dev when PostgreSQL is not available
$env:DATABASE_URL = "sqlite+aiosqlite:///$root/data/complianceguard.db"
$env:SECRET_KEY = "local-dev-secret-key-minimum-32-characters-long"
$env:FIELD_ENCRYPTION_KEY = "8vP2mKqR9xT4nW7jL1hF5sY0bN6cA3eU="
$env:TESTING = "false"
$env:APP_DEBUG = "true"

New-Item -ItemType Directory -Force -Path "$root\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\backend\reports" | Out-Null

Write-Host "Initializing database..." -ForegroundColor Cyan
Set-Location "$root\backend"
python -m pip install -q -r requirements.txt aiosqlite

python -c @"
import asyncio
from app.core.database import Base, engine

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database tables created')

asyncio.run(init())
"@

Write-Host "Starting API on http://localhost:8000" -ForegroundColor Green
Write-Host "Start frontend separately: cd frontend && npm run dev" -ForegroundColor Green
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
