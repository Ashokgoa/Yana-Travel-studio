# Starts the FastAPI backend privately on 127.0.0.1:8000 (applies pending migrations first).
# The frontend forwards /api/v1 to it; it is never exposed to the network.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend"
& .\.venv\Scripts\python.exe -m alembic upgrade head
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
