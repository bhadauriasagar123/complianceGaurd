# Local Vite dev server (proxies /api to backend)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path "node_modules")) { npm ci }
Write-Host "Frontend -> http://127.0.0.1:5173"
npm run dev -- --host 127.0.0.1 --port 5173
