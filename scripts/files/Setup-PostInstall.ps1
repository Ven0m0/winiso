param(
    [switch]$NoReboot
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== First Logon Configuration ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "[+] Disabling Hibernate..." -ForegroundColor Cyan
powercfg /hibernate off
Write-Host "[OK] Hibernate disabled" -ForegroundColor Green

Write-Host "[+] Stripping 8.3 filenames (this may take a while)..." -ForegroundColor Cyan
Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } | ForEach-Object {
    $drive = $_.DriveLetter + ":"
    Write-Host "    Processing $drive..." -ForegroundColor Gray
    fsutil 8dot3name strip /d $drive /s 2>$null
}
Write-Host "[OK] 8.3 filenames stripped" -ForegroundColor Green

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