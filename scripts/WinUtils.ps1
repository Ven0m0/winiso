<#
.SYNOPSIS
    Shared helpers for the Windows servicing PowerShell scripts (DISM wrappers).
.DESCRIPTION
    Dot-source this file; do not duplicate these functions in individual scripts.
#>

function Write-Step {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '', Justification = 'Console status message for an interactive admin tool, not pipeline output.')]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[+] $Message"
}

function Write-Success {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '', Justification = 'Console status message for an interactive admin tool, not pipeline output.')]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[OK] $Message"
}

function Write-ErrorExit {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '', Justification = 'Console status message for an interactive admin tool, not pipeline output.')]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[ERROR] $Message"
    exit 1
}

function Assert-Admin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-ErrorExit "This script must be run as Administrator."
    }
}

function Invoke-Dism {
    param([Parameter(Mandatory)][string[]]$Arguments)
    & dism.exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorExit "dism $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}
