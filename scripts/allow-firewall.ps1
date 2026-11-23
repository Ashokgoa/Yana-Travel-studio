# One-time: allow other computers on PRIVATE/DOMAIN networks to reach YANA Travel
# Studio on TCP port 3000. Public networks (cafés, hotels) stay blocked.
# Must be run as Administrator:
#   Right-click PowerShell > "Run as administrator", then:
#   powershell -ExecutionPolicy Bypass -File scripts\allow-firewall.ps1
#
# To remove later:  Remove-NetFirewallRule -DisplayName "YANA Travel Studio (3000)"
$ErrorActionPreference = "Stop"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Please run this script from PowerShell opened with 'Run as administrator'." -ForegroundColor Red
    exit 1
}
$name = "YANA Travel Studio (3000)"
if (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue) {
    Write-Host "Firewall rule already exists: $name" -ForegroundColor Green
    exit 0
}
New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort 3000 `
    -Action Allow -Profile Domain, Private | Out-Null
Write-Host "Firewall rule added: $name (Domain and Private networks only)." -ForegroundColor Green
