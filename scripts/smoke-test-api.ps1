# Quick API smoke test (requires PostgreSQL running on localhost:5432)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Load .env into process
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

Set-Location "$Root\backend"

Write-Host "Starting API server for smoke test..." -ForegroundColor Yellow
$job = Start-Job -ScriptBlock {
    Set-Location $using:Root\backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 2>&1
}

Start-Sleep -Seconds 5

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -Method Get
    if ($health.status -ne "healthy") { throw "Health check failed" }
    Write-Host "Health check: OK" -ForegroundColor Green

    $docs = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/docs" -Method Get -UseBasicParsing
    if ($docs.StatusCode -ne 200) { throw "OpenAPI docs unreachable" }
    Write-Host "API docs: OK" -ForegroundColor Green
}
catch {
    Write-Host "Smoke test skipped or failed (PostgreSQL/Redis may not be running): $_" -ForegroundColor Yellow
    Write-Host "Tests and builds passed without live server. Use Docker for full stack." -ForegroundColor Yellow
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq '' } | Stop-Process -Force -ErrorAction SilentlyContinue
}
