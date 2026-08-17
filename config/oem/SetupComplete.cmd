@echo off
:: =============================================================================
:: SetupComplete.cmd - Runs after Windows Setup completes (first boot)
:: =============================================================================
:: This script is injected via $OEM$ folder and runs with SYSTEM privileges
:: during the first boot after Windows installation.
::
:: Location after install: C:\Windows\Setup\Scripts\SetupComplete.cmd
:: =============================================================================

:: Log file for debugging
set "LOGFILE=%WINDIR%\Setup\Scripts\SetupComplete.log"
echo [%DATE% %TIME%] SetupComplete.cmd started >> "%LOGFILE%"

:: -----------------------------------------------------------------------------
:: 8.3 Short Name Behavior (per-volume settings)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Configuring 8.3 name behavior... >> "%LOGFILE%"
fsutil behavior set disable8dot3 1 >> "%LOGFILE%" 2>&1
echo 8.3 short name creation disabled for future files >> "%LOGFILE%"

:: -----------------------------------------------------------------------------
:: NTFS Compression (enable capability, don't force)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Configuring NTFS compression... >> "%LOGFILE%"
fsutil behavior set disablecompression 0 >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Component Cleanup (run if not done during servicing)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Running component cleanup... >> "%LOGFILE%"
Dism /Online /Cleanup-Image /StartComponentCleanup >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Power Settings (for Pro for Workstations - High Performance)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Setting High Performance power plan... >> "%LOGFILE%"
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Consumer Experience (Start menu suggestions, etc.)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling consumer experience... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent" /v "DisableWindowsConsumerFeatures" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent" /v "DisableSoftLanding" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent" /v "DisableCloudOptimizedContent" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Reduce Telemetry (Security level - minimum allowed)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Reducing telemetry... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection" /v "AllowTelemetry" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection" /v "AllowTelemetry" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Advertising ID
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling advertising ID... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo" /v "DisabledByGroupPolicy" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Activity History
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling activity history... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\System" /v "EnableActivityFeed" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\System" /v "PublishUserActivities" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\System" /v "UploadUserActivities" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Cortana
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling Cortana... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search" /v "AllowCortana" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Chat and Copilot
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling Chat and Copilot... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Chat" /v "ChatIcon" /t REG_DWORD /d 3 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot" /v "TurnOffWindowsCopilot" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Windows Tips and Suggestions
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling tips and suggestions... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent" /v "DisableTailoredExperiencesWithDiagnosticData" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Web Search in Start Menu
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling web search... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search" /v "DisableWebSearch" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search" /v "ConnectedSearchUseWeb" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Performance: Disable background apps (for non-essential apps)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Configuring background apps... >> "%LOGFILE%"
reg add "HKU\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications" /v "GlobalUserDisabled" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: UI/UX Tweaks
:: -----------------------------------------------------------------------------
:: Classic context menu, ShowTaskViewButton and BingSearchEnabled are per-user
:: values -- they live in ventoy/answer/autounattend.xml's DefaultUser.ps1/
:: UserOnce.ps1 (which write to the loaded default-user hive / real HKCU), not
:: here. HKU\.DEFAULT is the SYSTEM account's own hive; a real user never reads it.
echo [%DATE% %TIME%] Applying UI/UX tweaks... >> "%LOGFILE%"
:: Hide "Recommended" section in Start Menu (best effort)
reg add "HKLM\SOFTWARE\Microsoft\PolicyManager\current\device\Start" /v "HideRecommendedSection" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Windows Update: defer feature updates only, not quality/security updates
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Deferring feature updates... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "DeferFeatureUpdates" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "DeferFeatureUpdatesPeriodInDays" /t REG_DWORD /d 30 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable legacy Remote Assistance (not Remote Desktop/RDP)
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling Remote Assistance... >> "%LOGFILE%"
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Remote Assistance" /v "fAllowToGetHelp" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Disable Customer Experience Improvement Program
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling CEIP... >> "%LOGFILE%"
reg add "HKLM\SOFTWARE\Microsoft\SQMClient\Windows" /v "CEIPEnable" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Clean up temporary files
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Cleaning temporary files... >> "%LOGFILE%"
del /q /f "%TEMP%\*" >> "%LOGFILE%" 2>&1
del /q /f "%WINDIR%\Temp\*" >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] SetupComplete.cmd finished >> "%LOGFILE%"
