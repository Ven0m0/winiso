#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Live-OS disk cleanup helper for Windows servicing.
.DESCRIPTION
    Restored from invoke_system_cleanup.py, itself converted from "Cleanup.cmd" /
    Invoke-SystemCleanup.ps1. Unlike the other Windows servicing scripts this
    targets the CURRENT machine, not a mounted WIM (temp files, driver installer
    leftovers, WER/Defender/search caches, log/cache bloat).
.PARAMETER LogPath
    Path to the cleanup log file.
#>
param(
    [string]$LogPath = (Join-Path $env:TEMP "iso-cmd-cleanup.log")
)

. "$PSScriptRoot\WinUtils.ps1"
Assert-Admin

$driveRootGarbageExts = @('bat', 'cmd', 'txt', 'log', 'jpg', 'jpeg', 'tmp', 'temp', 'bak', 'backup', 'exe')
$windirGarbageExts = @('log', 'txt', 'bmp', 'tmp')
$driverVendorDirs = @('NVIDIA', 'ATI', 'AMD', 'Dell', 'Intel', 'HP')

function Remove-PathQuiet {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$Path)
    if ($PSCmdlet.ShouldProcess($Path, 'Remove')) {
        Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Remove-FilesByExtension {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string[]]$Extensions)
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return }
    foreach ($ext in $Extensions) {
        $target = Join-Path $Root "*.$ext"
        if ($PSCmdlet.ShouldProcess($target, 'Remove')) {
            Remove-Item -Path $target -Force -ErrorAction SilentlyContinue
        }
    }
}

$windir = $env:WINDIR
$temp = $env:TEMP
$systemDrive = if ($env:SystemDrive) { $env:SystemDrive } else { 'C:' }
$programFiles = $env:ProgramFiles
$programFilesX86 = ${env:ProgramFiles(x86)}
$allUsersProfile = $env:ALLUSERSPROFILE
$localAppData = $env:LOCALAPPDATA

"Cleanup started: $(Get-Date -AsUTC -Format 'o')" | Add-Content -Path $LogPath -Encoding utf8

Remove-PathQuiet "$windir\Temp\*"
Remove-PathQuiet "$temp\*"
Remove-PathQuiet "$windir\Prefetch"
Remove-PathQuiet "$windir\Logs"
Remove-PathQuiet "$localAppData\cache"

Remove-PathQuiet "$systemDrive\Temp"
Remove-FilesByExtension "$systemDrive\" $driveRootGarbageExts

foreach ($vendor in $driverVendorDirs) {
    Remove-PathQuiet "$systemDrive\$vendor"
}

Remove-PathQuiet "$programFiles\Nvidia Corporation\Installer2"
$nvidiaNetService = "$allUsersProfile\NVIDIA Corporation\NetService"
if (Test-Path -LiteralPath $nvidiaNetService -PathType Container) {
    Remove-Item -Path (Join-Path $nvidiaNetService "*.exe") -Force -ErrorAction SilentlyContinue
}

Remove-PathQuiet "$systemDrive\MSOCache"
Remove-PathQuiet "$systemDrive\i386"

Remove-PathQuiet "$systemDrive\RECYCLER"
Remove-PathQuiet "$systemDrive\`$Recycle.Bin"

& reg.exe delete "HKCU\SOFTWARE\Classes\Local Settings\Muicache" /f 2>$null | Out-Null

Remove-PathQuiet "$allUsersProfile\Microsoft\Windows\WER\ReportArchive"
Remove-PathQuiet "$allUsersProfile\Microsoft\Windows\WER\ReportQueue"

Remove-PathQuiet "$allUsersProfile\Microsoft\Windows Defender\Scans\History\Results\Quick"
Remove-PathQuiet "$allUsersProfile\Microsoft\Windows Defender\Scans\History\Results\Resource"

Remove-PathQuiet "$allUsersProfile\Microsoft\Search\Data\Temp"

Remove-FilesByExtension $windir $windirGarbageExts
Remove-PathQuiet "$windir\Web\Wallpaper\Dell"

foreach ($base in @($programFiles, $programFilesX86)) {
    if ($base) {
        Remove-PathQuiet "$base\NVIDIA Corporation\Installer"
        Remove-PathQuiet "$base\NVIDIA Corporation\Installer2"
    }
}
Remove-PathQuiet "$env:ProgramData\NVIDIA Corporation\Downloader"
Remove-PathQuiet "$env:ProgramData\NVIDIA\Downloader"

Remove-PathQuiet "$windir\Logs\CBS"

"Cleanup finished: $(Get-Date -AsUTC -Format 'o')" | Add-Content -Path $LogPath -Encoding utf8

Write-Success "Cleanup complete. Log: $LogPath"
exit 0
