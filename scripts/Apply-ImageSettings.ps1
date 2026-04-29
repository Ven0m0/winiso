#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory=$true)]
    [string]$ISOPath,

    [Parameter(Mandatory=$false)]
    [string]$OutputPath,

    [Parameter(Mandatory=$false)]
    [string]$MountDir
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $ScriptDir "config.ps1"

if (-not (Test-Path $ConfigFile)) {
    Write-Error "Config file not found: $ConfigFile"
    exit 1
}

. $ConfigFile

if (-not $MountDir) { $MountDir = $DefaultMountDir }
if (-not $OutputPath) {
    $OutputPath = [System.IO.Path]::ChangeExtension($ISOPath, "_modified.iso")
}
if (-not $OscdimgPath) {
    $OscdimgPath = Find-Oscdimg
}

function Find-Oscdimg {
    $Paths = @(
        "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe",
        "C:\Program Files (x86)\Windows Kits\11\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
    )
    foreach ($p in $Paths) {
        if (Test-Path $p) { return $p }
    }
    Write-Error "oscdimg.exe not found. Install Windows ADK Deployment Tools."
    exit 1
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

if (-not (Test-Path $ISOPath)) { Write-ErrorExit "ISO not found: $ISOPath" }

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

if (-not (Test-Path "$ExtractDir\sources\boot.wim")) { Write-ErrorExit "boot.wim not found" }
if (-not (Test-Path "$ExtractDir\sources\install.wim")) { Write-ErrorExit "install.wim not found" }

if (-not (Test-Path $MountDir)) {
    New-Item -ItemType Directory -Path $MountDir -Force | Out-Null
}

foreach ($idx in $BootWimIndexes) {
    Write-Step "Processing boot.wim index $idx..."
    $BootMount = Join-Path $MountDir "boot$idx"
    if (Test-Path $BootMount) { Remove-Item $BootMount -Recurse -Force }
    New-Item -ItemType Directory -Path $BootMount -Force | Out-Null

    Mount-WindowsImage -ImagePath "$ExtractDir\sources\boot.wim" -Index $idx -Path $BootMount -Optimize -ErrorAction Stop | Out-Null
    Copy-Item "$ScriptDir\autounattend.xml" "$BootMount\autounattend.xml" -Force
    Write-Success "Copied autounattend.xml to boot.wim index $idx"

    Dismount-WindowsImage -Path $BootMount -Commit -ErrorAction Stop | Out-Null
    Write-Success "Unmounted boot.wim index $idx"
}

Write-Step "Processing install.wim index $InstallWimIndex..."
$InstallMount = Join-Path $MountDir "install"
if (Test-Path $InstallMount) { Remove-Item $InstallMount -Recurse -Force }
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

Dismount-WindowsImage -Path $InstallMount -Commit -ErrorAction Stop | Out-Null
Write-Success "Unmounted install.wim"

Write-Step "Creating ISO..."
$BootEtfs = "$ExtractDir\boot\etfsboot.com"
$BootEfi = "$ExtractDir\efi\microsoft\boot\efisys.bin"

if (-not (Test-Path $BootEtfs)) { Write-ErrorExit "etfsboot.com not found" }
if (-not (Test-Path $BootEfi)) { Write-ErrorExit "efisys.bin not found" }

$BootData = "bootdata:2#p0,e,b$BootEtfs#pEF,e,b$BootEfi"
$Args = @("-m", "-o", "-u2", "-udfver102", "-l$VolumeLabel", $BootData, $ExtractDir, $OutputPath)
& $OscdimgPath $Args

if ($LASTEXITCODE -ne 0) { Write-ErrorExit "ISO creation failed" }
Write-Success "ISO created: $OutputPath"

Write-Step "Cleaning up..."
if (Test-Path $TempExtractDir) { Remove-Item $TempExtractDir -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path $MountDir) { Remove-Item $MountDir -Recurse -Force -ErrorAction SilentlyContinue }
Write-Success "Cleanup complete"

Write-Host ""
Write-Host "=== SUCCESS ===" -ForegroundColor Green
Write-Host "Output: $OutputPath" -ForegroundColor White