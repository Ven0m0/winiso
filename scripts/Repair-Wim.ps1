#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Repair a mounted install.wim against a known-good reference image.
.DESCRIPTION
    Restored from repair_wim.py / "Repair Wim.cmd". Runs DISM RestoreHealth
    using the reference image as the /Source, then re-optimizes it. Prompts
    for the reference WIM, target WIM, and mount folders via native dialogs
    instead of hardcoded paths.
#>

. "$PSScriptRoot\WinUtils.ps1"
Assert-Admin

Add-Type -AssemblyName System.Windows.Forms

function Select-WimFile {
    param([Parameter(Mandatory)][string]$Title)
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = $Title
    $dialog.Filter = 'WIM images (*.wim)|*.wim|All files (*.*)|*.*'
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-ErrorExit "No file selected: $Title"
    }
    return $dialog.FileName
}

function Select-MountFolder {
    param([Parameter(Mandatory)][string]$Description)
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Description
    $dialog.ShowNewFolderButton = $true
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-ErrorExit "No folder selected: $Description"
    }
    return $dialog.SelectedPath
}

$referenceWim = Select-WimFile 'Select the known-good reference WIM'
$targetWim = Select-WimFile 'Select the target install.wim to repair'
$referenceMountRoot = Select-MountFolder 'Select an empty folder to mount the reference image into'
$mountRoot = Select-MountFolder 'Select an empty folder to mount the target image into'

if (-not (Test-Path -LiteralPath $referenceWim -PathType Leaf)) {
    Write-ErrorExit "Reference WIM not found: $referenceWim"
}
if (-not (Test-Path -LiteralPath $targetWim -PathType Leaf)) {
    Write-ErrorExit "Target WIM not found: $targetWim"
}

Write-Step "Mounting reference image"
Invoke-Dism @('/Mount-Image', "/ImageFile:$referenceWim", '/Index:1', "/MountDir:$referenceMountRoot")

Write-Step "Mounting target image"
Invoke-Dism @('/Mount-Image', "/ImageFile:$targetWim", '/Index:1', "/MountDir:$mountRoot")

Write-Step "Running RestoreHealth against reference source"
Invoke-Dism @("/Image:$mountRoot", '/Cleanup-Image', '/RestoreHealth', "/Source:$(Join-Path $referenceMountRoot 'windows')")

& dism.exe "/Image:$mountRoot" /Optimize-ProvisionedAppxPackages | Out-Null
Invoke-Dism @('/Cleanup-Image', "/Image=$mountRoot", '/StartComponentCleanup', '/ResetBase')

Write-Step "Saving target image"
Invoke-Dism @('/Unmount-Image', "/MountDir:$mountRoot", '/Commit')

Write-Step "Discarding reference mount"
Invoke-Dism @('/Unmount-Image', "/MountDir:$referenceMountRoot", '/Discard')

Invoke-Dism @('/CleanUp-Wim')

Write-Success "Repair complete: $targetWim"
exit 0
