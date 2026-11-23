# One-time setup: Python venv + backend deps, database migration, frontend deps.
# Usage (from project root):  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location "$Root\backend"
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m alembic upgrade head

Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location "$Root\frontend"
npm install
if (-not (Test-Path ".env.local")) { Copy-Item .env.example .env.local }

if (-not (Test-Path "$Root\.env")) { Copy-Item "$Root\.env.example" "$Root\.env" }
Set-Location $Root
Write-Host "Setup complete. Start the app with: scripts\start.ps1" -ForegroundColor Green
