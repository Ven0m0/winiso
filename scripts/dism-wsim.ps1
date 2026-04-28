#Requires -Version 5.1
<#
.SYNOPSIS
    Automated Windows image customization based on nohuto/dism-wsim.
.DESCRIPTION
    This script mounts a Windows image (WIM) and removes Edge, AppX packages,
    capabilities, optional features, and other components as described in
    https://github.com/nohuto/dism-wsim
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$WimPath,

    [Parameter(Mandatory=$true)]
    [string]$MountDir,

    [int]$Index = 1,

    [string]$DriverDir = "",
    [string]$PostInstallFolder = ""
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $MountDir)) {
    New-Item -ItemType Directory -Path $MountDir -Force | Out-Null
}

if (-not (Test-Path $WimPath)) {
    throw "WIM file not found at: $WimPath"
}

Write-Host "Mounting Windows Image (Index $Index) to $MountDir..." -ForegroundColor Cyan
Mount-WindowsImage -ImagePath $WimPath -Index $Index -Path $MountDir

try {
    # 1. Removing Edge
    Write-Host "Removing Microsoft Edge..." -ForegroundColor Yellow
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\Edge" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\EdgeCore" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$MountDir\Program Files (x86)\Microsoft\EdgeUpdate" -Recurse -Force -ErrorAction SilentlyContinue

    # 2. Removing Packages
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
    foreach ($p in $packages) {
        Get-WindowsPackage -Path $MountDir | Where-Object { $_.PackageName -like $p -and $_.State -eq 'Installed' } | ForEach-Object {
            Remove-WindowsPackage -Path $MountDir -PackageName $_.PackageName -NoRestart
        }
    }

    # 3. Disabling Features
    Write-Host "Disabling Optional Features..." -ForegroundColor Yellow
    $featuredisable = @(
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
    foreach ($f in $featuredisable) {
        try { Disable-WindowsOptionalFeature -Path $MountDir -FeatureName $f -NoRestart -ErrorAction Stop } catch { Write-Warning "Could not disable feature $f" }
    }

    # 4. Enabling Features
    Write-Host "Enabling Optional Features..." -ForegroundColor Yellow
    $featureenable = @(
        "DirectPlay"
    )
    foreach ($f in $featureenable) {
        try { Enable-WindowsOptionalFeature -Path $MountDir -FeatureName $f -All -NoRestart -ErrorAction Stop } catch { Write-Warning "Could not enable feature $f" }
    }

    # 5. Removing AppX Packages
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
    foreach ($p in $appx) {
        Get-AppxProvisionedAppxPackage -Path $MountDir | Where-Object { $_.DisplayName -like $p } | ForEach-Object {
            try { Remove-AppxProvisionedAppxPackage -Path $MountDir -PackageName $_.PackageName -ErrorAction Stop } catch {}
        }
    }

    # 6. Removing Capabilities
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
    foreach ($c in $capability) {
        Get-WindowsCapability -Path $MountDir | Where-Object { $_.Name -like $c } | ForEach-Object {
            try { Remove-WindowsCapability -Path $MountDir -Name $_.Name -ErrorAction Stop } catch {}
        }
    }

    # 7. Add Drivers
    if ($DriverDir -and (Test-Path $DriverDir)) {
        Write-Host "Adding Drivers from $DriverDir..." -ForegroundColor Yellow
        Add-WindowsDriver -Path $MountDir -Driver $DriverDir -Recurse -ForceUnsigned
    }

    # 8. Copy Post Install Folder
    if ($PostInstallFolder -and (Test-Path $PostInstallFolder)) {
        Write-Host "Copying Installation folder to MountDir..." -ForegroundColor Yellow
        Copy-Item $PostInstallFolder -Destination $MountDir -Recurse -Force
    }

    Write-Host "Customization complete." -ForegroundColor Green
}
finally {
    Write-Host "Dismounting and saving image..." -ForegroundColor Cyan
    Dismount-WindowsImage -Path $MountDir -Save
}
