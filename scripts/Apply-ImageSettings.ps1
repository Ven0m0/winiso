#Requires -RunAsAdministrator
#Requires -Version 5.1
# Script analysis suppressed - Write-Host is intentional for colored console output
# noqa: PSAvoidUsingWriteHost

param(
    [Parameter(Mandatory=$false)]
    [string]$ISOPath,

    [Parameter(Mandatory=$false)]
    [string]$ExtractPath,

    [Parameter(Mandatory=$false)]
    [string]$OutputPath,

    [Parameter(Mandatory=$false)]
    [string]$MountDir,

    [Parameter(Mandatory=$false)]
    [switch]$SkipISO
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $ScriptDir "config.ps1"

if (-not (Test-Path $ConfigFile)) {
    Write-Error "Config file not found: $ConfigFile"
    exit 1
}

. $ConfigFile

if (-not $ISOPath -and -not $ExtractPath) {
    Write-Host "ERROR: Must specify either -ISOPath or -ExtractPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\Apply-ImageSettings.ps1 -ISOPath <path>           # From ISO"
    Write-Host "  .\Apply-ImageSettings.ps1 -ExtractPath <path>    # From extracted folder"
    Write-Host "  .\Apply-ImageSettings.ps1 -ISOPath <path> -SkipISO  # Modify only, no ISO creation"
    exit 1
}

if ($ISOPath -and $ExtractPath) {
    Write-Host "ERROR: Cannot specify both -ISOPath and -ExtractPath" -ForegroundColor Red
    exit 1
}

if (-not $MountDir) { $MountDir = $DefaultMountDir }

function Find-Oscdimg {
    $WingetPath = Join-Path $env:USERPROFILE "AppData\Local\Microsoft\WinGet\Links\oscdimg.exe"
    $Paths = @(
        $WingetPath,
        "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe",
        "C:\Program Files (x86)\Windows Kits\11\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
    )
    foreach ($p in $Paths) {
        if (Test-Path $p) { return $p }
    }
    Write-Error "oscdimg.exe not found. Install Windows ADK Deployment Tools or winget it."
    exit 1
}

if (-not $OscdimgPath) {
    $OscdimgPath = Find-Oscdimg
}

function Write-Step {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-ErrorExit {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Safe-RemoveDirectory {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    try {
        Remove-Item $Path -Recurse -Force -ErrorAction Stop
    }
    catch {
        Write-Host "      Retrying cleanup..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        try {
            Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "      Warning: Could not fully clean $Path" -ForegroundColor Yellow
        }
    }
}

if ($ExtractPath) {
    if (-not (Test-Path $ExtractPath)) { Write-ErrorExit "ExtractPath not found: $ExtractPath" }
    $ExtractDir = $ExtractPath
    Write-Step "Using extracted folder: $ExtractDir"
} else {
    if (-not (Test-Path $ISOPath)) { Write-ErrorExit "ISO not found: $ISOPath" }

    if (-not $OutputPath) {
        $OutputPath = [System.IO.Path]::ChangeExtension($ISOPath, "_modified.iso")
    }

    $ExtractDir = $TempExtractDir
    if (Test-Path $ExtractDir) {
        Remove-Item $ExtractDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null

    Write-Step "Extracting ISO..."
    $Shell = New-Object -ComObject Shell.Application
    $Zip = $Shell.Namespace($ISOPath)
    $Zip.CopyHere($Zip.Items(), 0x100) | Out-Null

    Start-Sleep -Seconds 2

    $ExtractDir = (Get-ChildItem $ExtractDir | Select-Object -First 1).FullName
    if (-not $ExtractDir) {
        Get-ChildItem $ISOPath | ForEach-Object {
            Copy-Item $_.FullName "$TempExtractDir\" -Recurse -Force
        }
        $ExtractDir = $TempExtractDir
    }

    Write-Success "ISO extracted to: $ExtractDir"
}

if (-not (Test-Path "$ExtractDir\sources\boot.wim")) { Write-ErrorExit "boot.wim not found" }
if (-not (Test-Path "$ExtractDir\sources\install.wim")) { Write-ErrorExit "install.wim not found" }

if (-not (Test-Path $MountDir)) {
    New-Item -ItemType Directory -Path $MountDir -Force | Out-Null
}

foreach ($idx in $BootWimIndexes) {
    Write-Step "Processing boot.wim index $idx..."
    $BootMount = Join-Path $MountDir "boot$idx"

    # Check if already mounted and remount if necessary
    try {
        $existingMount = Get-WindowsImage -Mounted | Where-Object { $_.Path -eq $BootMount }
        if ($existingMount) {
            Write-Host "      Image already mounted, remounting..." -ForegroundColor Yellow
            Dismount-WindowsImage -Path $BootMount -Discard -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    catch { }

    Safe-RemoveDirectory $BootMount
    New-Item -ItemType Directory -Path $BootMount -Force | Out-Null

    Mount-WindowsImage -ImagePath "$ExtractDir\sources\boot.wim" -Index $idx -Path $BootMount -Optimize -ErrorAction Stop | Out-Null
    Copy-Item "$ScriptDir\autounattend.xml" "$BootMount\autounattend.xml" -Force
    Write-Success "Copied autounattend.xml to boot.wim index $idx"

    Dismount-WindowsImage -Path $BootMount -Save -ErrorAction Stop | Out-Null
    Write-Success "Unmounted boot.wim index $idx"
}

Write-Step "Processing install.wim index $InstallWimIndex..."
$InstallMount = Join-Path $MountDir "install"

# Check if already mounted and remount if necessary
try {
    $existingMount = Get-WindowsImage -Mounted | Where-Object { $_.Path -eq $InstallMount }
    if ($existingMount) {
        Write-Host "      Image already mounted, remounting..." -ForegroundColor Yellow
        Dismount-WindowsImage -Path $InstallMount -Discard -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}
catch { }

Safe-RemoveDirectory $InstallMount
New-Item -ItemType Directory -Path $InstallMount -Force | Out-Null

Mount-WindowsImage -ImagePath "$ExtractDir\sources\install.wim" -Index $InstallWimIndex -Path $InstallMount -Optimize -ErrorAction Stop | Out-Null
Write-Success "Mounted install.wim index $InstallWimIndex"

Write-Step "Copying autounattend.xml..."
Copy-Item "$ScriptDir\autounattend.xml" "$InstallMount\Windows\Panther\unattend.xml" -Force
Copy-Item "$ScriptDir\autounattend.xml" "$ExtractDir\autounattend.xml" -Force

Write-Step "Disabling 8.3 filename creation..."
$RegHivePath = "$InstallMount\Windows\System32\Config\SYSTEM"
$TempHive = "HKLM\WIM_REG"
reg load $TempHive $RegHivePath | Out-Null
Set-ItemProperty -Path "HKLM:\WIM_REG\ControlSet001\Control\FileSystem" -Name "NtfsDisable8dot3NameCreation" -Value 1 -Type DWord -ErrorAction SilentlyContinue
reg unload $TempHive | Out-Null
Write-Success "8.3 filename creation disabled"

Write-Step "Injecting post-install scripts..."
$ScriptsDir = "$InstallMount\Windows\Setup\Scripts"
if (-not (Test-Path $ScriptsDir)) { New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null }

$PostInstallSrc = Join-Path $ScriptDir "files\Setup-PostInstall.ps1"
if (Test-Path $PostInstallSrc) {
    Copy-Item $PostInstallSrc "$ScriptsDir\Setup-PostInstall.ps1" -Force
}

$SetupComplete = @"
@echo off
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-PostInstall.ps1"
del /q /f "%0"
"@
$SetupComplete | Out-File "$ScriptsDir\SetupComplete.cmd" -Encoding ASCII -Force
Write-Success "Post-install scripts injected"

Dismount-WindowsImage -Path $InstallMount -Save -ErrorAction Stop | Out-Null
Write-Success "Unmounted install.wim"

if ($SkipISO) {
    Write-Step "Skipping ISO creation ( -SkipISO specified)"
    Write-Success "Modified files remain in: $ExtractDir"
} else {
    if (-not $OutputPath) {
        if ($ExtractPath) {
            # Default to current directory with modified ISO name
            $BaseName = Split-Path (Get-Location) -Leaf
            if (-not $BaseName) { $BaseName = "modified" }
            $OutputPath = Join-Path (Get-Location) "$BaseName`_modified.iso"
        } else {
            $OutputPath = [System.IO.Path]::ChangeExtension($ISOPath, "_modified.iso")
        }
    }

    Write-Step "Creating ISO..."
    $BootEtfs = "$ExtractDir\boot\etfsboot.com"
    $BootEfi = "$ExtractDir\efi\microsoft\boot\efisys.bin"

    if (-not (Test-Path $BootEtfs)) { Write-ErrorExit "etfsboot.com not found" }
    if (-not (Test-Path $BootEfi)) { Write-ErrorExit "efisys.bin not found" }

    $BootData = "bootdata:2#p0,e,b$BootEtfs#pEF,e,b$BootEfi"
    $OscdimgArgs = @("-m", "-o", "-u2", "-udfver102", "-l$VolumeLabel", $BootData, $ExtractDir, $OutputPath)
    & $OscdimgPath $OscdimgArgs

    if ($LASTEXITCODE -ne 0) { Write-ErrorExit "ISO creation failed" }
    Write-Success "ISO created: $OutputPath"
}

Write-Step "Cleaning up..."
if ($ExtractPath) {
    Write-Success "Kept extracted folder: $ExtractDir"
} else {
    Safe-RemoveDirectory $TempExtractDir
    Write-Success "Removed temp extraction folder"
}
Safe-RemoveDirectory $MountDir
Write-Success "Removed mount directory"

Write-Host ""
Write-Host "=== SUCCESS ===" -ForegroundColor Green
if ($SkipISO) {
    Write-Host "Modified folder: $ExtractDir" -ForegroundColor White
} else {
    Write-Host "Output: $OutputPath" -ForegroundColor White
}