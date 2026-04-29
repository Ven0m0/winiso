param(
    [switch]$NoReboot
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== First Logon Configuration ===" -ForegroundColor Yellow
Write-Host ""

Write-Step "Disabling Hibernate..."
powercfg /hibernate off
Write-Success "Hibernate disabled"

Write-Step "Stripping 8.3 filenames (this may take a while)..."
Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } | ForEach-Object {
    $drive = $_.DriveLetter + ":"
    Write-Host "    Processing $drive..."
    fsutil 8dot3name strip /d $drive /s 2>$null
}
Write-Success "8.3 filenames stripped"

Write-Host ""
Write-Host "=== Configuration Complete ===" -ForegroundColor Green
Write-Host ""

if (-not $NoReboot) {
    Write-Host "System will reboot in 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    Restart-Computer -Force
}

$ScriptPath = $MyInvocation.PSCommandPath
Remove-Item $ScriptPath -Force -ErrorAction SilentlyContinue