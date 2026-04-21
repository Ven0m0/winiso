#Requires -Version 5.1
#Requires -RunAsAdministrator

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

    if (!(Test-Path $WimPath)) {
        throw "install.wim/esd not found in ISO"
    }

    dism /Mount-Image /ImageFile:$WimPath /Index:$Index /MountDir:$MountDir | Out-Null

    $appx = @(
        "Microsoft.BingNews",
        "Microsoft.BingWeather",
        "Microsoft.GetHelp",
        "Microsoft.Getstarted",
        "Microsoft.MicrosoftOfficeHub",
        "Microsoft.MicrosoftSolitaireCollection",
        "Microsoft.People",
        "Microsoft.PowerAutomateDesktop",
        "Microsoft.Todos",
        "Microsoft.WindowsAlarms",
        "Microsoft.WindowsFeedbackHub",
        "Microsoft.WindowsMaps",
        "Microsoft.WindowsSoundRecorder",
        "Microsoft.Xbox.TCUI",
        "Microsoft.XboxApp",
        "Microsoft.XboxGameOverlay",
        "Microsoft.XboxGamingOverlay",
        "Microsoft.XboxIdentityProvider",
        "Microsoft.XboxSpeechToTextOverlay",
        "Microsoft.YourPhone",
        "Microsoft.ZuneMusic",
        "Microsoft.ZuneVideo",
        "MicrosoftTeams",
        "Clipchamp.Clipchamp",
        "Microsoft.OutlookForWindows"
    )

    foreach ($p in $appx) {
        try {
            dism /Image:$MountDir /Remove-ProvisionedAppxPackage /PackageName:"$p*" | Out-Null
        } catch {}
    }

    $caps = @(
        "App.Support.QuickAssist*",
        "Hello.Face*",
        "Language.Handwriting*",
        "Language.OCR*",
        "Language.Speech*",
        "MathRecognizer*",
        "Print.Fax.Scan*",
        "Browser.InternetExplorer*"
    )

    foreach ($c in $caps) {
        try {
            dism /Image:$MountDir /Remove-Capability /CapabilityName:$c | Out-Null
        } catch {}
    }

    $features = @(
        "Printing-XPSServices-Features",
        "WorkFolders-Client"
    )

    foreach ($f in $features) {
        try {
            dism /Image:$MountDir /Disable-Feature /FeatureName:$f /Remove | Out-Null
        } catch {}
    }

    reg load HKLM\OFFLINE "$MountDir\Windows\System32\Config\SOFTWARE" | Out-Null

    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\CloudContent /v DisableWindowsConsumerFeatures /t REG_DWORD /d 1 /f | Out-Null
    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\DataCollection /v AllowTelemetry /t REG_DWORD /d 0 /f | Out-Null
    reg add HKLM\OFFLINE\Microsoft\Windows\CurrentVersion\Policies\DataCollection /v AllowTelemetry /t REG_DWORD /d 0 /f | Out-Null
    reg add HKLM\OFFLINE\Policies\Microsoft\Windows\WindowsCopilot /v TurnOffWindowsCopilot /t REG_DWORD /d 1 /f | Out-Null

    reg unload HKLM\OFFLINE | Out-Null

    fsutil 8dot3name strip /f /s $MountDir | Out-Null

    dism.exe /Image:$MountDir /Optimize-ProvisionedAppxPackages | Out-Null

    dism.exe /Image:$MountDir /Cleanup-Image /StartComponentCleanup /ResetBase | Out-Null

    dism /Unmount-Image /MountDir:$MountDir /Commit | Out-Null

    dism /Export-Image /SourceImageFile:$WimPath /SourceIndex:$Index `
        /DestinationImageFile:$EsdPath /Compress:recovery /CheckIntegrity | Out-Null

    Write-Host "Done: $EsdPath"
}
finally {
    try { dism /Cleanup-Mountpoints | Out-Null } catch {}
}
