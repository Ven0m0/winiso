#Requires -Version 5.1

<#
Converted from "ISO.cmd". Builds a bootable UEFI+BIOS ISO from a staged directory
using oscdimg.exe (Windows ADK Deployment Tools).
#>

param(
    [string]$IsoRoot = "C:\ISO",
    [string]$OutputIso = "C:\Win.iso"
)

$ErrorActionPreference = "Stop"

function Write-ErrorExit { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red; exit 1 }

function Find-Oscdimg {
    $paths = @(
        (Join-Path $env:USERPROFILE "AppData\Local\Microsoft\WinGet\Links\oscdimg.exe"),
        "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe",
        "C:\Program Files (x86)\Windows Kits\11\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    Write-ErrorExit "oscdimg.exe not found. Install Windows ADK Deployment Tools or winget it."
}

if (-not (Test-Path $IsoRoot)) { Write-ErrorExit "ISO root not found: $IsoRoot" }

$oscdimgPath = Find-Oscdimg
$etfsboot = Join-Path $IsoRoot "boot\etfsboot.com"
$efisys = Join-Path $IsoRoot "efi\Microsoft\boot\efisys.bin"

if (-not (Test-Path $etfsboot)) { Write-ErrorExit "etfsboot.com not found under $IsoRoot" }
if (-not (Test-Path $efisys)) { Write-ErrorExit "efisys.bin not found under $IsoRoot" }

$bootData = "2#p0,e,b$etfsboot#pEF,e,b$efisys"
& $oscdimgPath -m -o -u2 -udfver102 "-bootdata:$bootData" $IsoRoot $OutputIso

if ($LASTEXITCODE -ne 0) { Write-ErrorExit "oscdimg failed with exit code $LASTEXITCODE" }
Write-Host "[OK] ISO created: $OutputIso" -ForegroundColor Green
