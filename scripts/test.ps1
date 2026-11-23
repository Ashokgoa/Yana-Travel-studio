# Runs all automated checks: backend tests, frontend typecheck, lint and unit tests.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend";  & .\.venv\Scripts\python.exe -m pytest; if ($LASTEXITCODE) { exit $LASTEXITCODE }
Set-Location "$Root\frontend"; npm run typecheck; if ($LASTEXITCODE) { exit $LASTEXITCODE }
npm run lint; if ($LASTEXITCODE) { exit $LASTEXITCODE }
npm test; if ($LASTEXITCODE) { exit $LASTEXITCODE }
Set-Location $Root
Write-Host "All checks passed." -ForegroundColor Green
