#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Boot a built ISO in a Hyper-V VM and verify it installs end-to-end.
.DESCRIPTION
    Ported from CleanWin11IsoMaker's functions/hyperv.ps1, with two rewrites
    required by ventoy/answer/autounattend.xml:
      - The disk assertion in the answer file's pe.cmd halts Setup unless disk 0
        is >=100 GiB, so the test VM disk is fixed above that floor regardless
        of profile.
      - The answer file's diskpart stage is preceded by a "pause" (a deliberate
        data-loss guard) and WinPE never reports a Hyper-V heartbeat, so the
        harness injects Enter via Msvm_Keyboard until a full Windows install
        boots and its heartbeat integration service reports OK - the earliest
        point that transitively proves boot, partition, apply-image and
        bcdboot all succeeded.
    On timeout, a best-effort screenshot of the stuck VM is saved next to the
    ISO so the failure is diagnosable without reproducing it interactively.
.PARAMETER IsoPath
    Path to the ISO to test. Defaults to the newest *.iso under output/.
.PARAMETER Profile
    'Bypass' (default) disables vTPM/SecureBoot and uses 2 GB RAM, exercising
    the answer file's BypassTPMCheck/BypassSecureBootCheck/BypassRAMCheck keys.
    'Compliant' enables vTPM/SecureBoot with 4 GB RAM for the normal install path.
.PARAMETER TimeoutMinutes
    Minutes to wait for the heartbeat to report OK before declaring failure.
.PARAMETER VMName
    Name of the throwaway test VM.
.PARAMETER KeepVM
    Skip teardown after the test (for interactive inspection).
.PARAMETER Recreate
    Remove a pre-existing VM of the same name before creating a new one.
.EXAMPLE
    pwsh -File scripts/Test-IsoBoot.ps1 -Profile Bypass -TimeoutMinutes 45
    Boots the newest output/*.iso with TPM/SecureBoot checks bypassed.
#>
param(
    [string]$IsoPath,
    [ValidateSet('Compliant', 'Bypass')]
    [string]$Profile = 'Bypass',
    [int]$TimeoutMinutes = 45,
    [string]$VMName = 'winiso-isotest',
    [switch]$KeepVM,
    [switch]$Recreate
)

. "$PSScriptRoot\HyperVUtils.ps1"
Assert-Admin
Assert-HyperV

$rootDir = Split-Path $PSScriptRoot -Parent
$outputDir = Join-Path $rootDir 'output'
$vmDir = Join-Path $env:TEMP "$VMName-vm"

if (-not $IsoPath) {
    $newestIso = Get-ChildItem -Path $outputDir -Filter '*.iso' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $newestIso) {
        Write-ErrorExit "No ISO found under $outputDir and -IsoPath was not given."
    }
    $IsoPath = $newestIso.FullName
}
if (-not (Test-Path -LiteralPath $IsoPath -PathType Leaf)) {
    Write-ErrorExit "ISO not found: $IsoPath"
}

if ($Recreate) {
    Remove-TestVm -Name $VMName -Path $vmDir
}

# Fixed above the answer file's 100 GiB assert.vbs floor (ventoy/answer/autounattend.xml:46-62).
$diskBytes = 118111600640 # 110 GiB
$profileSpec = if ($Profile -eq 'Compliant') {
    @{ MemoryBytes = 4294967296; SecureBoot = $true; Tpm = $true }
}
else {
    @{ MemoryBytes = 2147483648; SecureBoot = $false; Tpm = $false }
}

try {
    Write-Step "Creating $Profile test VM '$VMName'"
    New-TestVm -Name $VMName -Path $vmDir -DiskBytes $diskBytes `
        -MemoryBytes $profileSpec.MemoryBytes -SecureBoot:$profileSpec.SecureBoot -Tpm:$profileSpec.Tpm

    Write-Step "Attaching ISO and starting VM"
    Add-VmDvd -Name $VMName -Path $IsoPath
    Start-VM -Name $VMName

    $keystrokesWork = $null
    $vmConnectLaunched = $false
    $onPoll = {
        if ($null -eq $keystrokesWork) {
            $keystrokesWork = Send-VmEnterKey -Name $VMName
            if (-not $keystrokesWork -and -not $vmConnectLaunched) {
                Write-Step 'Msvm_Keyboard unavailable; opening vmconnect - press Enter at the diskpart guard prompt'
                Start-Process -FilePath 'vmconnect.exe' -ArgumentList 'localhost', $VMName
                $vmConnectLaunched = $true
            }
        }
        elseif ($keystrokesWork) {
            Send-VmEnterKey -Name $VMName | Out-Null
        }
    }

    Write-Step "Waiting up to $TimeoutMinutes minutes for the install to complete"
    $started = Get-Date
    $passed = Wait-VmHeartbeat -Name $VMName -TimeoutMinutes $TimeoutMinutes -OnPoll $onPoll
    $elapsedMinutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)

    if ($passed) {
        Write-Success "ISO booted and installed in $elapsedMinutes min ($Profile profile): $IsoPath"
        exit 0
    }

    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $screenshotPath = Join-Path $outputDir "isotest-$timestamp.png"
    Save-VmScreenshot -Name $VMName -OutFile $screenshotPath
    Write-ErrorExit "ISO did not finish installing within $TimeoutMinutes min. Screenshot: $screenshotPath"
}
finally {
    if (-not $KeepVM) {
        Write-Step 'Tearing down test VM'
        Remove-TestVm -Name $VMName -Path $vmDir
    }
}
