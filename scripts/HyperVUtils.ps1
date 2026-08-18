<#
.SYNOPSIS
    Shared Hyper-V helpers for ISO boot testing and online servicing.
.DESCRIPTION
    Dot-source this file; do not duplicate these functions in individual scripts.
    Wraps Hyper-V module cmdlets (permitted per AGENTS.md - no dism.exe equivalent
    exists for VM lifecycle) plus a small amount of WMI for keystroke injection and
    screenshot capture that the Hyper-V module does not expose.
#>

. "$PSScriptRoot\WinUtils.ps1"

function Assert-HyperV {
    if (-not (Get-Module -ListAvailable -Name Hyper-V)) {
        Write-ErrorExit "Hyper-V PowerShell module not found. Enable the Hyper-V Windows feature."
    }
    $service = Get-Service -Name vmms -ErrorAction SilentlyContinue
    if (-not $service -or $service.Status -ne 'Running') {
        Write-ErrorExit "Hyper-V Virtual Machine Management service (vmms) is not running."
    }
}

function New-TestVm {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][int64]$DiskBytes,
        [Parameter(Mandatory)][int64]$MemoryBytes,
        [switch]$SecureBoot,
        [switch]$Tpm
    )
    if (Get-VM -Name $Name -ErrorAction SilentlyContinue) {
        Write-ErrorExit "VM '$Name' already exists. Pass -Recreate to remove it first."
    }
    New-Item -Path $Path -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null

    $vmParams = @{
        Name               = $Name
        MemoryStartupBytes = $MemoryBytes
        Generation         = 2
        NewVHDPath         = "$Path\$Name.vhdx"
        NewVHDSizeBytes    = $DiskBytes
        Path               = $Path
    }
    New-VM @vmParams -Force | Out-Null
    Set-VM -Name $Name -ProcessorCount 2 -CheckpointType Disabled
    Set-VMFirmware -VMName $Name -EnableSecureBoot ($SecureBoot.IsPresent ? 'On' : 'Off')

    if ($Tpm) {
        try {
            Set-VMKeyProtector -VMName $Name -NewLocalKeyProtector -ErrorAction Stop
            Enable-VMTPM -VMName $Name -ErrorAction Stop
        }
        catch {
            Write-Step "vTPM unavailable on this host ($($_.Exception.Message)); continuing without it."
        }
    }
    Get-VMIntegrationService -VMName $Name | Enable-VMIntegrationService
}

function Remove-TestVm {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Path
    )
    $vm = Get-VM -Name $Name -ErrorAction SilentlyContinue
    if (-not $vm) {
        return
    }
    if ($vm.State -ne 'Off') {
        Stop-VM -Name $Name -TurnOff -Force
        Start-Sleep -Seconds 5
    }
    Remove-VM -Name $Name -Force
    Remove-Item -Path "$Path\$Name.vhdx" -Force -ErrorAction SilentlyContinue
}

function Add-VmDvd {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Path
    )
    Add-VMDvdDrive -VMName $Name -Path $Path -ControllerNumber 0 -ControllerLocation 2
    $dvd = Get-VM -Name $Name | Get-VMDvdDrive -ControllerNumber 0 -ControllerLocation 2
    Set-VMFirmware -VMName $Name -FirstBootDevice $dvd
}

function Remove-VmDvd {
    param([Parameter(Mandatory)][string]$Name)
    $dvd = Get-VM -Name $Name | Get-VMDvdDrive -ControllerNumber 0 -ControllerLocation 2
    if ($dvd) {
        Remove-VMDvdDrive $dvd
    }
}

function Send-VmEnterKey {
    param([Parameter(Mandatory)][string]$Name)
    $vm = Get-VM -Name $Name -ErrorAction SilentlyContinue
    if (-not $vm) {
        return $false
    }
    $keyboard = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_Keyboard `
        -Filter "SystemName='$($vm.Id.Guid)'" -ErrorAction SilentlyContinue
    if (-not $keyboard) {
        return $false
    }
    Invoke-CimMethod -InputObject $keyboard -MethodName TypeKey -Arguments @{ keyCode = [uint32]0x0D } | Out-Null
    return $true
}

function Wait-VmHeartbeat {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][int]$TimeoutMinutes,
        [scriptblock]$OnPoll
    )
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ((Get-Date) -lt $deadline) {
        $heartbeat = Get-VMIntegrationService -VMName $Name -Name Heartbeat -ErrorAction SilentlyContinue
        if ($heartbeat -and $heartbeat.PrimaryStatusDescription -eq 'OK') {
            return $true
        }
        if ($OnPoll) {
            & $OnPoll
        }
        Start-Sleep -Seconds 10
    }
    return $false
}

function Save-VmScreenshot {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$OutFile
    )
    try {
        $vm = Get-VM -Name $Name -ErrorAction Stop
        $vsms = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_VirtualSystemManagementService
        $settings = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_VirtualSystemSettingData `
            -Filter "ConfigurationID='$($vm.Id.Guid)'" -ErrorAction Stop
        $result = Invoke-CimMethod -InputObject $vsms -MethodName GetVirtualSystemThumbnailImage -Arguments @{
            TargetSystem = $settings
            WidthPixels  = [uint16]640
            HeightPixels = [uint16]480
        }
        $bytes = [byte[]]$result.ImageData
        if (-not $bytes -or $bytes.Length -eq 0) {
            return
        }
        Add-Type -AssemblyName System.Drawing
        $bitmap = New-Object System.Drawing.Bitmap(640, 480, [System.Drawing.Imaging.PixelFormat]::Format16bppRgb565)
        $rect = New-Object System.Drawing.Rectangle(0, 0, 640, 480)
        $data = $bitmap.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly, $bitmap.PixelFormat)
        [System.Runtime.InteropServices.Marshal]::Copy($bytes, 0, $data.Scan0, $bytes.Length)
        $bitmap.UnlockBits($data)
        $bitmap.Save($OutFile, [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Dispose()
    }
    catch {
        Write-Step "Screenshot capture failed (non-fatal): $($_.Exception.Message)"
    }
}
