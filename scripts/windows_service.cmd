@echo off
:: =============================================================================
:: Windows Servicing Script for Debloated ISO Builder
:: =============================================================================
:: This script performs Windows-specific servicing operations that cannot be
:: done on Linux. Run this on a Windows machine with the WIM file accessible.
::
:: Usage: windows_service.cmd [WIM_PATH] [MOUNT_DIR]
::   WIM_PATH  - Path to install.wim (default: C:\ISO\sources\install.wim)
::   MOUNT_DIR - Mount directory (default: C:\mnt)
::
:: Requirements:
::   - Windows 10/11 with DISM
::   - Administrator privileges
::   - Sufficient disk space for mount operations
:: =============================================================================

setlocal EnableDelayedExpansion

:: Configuration
set "WIM_PATH=%~1"
set "MOUNT_DIR=%~2"
set "ISO_DIR=%~3"

if "%WIM_PATH%"=="" set "WIM_PATH=C:\ISO\sources\install.wim"
if "%MOUNT_DIR%"=="" set "MOUNT_DIR=C:\mnt"
if "%ISO_DIR%"=="" for %%F in ("%WIM_PATH%") do set "ISO_DIR=%%~dpF.."

echo.
echo =============================================================================
echo  Windows Servicing Script for Debloated ISO
echo =============================================================================
echo  WIM File:  %WIM_PATH%
echo  Mount Dir: %MOUNT_DIR%
echo  ISO Dir:   %ISO_DIR%
echo =============================================================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Validate WIM exists
if not exist "%WIM_PATH%" (
    echo ERROR: WIM file not found: %WIM_PATH%
    pause
    exit /b 1
)

:: Create mount directory
if not exist "%MOUNT_DIR%" mkdir "%MOUNT_DIR%"

echo [1/10] Cleaning up any previous mount points...
Dism /Cleanup-Mountpoints
DISM /Cleanup-Wim

echo.
echo [2/10] Getting WIM image count...
for /f "tokens=3" %%i in ('DISM /Get-ImageInfo /ImageFile:"%WIM_PATH%" ^| findstr /C:"Index"') do set INDEX_COUNT=%%i

:: Get the actual number of images
for /f %%i in ('DISM /Get-ImageInfo /ImageFile:"%WIM_PATH%" ^| findstr /C:"Index :" ^| find /c /v ""') do set IMAGE_COUNT=%%i

if "%IMAGE_COUNT%"=="" set IMAGE_COUNT=1
echo Found %IMAGE_COUNT% image(s) in WIM file

echo.
echo Starting servicing for all %IMAGE_COUNT% image(s)...
set CURRENT_INDEX=1

:PROCESS_NEXT_INDEX
if %CURRENT_INDEX% GTR %IMAGE_COUNT% goto SERVICING_COMPLETE

echo.
echo ============================================================================
echo Processing Index %CURRENT_INDEX% of %IMAGE_COUNT%
echo ============================================================================

echo.
echo [2/10] Mounting WIM image (Index %CURRENT_INDEX%)...
DISM /Mount-Image /ImageFile:"%WIM_PATH%" /Index:%CURRENT_INDEX% /MountDir:"%MOUNT_DIR%"
if %errorlevel% neq 0 (
    echo ERROR: Failed to mount WIM image index %CURRENT_INDEX%
    pause
    exit /b 1
)

echo.
echo [3/10] Stripping 8.3 short filenames (this may take a while)...
fsutil 8dot3name strip /f /s "%MOUNT_DIR%"
echo 8.3 stripping complete.

echo.
echo [4/10] Optimizing provisioned AppX packages...
DISM.exe /Image:"%MOUNT_DIR%" /Optimize-ProvisionedAppxPackages
echo AppX optimization complete.

echo.
echo [5/10] Running DISM RestoreHealth (offline, may be skipped if no source)...
:: Note: RestoreHealth needs a source for offline images, may fail gracefully
Dism /Image:"%MOUNT_DIR%" /Cleanup-Image /RestoreHealth 2>nul
if %errorlevel% neq 0 (
    echo WARNING: RestoreHealth skipped or failed (normal for offline images without source)
)

echo.
echo [6/10] Running StartComponentCleanup with ResetBase...
Dism /Image:"%MOUNT_DIR%" /Cleanup-Image /StartComponentCleanup /ResetBase
if %errorlevel% neq 0 (
    echo WARNING: StartComponentCleanup may have encountered issues
)

echo.
echo [7/10] Applying registry tweaks for performance and 8.3 prevention...
:: Load offline registry hives
reg load HKLM\OFFLINE_SOFTWARE "%MOUNT_DIR%\Windows\System32\config\SOFTWARE"
reg load HKLM\OFFLINE_SYSTEM "%MOUNT_DIR%\Windows\System32\config\SYSTEM"

:: Disable ResetBase restriction (allow future cleanup)
reg add "HKLM\OFFLINE_SOFTWARE\Microsoft\Windows\CurrentVersion\SideBySide\Configuration" /v "DisableResetbase" /t REG_DWORD /d 0 /f

