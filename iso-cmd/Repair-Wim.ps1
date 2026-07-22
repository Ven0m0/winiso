#Requires -Version 5.1
#Requires -RunAsAdministrator

<#
Converted from "Repair Wim.cmd". Repairs a mounted install.wim against a known-good
reference image (RestoreHealth /Source), then re-optimizes it.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ReferenceWimPath,
    [string]$TargetWimPath = "C:\ISO\sources\install.wim",
    [string]$MountRoot = "C:\mnt",
    [string]$ReferenceMountRoot = "C:\Repair"
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

if (-not (Test-Path $ReferenceWimPath)) { Write-ErrorExit "Reference WIM not found: $ReferenceWimPath" }
if (-not (Test-Path $TargetWimPath)) { Write-ErrorExit "Target WIM not found: $TargetWimPath" }

New-Item -ItemType Directory -Path $ReferenceMountRoot -Force | Out-Null
New-Item -ItemType Directory -Path $MountRoot -Force | Out-Null

Write-Step "Mounting reference image"
Mount-WindowsImage -ImagePath $ReferenceWimPath -Index 1 -Path $ReferenceMountRoot | Out-Null
Clear-WindowsCorruptMountPoint | Out-Null

Write-Step "Mounting target image"
Mount-WindowsImage -ImagePath $TargetWimPath -Index 1 -Path $MountRoot | Out-Null
Clear-WindowsCorruptMountPoint | Out-Null

Write-Step "Running RestoreHealth against reference source"
Repair-WindowsImage -Path $MountRoot -RestoreHealth -Source (Join-Path $ReferenceMountRoot "windows") | Out-Null

& dism.exe "/Image:$MountRoot" "/Optimize-ProvisionedAppxPackages" | Out-Null
Invoke-Dism @("/Cleanup-Image", "/Image=$MountRoot", "/StartComponentCleanup", "/ResetBase")
Clear-WindowsCorruptMountPoint | Out-Null

Write-Step "Saving target image"
Dismount-WindowsImage -Path $MountRoot -Save | Out-Null

Write-Step "Discarding reference mount"
Dismount-WindowsImage -Path $ReferenceMountRoot -Discard | Out-Null

Clear-WindowsCorruptMountPoint | Out-Null
Invoke-Dism @("/CleanUp-Wim")

Write-Success "Repair complete: $TargetWimPath"
