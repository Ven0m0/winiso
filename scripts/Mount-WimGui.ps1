#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Native Windows GUI for mounting an install.wim.
.DESCRIPTION
    Prompts for a WIM file (OpenFileDialog) and a mount folder
    (FolderBrowserDialog), then runs dism.exe /Mount-Image. Uses only
    System.Windows.Forms/System.Drawing (built into Windows) - no extra
    dependencies.
.PARAMETER Index
    WIM image index to mount. Defaults to 1.
#>
param(
    [int]$Index = 1
)

. "$PSScriptRoot\WinUtils.ps1"
Assert-Admin

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$openFile = New-Object System.Windows.Forms.OpenFileDialog
$openFile.Title = 'Select install.wim (or boot.wim)'
$openFile.Filter = 'WIM images (*.wim)|*.wim|All files (*.*)|*.*'
if ($openFile.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    Write-ErrorExit "No WIM file selected."
}
$wimPath = $openFile.FileName

$folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
$folderBrowser.Description = 'Select an empty folder to mount the image into'
$folderBrowser.ShowNewFolderButton = $true
if ($folderBrowser.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    Write-ErrorExit "No mount folder selected."
}
$mountDir = $folderBrowser.SelectedPath

if ((Get-ChildItem -Path $mountDir -Force -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    $confirm = [System.Windows.Forms.MessageBox]::Show(
        "`"$mountDir`" is not empty. DISM requires an empty mount directory. Continue anyway?",
        'Mount folder not empty',
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    if ($confirm -ne [System.Windows.Forms.DialogResult]::Yes) {
        Write-ErrorExit "Aborted: mount folder not empty."
    }
}

Write-Step "Mounting `"$wimPath`" (index $Index) -> `"$mountDir`""
Invoke-Dism @('/Mount-Image', "/ImageFile:$wimPath", "/Index:$Index", "/MountDir:$mountDir")

Write-Success "Mounted."
Start-Process explorer.exe $mountDir

[System.Windows.Forms.MessageBox]::Show(
    "Mounted successfully:`n$wimPath`n->`n$mountDir",
    'Mount complete',
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null
exit 0
