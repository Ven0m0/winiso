#Requires -Version 5.1
#Requires -RunAsAdministrator

<#
Converted from "Cleanup.cmd" - a live-running-OS disk cleanup helper (temp files,
driver installer leftovers, WER/Defender/search caches, Windows log/cache bloat).
Unlike the other iso-cmd scripts this targets the CURRENT machine, not a mounted WIM.

The original .cmd referenced %REG%, %LOGPATH%, %LOGFILE%, %WIN_VER% without ever
defining them; those are resolved here to real values instead.
#>

param(
    [string]$LogPath = (Join-Path $env:TEMP "iso-cmd-cleanup.log")
)

$ErrorActionPreference = "Continue"

function Remove-PathQuiet {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

"Cleanup started: $(Get-Date -Format o)" | Out-File -FilePath $LogPath -Append -Encoding utf8

Remove-PathQuiet "$env:WINDIR\Temp\*"
Remove-PathQuiet "$env:TEMP\*"
Remove-PathQuiet "$env:WINDIR\Prefetch"
Remove-PathQuiet "$env:WINDIR\Logs"
Remove-PathQuiet "$env:LOCALAPPDATA\cache"

# Root drive garbage
Remove-PathQuiet "$env:SystemDrive\Temp"
foreach ($ext in "bat", "cmd", "txt", "log", "jpg", "jpeg", "tmp", "temp", "bak", "backup", "exe") {
    Get-ChildItem -Path "$env:SystemDrive\" -Filter "*.$ext" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

# Leftover driver installer directories (Nvidia/ATI/AMD/Dell/Intel/HP)
foreach ($vendor in "NVIDIA", "ATI", "AMD", "Dell", "Intel", "HP") {
    Remove-PathQuiet "$env:SystemDrive\$vendor"
}

Remove-PathQuiet "$env:ProgramFiles\Nvidia Corporation\Installer2"
if (Test-Path "$env:ALLUSERSPROFILE\NVIDIA Corporation\NetService") {
    Get-ChildItem "$env:ALLUSERSPROFILE\NVIDIA Corporation\NetService\*.exe" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

# Office / Windows installation caches
Remove-PathQuiet "$env:SystemDrive\MSOCache"
Remove-PathQuiet "$env:SystemDrive\i386"

# Recycle bins
Remove-PathQuiet "$env:SystemDrive\RECYCLER"
Remove-PathQuiet "$env:SystemDrive\`$Recycle.Bin"

# MUI cache
reg.exe delete "HKCU\SOFTWARE\Classes\Local Settings\Muicache" /f 2>$null | Out-Null

# Windows Error Reporting queues
Remove-PathQuiet "$env:ALLUSERSPROFILE\Microsoft\Windows\WER\ReportArchive"
Remove-PathQuiet "$env:ALLUSERSPROFILE\Microsoft\Windows\WER\ReportQueue"

# Defender scan history
Remove-PathQuiet "$env:ALLUSERSPROFILE\Microsoft\Windows Defender\Scans\History\Results\Quick"
Remove-PathQuiet "$env:ALLUSERSPROFILE\Microsoft\Windows Defender\Scans\History\Results\Resource"

# Windows Search temp data
Remove-PathQuiet "$env:ALLUSERSPROFILE\Microsoft\Search\Data\Temp"

# Windows update logs & built-in backgrounds
foreach ($ext in "log", "txt", "bmp", "tmp") {
    Get-ChildItem -Path "$env:WINDIR" -Filter "*.$ext" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}
Remove-PathQuiet "$env:WINDIR\Web\Wallpaper\Dell"

# Cached NVIDIA driver updates
foreach ($base in $env:ProgramFiles, ${env:ProgramFiles(x86)}) {
    if ($base) {
        Remove-PathQuiet "$base\NVIDIA Corporation\Installer"
        Remove-PathQuiet "$base\NVIDIA Corporation\Installer2"
    }
}
Remove-PathQuiet "$env:ProgramData\NVIDIA Corporation\Downloader"
Remove-PathQuiet "$env:ProgramData\NVIDIA\Downloader"

# Windows CBS logs
Remove-PathQuiet "$env:WINDIR\Logs\CBS"

"Cleanup finished: $(Get-Date -Format o)" | Out-File -FilePath $LogPath -Append -Encoding utf8
Write-Host "[OK] Cleanup complete. Log: $LogPath" -ForegroundColor Green
