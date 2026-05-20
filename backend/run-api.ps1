# Local API server (SQLite — no Docker)
$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$RepoRoot = Split-Path $BackendRoot -Parent

if (Test-Path (Join-Path $RepoRoot ".env")) {
    Get-Content (Join-Path $RepoRoot ".env") | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

$devDb = Join-Path $BackendRoot "dev.db"
$env:DATABASE_URL = "sqlite+aiosqlite:///$($devDb -replace '\\','/')"
$env:APP_ENV = "development"

Set-Location $BackendRoot
Write-Host "API -> http://127.0.0.1:8000 (DB: $devDb)"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
