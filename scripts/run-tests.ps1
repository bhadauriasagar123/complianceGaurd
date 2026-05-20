# ComplianceGuard - Run all tests and builds
$ErrorActionPreference = "Stop"

Write-Host "=== Backend Tests ===" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\..\backend"
python -m pip install -q -r requirements.txt aiosqlite pytest pytest-asyncio pytest-cov httpx pytest-env
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== Frontend Build ===" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\..\frontend"
npm ci --silent
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== All checks passed ===" -ForegroundColor Green
