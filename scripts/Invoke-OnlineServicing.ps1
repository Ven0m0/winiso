#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Build WinPE deployment/capture media, install a WIM into a Hyper-V VM for
    live tweaks, and recapture it - a second, opt-in manual path alongside the
    Linux offline pipeline and the NTLite manual path.
.DESCRIPTION
    Ported from CleanWin11IsoMaker's functions/winpe.ps1 and script.ps1's
    Hyper-V section. Two rewrites were required by AGENTS.md:
      - Every PowerShell DISM *module* cmdlet (Mount-WindowsImage,
        Dismount-WindowsImage, Get-WindowsImage, Export-WindowsImage,
        Add-WindowsPackage) is replaced with Invoke-Dism calling dism.exe -
        the "Servicing DISM-only" invariant applies to this script too.
        Hyper-V/Storage module cmdlets remain permitted (no dism.exe
        equivalent exists for VM/VHD lifecycle).
      - No hardcoded C:\mount-style paths; everything derives from
        $PSScriptRoot or -MountDir.
    Never invoked from build.py - this is a standalone manual workflow,
    mutually exclusive per build with the offline pipeline's WIM (see
    AGENTS.md's NTLite manual-alternative section for the same caveat).
    Stage 5 (live tweaks + sysprep) is interactive by design: the operator
    works inside the VM console, then runs sysprep.bat from the USB-B drive.
.PARAMETER InstallWimPath
    Source install.wim to deploy into the test VM.
.PARAMETER OutputWim
    Where to write the recaptured install.wim.
.PARAMETER InstallersPath
    Optional folder of offline installers copied onto the USB-B scratch disk.
.PARAMETER MountDir
    DISM mount directory for the WinPE boot.wim. Defaults to win_config.py's
    DEFAULT_MOUNT_DIR value.
.PARAMETER VMName
    Name of the throwaway servicing VM.
.EXAMPLE
    pwsh -File scripts/Invoke-OnlineServicing.ps1 -InstallWimPath output\install.wim -OutputWim output\install-serviced.wim
    Runs the full deploy -> live tweak -> capture loop.
#>
param(
    [Parameter(Mandatory)]
    [string]$InstallWimPath,
    [Parameter(Mandatory)]
    [string]$OutputWim,
    [string]$InstallersPath,
    [string]$MountDir = 'C:\Mount',
    [string]$VMName = 'winiso-servicing'
)

. "$PSScriptRoot\HyperVUtils.ps1"
Assert-Admin
Assert-HyperV

if (-not (Test-Path -LiteralPath $InstallWimPath -PathType Leaf)) {
    Write-ErrorExit "install.wim not found: $InstallWimPath"
}

$tempDir = Join-Path $env:TEMP "$VMName-work"
$winPeDir = Join-Path $tempDir 'winpe_amd64'
$vmDir = Join-Path $tempDir 'VM'
$logPath = Join-Path $tempDir 'log.txt'

function Get-AdkRoot {
    $valueName = 'KitsRoot10'
    $candidatePaths = @(
        'HKLM:\Software\Wow6432Node\Microsoft\Windows Kits\Installed Roots',
        'HKLM:\Software\Microsoft\Windows Kits\Installed Roots'
    )
    foreach ($regPath in $candidatePaths) {
        $property = Get-ItemProperty -Path $regPath -Name $valueName -ErrorAction SilentlyContinue
        if ($property) {
            return $property.$valueName
        }
    }
    Write-ErrorExit 'Windows ADK not found. Install the ADK and the WinPE add-on.'
}

function Set-AdkPath {
    $kitsRoot = Get-AdkRoot
    $winPeRoot = Join-Path $kitsRoot 'Assessment and Deployment Kit\Windows Preinstallation Environment'
    $deployRoot = Join-Path $kitsRoot 'Assessment and Deployment Kit\Deployment Tools\amd64'
    if (-not (Test-Path -LiteralPath $winPeRoot)) {
        Write-ErrorExit "WinPE add-on not found under $winPeRoot. Install it via the ADK installer."
    }
    $env:Path = "$deployRoot\DISM;$deployRoot\Oscdimg;$winPeRoot;$env:Path"
    return $winPeRoot
}

