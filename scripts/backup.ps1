# Backs up the database, uploaded images and generated PDFs into database\backups (safe while the app runs).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend"
& .\.venv\Scripts\python.exe -m app.cli backup
