# Runs YANA Travel Studio privately for YOUR OWN devices (e.g. your phone) from any
# Wi-Fi or mobile network, using Tailscale.
#
#  - The app listens only on 127.0.0.1 (not on the Wi-Fi/office network).
#  - `tailscale serve` gives it a private https://<laptop>.<tailnet>.ts.net address,
#    reachable ONLY by devices signed in to your Tailscale account.
#  - Never uses Tailscale Funnel (which would make it public on the internet).
#
# One-time prerequisites:
#  1. Tailscale installed and signed in on this laptop and on your phone (same account).
#  2. In the Tailscale admin console (https://login.tailscale.com/admin/dns):
#     enable MagicDNS and "HTTPS Certificates".
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-tailscale.ps1
# Stop:   Ctrl+C here, close the backend window, then run:  tailscale serve reset
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Port = 3000

$ts = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $ts -and (Test-Path "$env:ProgramFiles\Tailscale\tailscale.exe")) { $ts = "$env:ProgramFiles\Tailscale\tailscale.exe" }
if (-not $ts) {
    Write-Host "Tailscale is not installed. Install it from https://tailscale.com/download and sign in, then run this again." -ForegroundColor Red
    exit 1
}
$status = & $ts status --json | ConvertFrom-Json
if ($status.BackendState -ne "Running") {
    Write-Host "Tailscale is not connected. Open the Tailscale app, sign in / connect, then run this again." -ForegroundColor Red
    exit 1
}
$dnsName = $status.Self.DNSName.TrimEnd(".")

Write-Host "Starting backend (private, 127.0.0.1:8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-backend.ps1`""

Write-Host "Building frontend (1-2 minutes)..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
npm run build
if ($LASTEXITCODE) { Write-Host "Frontend build failed." -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "Publishing to your private Tailscale network (tailscale serve)..." -ForegroundColor Cyan
& $ts serve --bg $Port
if ($LASTEXITCODE) {
    Write-Host "'tailscale serve' failed. Make sure MagicDNS and HTTPS Certificates are enabled in the Tailscale admin console." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "YANA Travel Studio is available privately:" -ForegroundColor Green
Write-Host "  On this laptop:                 http://localhost:$Port"
Write-Host "  On your phone (Tailscale on):   https://$dnsName"
Write-Host ""
Write-Host "Only devices signed in to your Tailscale account can open it." -ForegroundColor Yellow
Write-Host "Keep this window and the backend window open. Ctrl+C stops the app; then run 'tailscale serve reset'." -ForegroundColor Yellow
Write-Host ""

npx next start --hostname 127.0.0.1 --port $Port
