#Requires -Version 5.1
#Requires -RunAsAdministrator

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
    [switch]$SkipISO,

    [Parameter(Mandatory=$false)]
    [switch]$Debloat
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $ScriptDir "config.ps1"

if (-not (Test-Path $ConfigFile)) {
    Write-Error "Config file not found: $ConfigFile"
    exit 1
}

. $ConfigFile

if (-not $ISOPath -and -not $ExtractPath -and -not $Debloat) {
    Write-Host "ERROR: Must specify either -ISOPath, -ExtractPath, or -Debloat" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\Apply-ImageSettings.ps1 -ISOPath <path>           # From ISO"
    Write-Host "  .\Apply-ImageSettings.ps1 -ExtractPath <path>    # From extracted folder"
    Write-Host "  .\Apply-ImageSettings.ps1 -ISOPath <path> -SkipISO  # Modify only, no ISO creation"
    Write-Host "  .\Apply-ImageSettings.ps1 -Debloat -MountDir <path> -WimPath <path> # Debloat WIM directly"
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

if (-not $OscdimgPath -and -not $Debloat) {
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

function Remove-Edge {
    Write-Host "Removing Microsoft Edge..." -ForegroundColor Yellow
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\Edge" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\EdgeCore" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\EdgeUpdate" -Recurse -Force -ErrorAction SilentlyContinue
}

function Remove-Packages {
    Write-Host "Removing Windows Packages..." -ForegroundColor Yellow
    $packages = @(
        "Microsoft-Windows-Hello-Face-Package*",
        "Microsoft-Windows-MSPaint-FoD-Package*",
        "Microsoft-Windows-Notepad-FoD-Package*",
        "Microsoft-Windows-PowerShell-ISE-FOD-Package*",
        "Microsoft-Windows-SnippingTool-FoD-Package*",
        "Microsoft-Windows-StepsRecorder-Package*",
        "Microsoft-Windows-TabletPCMath-Package*",
        "Microsoft-Windows-Wallpaper-Content-Extended-FoD-Package*"
    )
    $allPackages = Get-WindowsPackage -Path $MountDir
    foreach ($p in $packages) {
        $allPackages | Where-Object { $_.PackageName -like $p -and $_.State -eq 'Installed' } | ForEach-Object {
            Remove-WindowsPackage -Path $MountDir -PackageName $_.PackageName -NoRestart
        }
    }
}

function Set-Features {
    Write-Host "Configuring Optional Features..." -ForegroundColor Yellow
    $disable = @(
        "MicrosoftWindowsPowerShellV2Root",
        "MicrosoftWindowsPowerShellV2",
        "WorkFolders-Client",
        "SmbDirect",
        "Printing-PrintToPDFServices-Features",
        "Recall",
        "Microsoft-RemoteDesktopConnection",
        "Printing-Foundation-Features",
        "Printing-Foundation-InternetPrinting-Client"
    )
    foreach ($f in $disable) {
        try { Disable-WindowsOptionalFeature -Path $MountDir -FeatureName $f -NoRestart -ErrorAction Stop } catch { }
    }
    $enable = @("DirectPlay")
    foreach ($f in $enable) {
        try { Enable-WindowsOptionalFeature -Path $MountDir -FeatureName $f -All -NoRestart -ErrorAction Stop } catch { }
    }
}

function Remove-AppxPackages {
    Write-Host "Removing AppX Packages..." -ForegroundColor Yellow
    $appx = @(
        "Clipchamp.Clipchamp*",
        "Microsoft.549981C3F5F10*",
        "Microsoft.BingNews*",
        "Microsoft.BingWeather*",
        "Microsoft.GamingApp*",
        "Microsoft.GetHelp*",
        "Microsoft.Getstarted*",
        "Microsoft.MicrosoftOfficeHub*",
        "Microsoft.MicrosoftSolitaireCollection*",
        "Microsoft.MicrosoftStickyNotes*",
        "Microsoft.Paint*",
        "Microsoft.People*",
        "Microsoft.PowerAutomateDesktop*",
        "Microsoft.ScreenSketch*",
        "Microsoft.SecHealthUI*",
        "Microsoft.StorePurchaseApp*",
        "Microsoft.Todos*",
        "Microsoft.Windows.Photos*",
        "Microsoft.WindowsAlarms*",
        "Microsoft.WindowsCalculator*",
        "Microsoft.WindowsCamera*",
        "microsoft.windowscommunicationsapps*",
        "Microsoft.WindowsFeedbackHub*",
        "Microsoft.WindowsMaps*",
        "Microsoft.WindowsNotepad*",
        "Microsoft.WindowsSoundRecorder*",
        "Microsoft.WindowsStore*",
        "Microsoft.Xbox.TCUI*",
        "Microsoft.XboxGameOverlay*",
        "Microsoft.XboxGamingOverlay*",
        "Microsoft.XboxIdentityProvider*",
        "Microsoft.XboxSpeechToTextOverlay*",
        "Microsoft.YourPhone*",
        "Microsoft.ZuneMusic*",
        "Microsoft.ZuneVideo*",
        "MicrosoftCorporationII.QuickAssist*",
        "MicrosoftWindows.Client.WebExperience*"
    )
    $allAppx = Get-AppxProvisionedAppxPackage -Path $MountDir
    foreach ($p in $appx) {
        $allAppx | Where-Object { $_.DisplayName -like $p } | ForEach-Object {
            try { Remove-AppxProvisionedAppxPackage -Path $MountDir -PackageName $_.PackageName -ErrorAction Stop } catch { }
        }
    }
}

function Remove-Capabilities {
    Write-Host "Removing Capabilities..." -ForegroundColor Yellow
    $capability = @(
        "App.StepsRecorder*",
        "Browser.InternetExplorer*",
        "Hello.Face*",
        "MathRecognizer*",
        "Microsoft.Wallpapers.Extended*",
        "Microsoft.Windows.MSPaint*",
        "Microsoft.Windows.Notepad*",
        "Microsoft.Windows.PowerShell.ISE*",
        "Microsoft.Windows.SnippingTool*",
        "Microsoft.Windows.Wifi.Client*",
        "OneCoreUAP.OneSync*"
    )
    $allCaps = Get-WindowsCapability -Path $MountDir
    foreach ($c in $capability) {
        $allCaps | Where-Object { $_.Name -like $c } | ForEach-Object {
            try { Remove-WindowsCapability -Path $MountDir -Name $_.Name -ErrorAction Stop } catch { }
        }
    }
}

if ($Debloat) {
    if (-not $MountDir -or -not $WimPath) {
        Write-ErrorExit "Debloat mode requires -MountDir and -WimPath"
    }
    if (-not (Test-Path $MountDir)) {
        New-Item -ItemType Directory -Path $MountDir -Force | Out-Null
    }
    if (-not (Test-Path $WimPath)) {
        Write-ErrorExit "WIM file not found: $WimPath"
    }
    Write-Host "Mounting Windows Image..." -ForegroundColor Cyan
    Mount-WindowsImage -ImagePath $WimPath -Index 1 -Path $MountDir

    try {
        Remove-Edge
        Remove-Packages
        Set-Features
        Remove-AppxPackages
        Remove-Capabilities
        Write-Host "Customization complete." -ForegroundColor Green
    }
    finally {
        Write-Host "Dismounting and saving image..." -ForegroundColor Cyan
        Dismount-WindowsImage -Path $MountDir -Save
    }
    exit 0
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

$SetupComplete = "@echo off`nPowerShell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0Setup-PostInstall.ps1\"`ndel /q /f \"%0\"`n"
$SetupComplete | Out-File "$ScriptsDir\SetupComplete.cmd" -Encoding ASCII -Force
Write-Success "Post-install scripts injected"

if ($Debloat) {
    $WorkMount = $InstallMount
} else {
    $WorkMount = $InstallMount
}

Dismount-WindowsImage -Path $WorkMount -Save -ErrorAction Stop | Out-Null
Write-Success "Unmounted install.wim"

if ($SkipISO) {
    Write-Step "Skipping ISO creation ( -SkipISO specified)"
    Write-Success "Modified files remain in: $ExtractDir"
} else {
    if (-not $OutputPath) {
        if ($ExtractPath) {
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