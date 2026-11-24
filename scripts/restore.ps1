# Restores a backup zip: replaces the database, uploaded images and generated PDFs.
# STOP the app first (close the start.ps1 windows). A safety backup of the current state is made automatically.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 -File database\backups\yana_backup_YYYYMMDD_HHMMSS.zip
param([Parameter(Mandatory = $true)][string]$File)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Path = Resolve-Path $File
Set-Location "$Root\backend"
& .\.venv\Scripts\python.exe -m app.cli restore "$Path"