:: Enable NTFS compression (allow it, don't force it)
reg add "HKLM\OFFLINE_SYSTEM\ControlSet001\Control\FileSystem" /v "NtfsDisableCompression" /t REG_DWORD /d 0 /f
reg add "HKLM\OFFLINE_SYSTEM\ControlSet001\Policies" /v "NtfsDisableCompression" /t REG_DWORD /d 0 /f 2>nul

:: Disable 8.3 name creation for new files
reg add "HKLM\OFFLINE_SYSTEM\ControlSet001\Control\FileSystem" /v "NtfsDisable8dot3NameCreation" /t REG_DWORD /d 1 /f

:: High performance power plan (active from specialize/OOBE onward)
reg add "HKLM\OFFLINE_SYSTEM\ControlSet001\Control\Power\User\PowerSchemes" /v "ActivePowerScheme" /t REG_SZ /d "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c" /f

:: Insider updates without Insider Program (optional - for preview builds)
:: reg add "HKLM\OFFLINE_SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "BranchReadinessLevel" /t REG_DWORD /d 2 /f
:: reg add "HKLM\OFFLINE_SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "ManagePreviewBuilds" /t REG_DWORD /d 1 /f
:: reg add "HKLM\OFFLINE_SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "ManagePreviewBuildsPolicyValue" /t REG_DWORD /d 2 /f

:: Unload offline hives
reg unload HKLM\OFFLINE_SOFTWARE
reg unload HKLM\OFFLINE_SYSTEM
echo Registry tweaks applied.

echo.
echo [8/10] Cleaning up temporary files in ISO directory...
del /s /f /q "%ISO_DIR%\*.log" 2>nul
del /s /f /q "%ISO_DIR%\*.log1" 2>nul
del /s /f /q "%ISO_DIR%\*.log2" 2>nul
del /s /f /q "%ISO_DIR%\*.tmp" 2>nul
del /s /f /q "%ISO_DIR%\*.bak" 2>nul
del /s /f /q "%ISO_DIR%\*.old" 2>nul
del /s /f /q "%ISO_DIR%\*.trace" 2>nul
del /s /f /q "%ISO_DIR%\*.chk" 2>nul
echo Temp files cleaned.

echo.
echo [9/10] Unmounting and committing changes for index %CURRENT_INDEX%...
Dism /Cleanup-Mountpoints
Dism /Unmount-Image /MountDir:"%MOUNT_DIR%" /Commit
if %errorlevel% neq 0 (
    echo ERROR: Failed to unmount/commit image index %CURRENT_INDEX%
    echo Attempting discard...
    Dism /Unmount-Image /MountDir:"%MOUNT_DIR%" /Discard
    pause
    exit /b 1
)

:: Move to next index
set /a CURRENT_INDEX=%CURRENT_INDEX%+1
goto PROCESS_NEXT_INDEX

:SERVICING_COMPLETE
echo.
echo All %IMAGE_COUNT% image(s) have been serviced.

echo.
echo [10/10] Exporting all images to optimized WIM with maximum compression...
set "CLEANED_WIM=%~dp1install_cleaned.wim"

:: Export all indexes
set EXPORT_INDEX=1
:EXPORT_NEXT_INDEX
if %EXPORT_INDEX% GTR %IMAGE_COUNT% goto EXPORT_COMPLETE

echo Exporting index %EXPORT_INDEX% of %IMAGE_COUNT%...
if %EXPORT_INDEX% EQU 1 (
    :: First export creates the file
    Dism /Export-Image /SourceImageFile:"%WIM_PATH%" /SourceIndex:%EXPORT_INDEX% /DestinationImageFile:"%CLEANED_WIM%" /Compress:max /CheckIntegrity
) else (
    :: Subsequent exports append to the file
    Dism /Export-Image /SourceImageFile:"%WIM_PATH%" /SourceIndex:%EXPORT_INDEX% /DestinationImageFile:"%CLEANED_WIM%" /Compress:max /CheckIntegrity
)
if %errorlevel% neq 0 (
    echo ERROR: Failed to export index %EXPORT_INDEX%
    pause
    exit /b 1
)

set /a EXPORT_INDEX=%EXPORT_INDEX%+1
goto EXPORT_NEXT_INDEX

:EXPORT_COMPLETE
echo All %IMAGE_COUNT% image(s) exported successfully.

:: Replace original with cleaned version
echo.
echo Replacing original WIM with cleaned version...
del /f "%WIM_PATH%"
move "%CLEANED_WIM%" "%WIM_PATH%"

echo.
echo Final cleanup...
Dism /Cleanup-Mountpoints
DISM /Cleanup-Wim

echo.
echo =============================================================================
echo  Windows Servicing Complete!
echo =============================================================================
echo  The WIM has been:
echo    - 8.3 short names stripped
echo    - AppX packages optimized
echo    - Component store cleaned (ResetBase)
echo    - Registry tweaks applied
echo    - Exported with maximum compression
echo.
echo  You can now return to the Linux build to generate the final ISO.
echo =============================================================================
pause
