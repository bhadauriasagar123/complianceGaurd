# Start ComplianceGuard with Docker on Windows
# Requires Docker Desktop: https://www.docker.com/products/docker-desktop/
param(
    [ValidateSet("Quick", "Full")]
    [string]$Mode = "Quick"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DockerDir = Join-Path $Root "docker"

function Find-DockerExe {
    $candidates = @(
        "docker",
        "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe"
    )
    foreach ($c in $candidates) {
        if ($c -eq "docker") {
            $cmd = Get-Command docker -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
        } elseif (Test-Path $c) {
            return $c
        }
    }
    return $null
}

$Docker = Find-DockerExe
if (-not $Docker) {
    Write-Host ""
    Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "1. Install Docker Desktop:" -ForegroundColor Yellow
    Write-Host "   https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    Write-Host "2. Restart Windows if the installer asks." -ForegroundColor Yellow
    Write-Host "3. Open Docker Desktop - wait for 'Engine running'." -ForegroundColor Yellow
    Write-Host "4. Run again:" -ForegroundColor Yellow
    Write-Host "   .\scripts\start-docker.ps1" -ForegroundColor Cyan
    Write-Host "   .\scripts\start-docker.ps1 -Mode Full" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Guide: docs\DOCKER_LOCAL_WINDOWS.md" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "Missing .env - run: Copy-Item .env.example .env" -ForegroundColor Red
    exit 1
}

Write-Host "Using Docker: $Docker" -ForegroundColor Green
Write-Host "Mode: $Mode" -ForegroundColor Green
Set-Location $DockerDir

if ($Mode -eq "Quick") {
    Write-Host "Starting Quick stack (HTTP probe, ~5-10 min first build)..." -ForegroundColor Yellow
    & $Docker compose -f docker-compose.yml -f docker-compose.quick.yml up -d --build postgres redis api frontend
} else {
    Write-Host "Starting Full stack (Nmap/Nuclei/ZAP/Juice Shop, ~15-30 min first build)..." -ForegroundColor Yellow
    & $Docker compose --profile scanning up -d --build postgres redis api worker zap juice-shop frontend
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker compose failed. Is Docker Desktop running?" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Waiting for API (up to 3 minutes)..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 36; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 5
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ComplianceGuard (Docker) - $Mode mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " UI:         http://localhost:5173" -ForegroundColor Green
Write-Host " API:        http://localhost:8000" -ForegroundColor Green
Write-Host " API docs:   http://localhost:8000/docs" -ForegroundColor Green
if ($Mode -eq "Full") {
    Write-Host " Juice Shop: http://localhost:3000" -ForegroundColor Green
}
Write-Host ""
Write-Host " First-time setup:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:5173 and Register" -ForegroundColor White
Write-Host "  2. Scans -> Add target:" -ForegroundColor White
if ($Mode -eq "Full") {
    Write-Host "     http://juice-shop:3000  (or http://host.docker.internal:3000)" -ForegroundColor White
    Write-Host "  3. New scan -> Nmap + Nuclei -> Start (may take 10+ minutes)" -ForegroundColor White
} else {
    Write-Host "     https://testphp.vulnweb.com" -ForegroundColor White
    Write-Host "  3. New scan -> Start (finishes in ~10-30 seconds)" -ForegroundColor White
}
Write-Host "  4. Findings -> select completed scan" -ForegroundColor White
Write-Host ""
Write-Host " Stop:" -ForegroundColor Gray
if ($Mode -eq "Quick") {
    Write-Host "   cd docker; docker compose -f docker-compose.yml -f docker-compose.quick.yml down" -ForegroundColor Gray
} else {
    Write-Host "   cd docker; docker compose --profile scanning down" -ForegroundColor Gray
}
Write-Host " Guide: docs\DOCKER_LOCAL_WINDOWS.md" -ForegroundColor Gray
Write-Host ""

if (-not $healthy) {
    Write-Host "API not ready yet. Check: docker compose logs api" -ForegroundColor Yellow
}
