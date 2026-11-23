# Starts the Next.js frontend (development mode) on http://localhost:3000.
# Listens on 127.0.0.1 only, so it is NOT reachable from Wi-Fi/office networks
# (`next dev` would otherwise listen on all network interfaces).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\frontend"
npm run dev -- --hostname 127.0.0.1 --port 3000