function New-WinPeIso {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Deployment', 'Capture')]
        [string]$Type,
        [Parameter(Mandatory)]
        [string]$WinPeRoot
    )
    $winPeOc = Join-Path $winPeRoot 'amd64\WinPE_OCs'
    $packageNames = @(
        'WinPE-WMI', 'WinPE-WDS-Tools', 'WinPE-SecureStartup', 'WinPE-Scripting', 'WinPE-EnhancedStorage'
    )
    $packages = $packageNames | ForEach-Object { Join-Path $winPeOc "$_.cab" }
    $packages += $packageNames | ForEach-Object { Join-Path $winPeOc "en-us\$_`_en-us.cab" }

    if (Test-Path -LiteralPath $winPeDir) {
        Remove-Item -Path $winPeDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Step "Preparing WinPE working copy ($Type)"
    & copype amd64 $winPeDir 2>&1 | Add-Content -Path $logPath
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorExit "copype failed, see $logPath"
    }

    $mountPath = $MountDir
    if (Test-Path -LiteralPath $mountPath) {
        Remove-Item -Path $mountPath -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -Path $mountPath -ItemType Directory -Force | Out-Null
    $bootWim = Join-Path $winPeDir 'media\sources\boot.wim'
    Invoke-Dism @('/Mount-Image', "/ImageFile:$bootWim", '/Index:1', "/MountDir:$mountPath")

    Write-Step 'Adding WinPE packages'
    foreach ($package in $packages) {
        Invoke-Dism @('/Add-Package', "/Image:$mountPath", "/PackagePath:$package")
    }

    $bootBins = Join-Path $winPeDir 'fwfiles'
    $efisysNoPrompt = Join-Path $bootBins 'efisys_noprompt.bin'
    if (Test-Path -LiteralPath $efisysNoPrompt) {
        Copy-Item -Path $efisysNoPrompt -Destination (Join-Path $bootBins 'efisys.bin') -Force
    }
    Add-Content -Path (Join-Path $mountPath 'Windows\System32\startnet.cmd') `
        -Value 'powercfg /s 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'

    New-Item -Path (Join-Path $mountPath 'scripts') -ItemType Directory -Force | Out-Null
    if ($Type -eq 'Deployment') {
        Copy-Item -Path (Join-Path $PSScriptRoot 'winpe\deployment\*') -Destination (Join-Path $mountPath 'scripts') -Recurse
        Add-Content -Path (Join-Path $mountPath 'Windows\System32\startnet.cmd') -Value 'X:\scripts\install.cmd'
        $isoName = 'WinPE_D.iso'
    }
    else {
        Copy-Item -Path (Join-Path $PSScriptRoot 'winpe\capture\*') -Destination (Join-Path $mountPath 'scripts') -Recurse
        Add-Content -Path (Join-Path $mountPath 'Windows\System32\startnet.cmd') -Value 'X:\scripts\capture.cmd'
        $isoName = 'WinPE_C.iso'
    }

    Write-Step 'Cleaning up WinPE image'
    Invoke-Dism @("/Image:$mountPath", '/Cleanup-Image', '/StartComponentCleanup')
    Invoke-Dism @('/Unmount-Image', "/MountDir:$mountPath", '/Commit')

    Write-Step 'Creating WinPE ISO'
    $isoPath = Join-Path $tempDir $isoName
    & MakeWinPEMedia /ISO $winPeDir $isoPath 2>&1 | Add-Content -Path $logPath
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorExit "MakeWinPEMedia failed for $Type, see $logPath"
    }
    Remove-Item -Path $winPeDir -Recurse -Force -ErrorAction SilentlyContinue
    return $isoPath
}

function New-ScratchVhd {
    param([Parameter(Mandatory)][string]$WimPath)
    $vhdPath = Join-Path $vmDir 'USB.vhdx'
    Write-Step 'Creating scratch VHDX (USB-B)'
    New-VHD -Path $vhdPath -SizeBytes 34359738368 -Dynamic | Mount-VHD -Passthru |
        Initialize-Disk -PassThru | New-Partition -AssignDriveLetter -UseMaximumSize |
        Format-Volume -FileSystem NTFS -NewFileSystemLabel 'USB-B' -Confirm:$false -Force | Out-Null
    $driveLetter = (Get-Volume | Where-Object { $_.FileSystemLabel -eq 'USB-B' }).DriveLetter

    New-Item -Path "${driveLetter}:\Images" -ItemType Directory -Force | Out-Null
    Copy-Item -Path $WimPath -Destination "${driveLetter}:\Images\install.wim" -Force
    Set-Content -Path "${driveLetter}:\sysprep.bat" -Value 'C:\Windows\System32\Sysprep\sysprep /oobe /generalize /shutdown'
    if ($InstallersPath -and (Test-Path -LiteralPath $InstallersPath)) {
        Copy-Item -Path $InstallersPath -Destination "${driveLetter}:\Install" -Recurse -Force
    }
    Dismount-VHD -Path $vhdPath
    return $vhdPath
}

function Wait-VmOff {
    param([Parameter(Mandatory)][string]$Name)
    while ((Get-VM -Name $Name).State -ne 'Off') {
        Write-Step 'Waiting for VM to shut down...'
        Start-Sleep -Seconds 5
    }
}

try {
    $winPeRoot = Set-AdkPath
    New-Item -Path $tempDir -ItemType Directory -Force | Out-Null

    $deployIso = New-WinPeIso -Type 'Deployment' -WinPeRoot $winPeRoot
    $captureIso = New-WinPeIso -Type 'Capture' -WinPeRoot $winPeRoot
    $scratchVhd = New-ScratchVhd -WimPath $InstallWimPath

    Write-Step "Creating servicing VM '$VMName'"
    New-TestVm -Name $VMName -Path $vmDir -DiskBytes 68719476736 -MemoryBytes 4294967296 -SecureBoot -Tpm
    Add-VMHardDiskDrive -VMName $VMName -Path $scratchVhd

    Write-Step 'Deployment stage: applying image to VHDX'
    Add-VmDvd -Name $VMName -Path $deployIso
    Start-VM -Name $VMName
    Wait-VmOff -Name $VMName
    Remove-VmDvd -Name $VMName

    Write-Step 'Online modifications stage: make live changes, then run USB-B:\sysprep.bat'
    Start-VM -Name $VMName
    Start-Sleep -Seconds 3
    Start-Process -FilePath 'vmconnect.exe' -ArgumentList 'localhost', $VMName
    Wait-VmOff -Name $VMName

    Write-Step 'Capture stage: recapturing image'
    Add-VmDvd -Name $VMName -Path $captureIso
    Start-VM -Name $VMName
    Wait-VmOff -Name $VMName

    Write-Step 'Copying recaptured image off scratch VHDX'
    $driveLetter = (Mount-VHD -Path $scratchVhd -Passthru | Get-Disk | Get-Partition | Get-Volume |
            Where-Object { $_.FileSystemLabel -eq 'USB-B' }).DriveLetter
    Copy-Item -Path "${driveLetter}:\Images\install.wim" -Destination $OutputWim -Force
    Dismount-VHD -Path $scratchVhd

    Write-Success "Online servicing complete: $OutputWim"
}
finally {
    Write-Step 'Tearing down servicing VM and temp files'
    Remove-TestVm -Name $VMName -Path $vmDir
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
