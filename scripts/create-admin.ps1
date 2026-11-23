# Creates an additional administrator account (prompts for email, name and password).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\create-admin.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend"
$email = Read-Host "Administrator email"
$name = Read-Host "Administrator full name"
& .\.venv\Scripts\python.exe -m app.cli create-admin --email $email --name $name
