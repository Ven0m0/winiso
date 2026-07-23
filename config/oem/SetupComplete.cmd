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
:: Strip existing 8.3 short names on all fixed drives
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Stripping existing 8.3 short names... >> "%LOGFILE%"
for /f "skip=1 tokens=1" %%D in ('wmic logicaldisk where "drivetype=3" get deviceid') do (
	if not "%%D"=="" fsutil 8dot3name strip /d %%D /s >> "%LOGFILE%" 2>&1
)

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
:: Disable Hibernate
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Disabling hibernate... >> "%LOGFILE%"
powercfg /hibernate off >> "%LOGFILE%" 2>&1

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
echo [%DATE% %TIME%] Applying UI/UX tweaks... >> "%LOGFILE%"
:: Enable Classic Context Menu
reg add "HKU\.DEFAULT\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32" /f /ve >> "%LOGFILE%" 2>&1
:: Hide Task View Button
reg add "HKU\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "ShowTaskViewButton" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1
:: Disable Bing Search in Start Menu
reg add "HKU\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Search" /v "BingSearchEnabled" /t REG_DWORD /d 0 /f >> "%LOGFILE%" 2>&1
:: Hide "Recommended" section in Start Menu (best effort)
reg add "HKLM\SOFTWARE\Microsoft\PolicyManager\current\device\Start" /v "HideRecommendedSection" /t REG_DWORD /d 1 /f >> "%LOGFILE%" 2>&1

:: -----------------------------------------------------------------------------
:: Clean up temporary files
:: -----------------------------------------------------------------------------
echo [%DATE% %TIME%] Cleaning temporary files... >> "%LOGFILE%"
del /q /f "%TEMP%\*" >> "%LOGFILE%" 2>&1
del /q /f "%WINDIR%\Temp\*" >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] SetupComplete.cmd finished >> "%LOGFILE%"
