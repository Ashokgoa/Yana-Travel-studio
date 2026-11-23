# One-time setup (safe to re-run): Python venv + backend deps, config, database
# migration, first administrator account, frontend deps.
# Usage (from project root):  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = "$Root\backend\.venv\Scripts\python.exe"

Write-Host "== Configuration ==" -ForegroundColor Cyan
if (-not (Test-Path "$Root\.env")) { Copy-Item "$Root\.env.example" "$Root\.env" }
$envText = Get-Content "$Root\.env" -Raw
if ($envText -notmatch "(?m)^YANA_SECRET_KEY=\S+") {
    # Random key that signs login sessions; stays only in your local .env (git-ignored).
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $key = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
    if ($envText -match "(?m)^YANA_SECRET_KEY=") {
        $envText = $envText -replace "(?m)^YANA_SECRET_KEY=.*$", "YANA_SECRET_KEY=$key"
    } else {
        $envText = $envText.TrimEnd() + "`r`nYANA_SECRET_KEY=$key`r`n"
    }
    Set-Content -Path "$Root\.env" -Value $envText -Encoding utf8 -NoNewline
    Write-Host "Generated YANA_SECRET_KEY in .env"
}

Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location "$Root\backend"
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements-dev.txt
& $Py -m alembic upgrade head

$hasAdmin = & $Py -c "from sqlalchemy import select; from app.database.session import SessionLocal; from app.models import User, Role; s=SessionLocal(); print(s.scalar(select(User.id).join(User.role).where(Role.code=='admin').limit(1)) is not None)"
if ($hasAdmin -eq "False") {
    Write-Host ""
    Write-Host "No administrator account yet. Let's create one." -ForegroundColor Yellow
    $email = Read-Host "Administrator email"
    $name = Read-Host "Administrator full name"
    & $Py -m app.cli create-admin --email $email --name $name
}

Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location "$Root\frontend"
npm install
if (-not (Test-Path ".env.local")) { Copy-Item .env.example .env.local }

Set-Location $Root
Write-Host "Setup complete. Start the app with: scripts\start.ps1" -ForegroundColor Green
