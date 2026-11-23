# Runs YANA Travel Studio so OTHER computers on the same network can use it.
#
#  - Backend (FastAPI) stays private on 127.0.0.1:8000.
#  - Frontend runs as an optimised production server on port 3000, listening on
#    all network interfaces; it forwards /api/v1 to the backend.
#  - Other machines open:  http://<this-computer's-IP>:3000
#
# Windows Firewall must allow inbound TCP 3000 once: run scripts\allow-firewall.ps1
# as Administrator.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start-shared.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Port = 3000

Write-Host "Starting backend (private, 127.0.0.1:8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-backend.ps1`""

Write-Host "Building frontend (1-2 minutes)..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
npm run build
if ($LASTEXITCODE) { Write-Host "Frontend build failed." -ForegroundColor Red; exit $LASTEXITCODE }

$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress

Write-Host ""
Write-Host "YANA Travel Studio is being shared on your network:" -ForegroundColor Green
Write-Host "  On this computer:   http://localhost:$Port"
foreach ($ip in $ips) { Write-Host "  On other computers: http://${ip}:$Port" }
Write-Host ""
Write-Host "Keep this window and the backend window open. Press Ctrl+C here to stop sharing." -ForegroundColor Yellow
Write-Host ""

npx next start --hostname 0.0.0.0 --port $Port
