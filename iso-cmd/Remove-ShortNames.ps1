#Requires -Version 5.1
#Requires -RunAsAdministrator

<#
Consolidates the former "8.3 strip all.cmd", "Remove Shortnames.cmd", and
"Remove Shortnames -install.cmd" into one parameterized script:
  - default (no switches)      : install.wim + boot.wim   (was "Remove Shortnames.cmd")
  - -IncludeWinre              : also reprocess Winre.wim  (was "8.3 strip all.cmd")
  - -InstallOnly               : install.wim only, drop leftover *.LOG (was "...-install.cmd")
#>

param(
    [string]$IsoRoot = "C:\ISO",
    [string]$MountRoot = "C:\mnt",
    [switch]$InstallOnly,
    [switch]$IncludeWinre
)

$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Message) Write-Host "[+] $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-ErrorExit { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red; exit 1 }

function Invoke-Dism {
    param([string[]]$DismArgs)
    & dism.exe @DismArgs
    if ($LASTEXITCODE -ne 0) { Write-ErrorExit "dism $($DismArgs -join ' ') failed with exit code $LASTEXITCODE" }
}

function Strip-8dot3 {
    param([string]$Path)
    Write-Step "Stripping 8.3 short names under $Path"
    & fsutil 8dot3name strip /f /s $Path | Out-Null
}

function Clean-MountedImage {
    param([string]$MountDir)
    & dism.exe "/Image:$MountDir" "/Optimize-ProvisionedAppxPackages" | Out-Null
    Invoke-Dism @("/Cleanup-Image", "/Image=$MountDir", "/StartComponentCleanup", "/ResetBase")
}

Clear-WindowsCorruptMountPoint | Out-Null
Invoke-Dism @("/CleanUp-Wim")
Strip-8dot3 -Path $IsoRoot

$installWim = Join-Path $IsoRoot "sources\install.wim"
$installMount = Join-Path $MountRoot "install"
New-Item -ItemType Directory -Path $installMount -Force | Out-Null

Write-Step "Mounting install.wim"
Mount-WindowsImage -ImagePath $installWim -Index 1 -Path $installMount | Out-Null
Strip-8dot3 -Path $installMount
Clean-MountedImage -MountDir $installMount

if ($InstallOnly) {
    Write-Step "Removing leftover *.LOG files"
    Get-ChildItem -Path $installMount -Filter "*LOG" -Recurse -Force -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

if ($IncludeWinre) {
    $winreWim = Join-Path $installMount "Windows\System32\Recovery\Winre.wim"
    $winreMount = Join-Path $MountRoot "winre"
    New-Item -ItemType Directory -Path $winreMount -Force | Out-Null

    Clear-WindowsCorruptMountPoint | Out-Null
    Write-Step "Mounting Winre.wim"
    Mount-WindowsImage -ImagePath $winreWim -Index 1 -Path $winreMount | Out-Null
    Strip-8dot3 -Path $winreMount
    Invoke-Dism @("/Cleanup-Image", "/Image=$winreMount", "/StartComponentCleanup", "/ResetBase")
    Clear-WindowsCorruptMountPoint | Out-Null
    Dismount-WindowsImage -Path $winreMount -Save | Out-Null

    $winreCleaned = Join-Path $installMount "Windows\System32\Recovery\Winre_cleaned.wim"
    Export-WindowsImage -SourceImagePath $winreWim -SourceIndex 1 -DestinationImagePath $winreCleaned -CompressionType Maximum -CheckIntegrity | Out-Null
    Clear-WindowsCorruptMountPoint | Out-Null

    Start-Sleep -Seconds 1
    Remove-Item -Path $winreWim -Force
    Start-Sleep -Seconds 2
    Rename-Item -Path $winreCleaned -NewName "Winre.wim"
    Start-Sleep -Seconds 1
    Write-Success "Winre.wim reprocessed"
}

Clear-WindowsCorruptMountPoint | Out-Null
Dismount-WindowsImage -Path $installMount -Save | Out-Null

$installCleaned = Join-Path $IsoRoot "sources\install_cleaned.wim"
Export-WindowsImage -SourceImagePath $installWim -SourceIndex 1 -DestinationImagePath $installCleaned -CompressionType Maximum -CheckIntegrity | Out-Null
Clear-WindowsCorruptMountPoint | Out-Null
Invoke-Dism @("/CleanUp-Wim")
Write-Success "install.wim processed -> $installCleaned"

if (-not $InstallOnly) {
    $bootWim = Join-Path $IsoRoot "sources\boot.wim"
    $bootMount = Join-Path $MountRoot "boot"
    New-Item -ItemType Directory -Path $bootMount -Force | Out-Null

    Write-Step "Mounting boot.wim"
    Mount-WindowsImage -ImagePath $bootWim -Index 1 -Path $bootMount | Out-Null
    Strip-8dot3 -Path $bootMount
    Invoke-Dism @("/Cleanup-Image", "/Image=$bootMount", "/StartComponentCleanup", "/ResetBase")
    Clear-WindowsCorruptMountPoint | Out-Null
    Dismount-WindowsImage -Path $bootMount -Save | Out-Null

    $bootCleaned = Join-Path $IsoRoot "sources\boot_cleaned.wim"
    Export-WindowsImage -SourceImagePath $bootWim -SourceIndex 1 -DestinationImagePath $bootCleaned -CompressionType Maximum -CheckIntegrity | Out-Null
    Clear-WindowsCorruptMountPoint | Out-Null
    Invoke-Dism @("/CleanUp-Wim")
    Write-Success "boot.wim processed -> $bootCleaned"
}

Write-Success "Done."
