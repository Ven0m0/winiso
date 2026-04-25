param(
    [Parameter(Mandatory=$true)][string]$IsoPath,
    [string]$WorkDir = "$PWD\work",
    [int]$Index = 1
)

$ErrorActionPreference = "Stop"

$MountDir = Join-Path $WorkDir "mnt"
$WimPath  = Join-Path $WorkDir "install.wim"
$EsdPath  = Join-Path $WorkDir "install.esd"

New-Item -ItemType Directory -Force -Path $WorkDir, $MountDir | Out-Null

try {
    & 7z e $IsoPath "sources\install.wim" "-o$WorkDir" -y | Out-Null
    if (!(Test-Path $WimPath)) {
        & 7z e $IsoPath "sources\install.esd" "-o$WorkDir" -y | Out-Null
    }

    if (!(Test-Path $WimPath) -and (Test-Path $EsdPath)) {
        dism /Export-Image /SourceImageFile:$EsdPath /SourceIndex:$Index `
            /DestinationImageFile:$WimPath /Compress:max /CheckIntegrity | Out-Null
    }

    dism /Mount-Image /ImageFile:$WimPath /Index:$Index /MountDir:$MountDir | Out-Null

    # Appx removal
    $appx = @("Microsoft.BingNews", "Microsoft.BingWeather", "Microsoft.GetHelp",
        "Microsoft.Getstarted", "Microsoft.MicrosoftOfficeHub",
        "Microsoft.MicrosoftSolitaireCollection", "Microsoft.People",
        "Microsoft.PowerAutomateDesktop", "Microsoft.Todos",
        "Microsoft.WindowsAlarms", "Microsoft.WindowsFeedbackHub",
        "Microsoft.WindowsMaps", "Microsoft.WindowsSoundRecorder",
        "Microsoft.Xbox.TCUI", "Microsoft.XboxApp",
        "Microsoft.XboxGameOverlay", "Microsoft.XboxGamingOverlay",
        "Microsoft.XboxIdentityProvider", "Microsoft.XboxSpeechToTextOverlay",
        "Microsoft.YourPhone", "Microsoft.ZuneMusic", "Microsoft.ZuneVideo",
        "MicrosoftTeams", "Clipchamp.Clipchamp", "Microsoft.OutlookForWindows")
    foreach ($p in $appx) {
        try { dism /Image:$MountDir /Remove-ProvisionedAppxPackage /PackageName:"$p*" | Out-Null } catch {}
    }

    # Capabilities
    $caps = @("App.Support.QuickAssist*", "Hello.Face*", "Language.Handwriting*",
        "Language.OCR*", "Language.Speech*", "MathRecognizer*",
        "Print.Fax.Scan*", "Browser.InternetExplorer*")
    foreach ($c in $caps) {
        try { dism /Image:$MountDir /Remove-Capability /CapabilityName:$c | Out-Null } catch {}
    }

    # Features
    $features = @("Printing-XPSServices-Features", "WorkFolders-Client")
    foreach ($f in $features) {
        try { dism /Image:$MountDir /Disable-Feature /FeatureName:$f /Remove | Out-Null } catch {}
    }

    # Offline registry
    reg load HKLM\OFFLINE "$MountDir\Windows\System32\Config\SOFTWARE" | Out-Null
    reg load HKLM\OFFLINE_SYSTEM "$MountDir\Windows\System32\Config\SYSTEM" | Out-Null

    # Telemetry + consumer features
    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\CloudContent /v DisableWindowsConsumerFeatures /t REG_DWORD /d 1 /f | Out-Null
    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\DataCollection /v AllowTelemetry /t REG_DWORD /d 0 /f | Out-Null
    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\WindowsCopilot /v TurnOffWindowsCopilot /t REG_DWORD /d 1 /f | Out-Null

    # Game + scheduler tuning
    reg add HKLM\OFFLINE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile /v SystemResponsiveness /t REG_DWORD /d 10 /f | Out-Null
    reg add HKLM\OFFLINE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games /v "GPU Priority" /t REG_DWORD /d 8 /f | Out-Null
    reg add HKLM\OFFLINE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games /v "Priority" /t REG_DWORD /d 6 /f | Out-Null

    # Disable GameDVR
    reg add HKLM\OFFLINE\System\GameConfigStore /v GameDVR_Enabled /t REG_DWORD /d 0 /f | Out-Null

    # REMOVE network throttling index entirely
    Remove-ItemProperty -Path "HKLM\OFFLINE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" `
        -Name "NetworkThrottlingIndex" -ErrorAction SilentlyContinue

    # Timer / kernel
    reg add HKLM\OFFLINE_SYSTEM\ControlSet001\Control\Session Manager\kernel /v GlobalTimerResolutionRequests /t REG_DWORD /d 1 /f | Out-Null

    # Services (safe gaming set)
    $services = @("DiagTrack", "dmwappushservice", "WerSvc", "MapsBroker", "lfsvc",
        "SharedAccess", "RetailDemo", "Fax", "XblAuthManager", "XblGameSave",
        "XboxGipSvc", "XboxNetApiSvc")
    foreach ($s in $services) {
        try { reg add "HKLM\OFFLINE_SYSTEM\ControlSet001\Services\$s" /v Start /t REG_DWORD /d 4 /f | Out-Null } catch {}
    }

    reg unload HKLM\OFFLINE | Out-Null
    reg unload HKLM\OFFLINE_SYSTEM | Out-Null

    # File system tweak (optional, low impact)
    fsutil 8dot3name strip /f /s $MountDir | Out-Null

    # Optimize appx provisioning
    dism.exe /Image:$MountDir /Optimize-ProvisionedAppxPackages | Out-Null

    # Component cleanup
    dism.exe /Image:$MountDir /Cleanup-Image /StartComponentCleanup /ResetBase | Out-Null

    dism /Unmount-Image /MountDir:$MountDir /Commit | Out-Null
} finally {
    try { dism /Cleanup-Mountpoints | Out-Null } catch {}
}

Write-Host "Done"
