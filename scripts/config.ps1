# Configuration file for Apply-ImageSettings.ps1
# Adjust these values as needed for your environment

# Path to oscdimg.exe (Windows ADK - Deployment Tools)
# If not found, script will search common locations
$OscdimgPath = $null

# Default mount directory
$DefaultMountDir = "C:\Mount"

# Install.wim index to use (1 = Pro, 2 = Home, etc.)
$InstallWimIndex = 1

# Boot.wim indexes to process (only index 1 exists in standard Windows 11 ISOs)
$BootWimIndexes = @(1)

# ISO Volume Label
$VolumeLabel = "WIN11"

# Temporary extraction directory (auto-cleaned)
$TempExtractDir = "C:\Temp\ISO_Extract"