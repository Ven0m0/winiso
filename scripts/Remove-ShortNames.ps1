#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Strip 8.3 short filenames from a staged ISO's install.wim.
.DESCRIPTION
    Restored from remove_short_names.py, itself a consolidation of "8.3 strip
    all.cmd", "Remove Shortnames.cmd", and "Remove Shortnames -install.cmd".
    Reduced to install.wim only - Winre.wim and boot.wim reprocessing removed.
    Prompts for the ISO root and mount folder via native dialogs instead of
    hardcoded paths.
#>

. "$PSScriptRoot\WinUtils.ps1"
Assert-Admin

Add-Type -AssemblyName System.Windows.Forms

function Select-Folder {
    param([Parameter(Mandatory)][string]$Description)
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Description
    $dialog.ShowNewFolderButton = $true
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-ErrorExit "No folder selected: $Description"
    }
    return $dialog.SelectedPath
}

function Invoke-8dot3Strip {
    param([Parameter(Mandatory)][string]$Path)
    Write-Step "Stripping 8.3 short names under $Path"
    & fsutil 8dot3name strip /f /s $Path | Out-Null
}

$isoRoot = Select-Folder 'Select the staged ISO root (contains sources\install.wim)'
$mountRoot = Select-Folder 'Select an empty folder to mount install.wim into'

New-Item -ItemType Directory -Force -Path $mountRoot | Out-Null

Invoke-Dism @('/CleanUp-Wim', '/quiet')
Invoke-8dot3Strip $isoRoot

$installWim = Join-Path $isoRoot 'sources\install.wim'
$installMount = Join-Path $mountRoot 'install'
New-Item -ItemType Directory -Force -Path $installMount | Out-Null

Write-Step "Mounting install.wim"
Invoke-Dism @('/Mount-Image', "/ImageFile:$installWim", '/Index:1', "/MountDir:$installMount")
Invoke-8dot3Strip $installMount

& dism.exe "/Image:$installMount" /Optimize-ProvisionedAppxPackages | Out-Null
Invoke-Dism @('/Cleanup-Image', "/Image=$installMount", '/StartComponentCleanup')
Invoke-Dism @('/Cleanup-Image', "/Image=$installMount", '/StartComponentCleanup', '/ResetBase')

Write-Step "Removing leftover *.LOG files"
Get-ChildItem -Path $installMount -Filter '*LOG' -Recurse -Force -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Invoke-Dism @('/Unmount-Image', "/MountDir:$installMount", '/Commit')

$installCleaned = Join-Path $isoRoot 'sources\install_cleaned.wim'
Invoke-Dism @('/Export-Image', "/SourceImageFile:$installWim", '/SourceIndex:1', "/DestinationImageFile:$installCleaned", '/Compress:max', '/CheckIntegrity')
Invoke-Dism @('/CleanUp-Wim', '/quiet')

Write-Success "install.wim processed -> $installCleaned"
exit 0
