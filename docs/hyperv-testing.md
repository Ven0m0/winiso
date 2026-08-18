# Hyper-V Testing Utilities

`scripts/HyperVUtils.ps1` is a shared PowerShell helper library for VM- and VHD-lifecycle
operations. It is dot-sourced by two consumer scripts and is never run standalone. It itself
dot-sources `scripts/WinUtils.ps1` for logging and admin-check helpers — do not duplicate either
file's functions.

Windows-only. See `AGENTS.md` (canonical repo guide) for the pipeline context these scripts sit
alongside.

## Why this library exists

Two reasons the repo carries a dedicated Hyper-V wrapper instead of calling Hyper-V cmdlets
directly from each consumer script:

1. **Sanctioned rule carve-out.** `AGENTS.md`'s "Servicing DISM-only" invariant normally bans
   PowerShell module cmdlets in favor of shelling out to `dism.exe`. `HyperVUtils.ps1` (and its
   two consumers) are the one exception — there is no `dism.exe` equivalent for VM/VHD lifecycle
   (`New-VM`, `New-VHD`, `Mount-VHD`, ...), so the Hyper-V and Storage modules are used directly.
   The DISM-only rule still applies unchanged to actual image mount/servicing.
2. **WMI operations the Hyper-V module doesn't expose.** Keystroke injection and screenshot
   capture require raw `Msvm_*` WMI calls that have no first-class cmdlet. Centralizing them here
   means both consumer scripts get the same tested implementation instead of two divergent copies.

## Exported functions

| Function | Purpose |
|----------|---------|
| `Assert-HyperV` | Errors out if the Hyper-V PowerShell module isn't installed or the `vmms` service isn't running. |
| `New-TestVm -Name -Path -DiskBytes -MemoryBytes [-SecureBoot] [-Tpm]` | Creates a Generation 2 VM with a new VHDX, 2 vCPUs, checkpoints disabled. Errors if a VM with that name already exists — caller must remove it first. `-Tpm` sets a local key protector and enables vTPM, degrading gracefully (continues without it) if the host doesn't support vTPM. |
| `Remove-TestVm -Name -Path` | Force-stops and deletes the VM plus its VHDX. No-op if the VM doesn't exist. |
| `Add-VmDvd -Name -Path` | Attaches an ISO as a DVD drive on controller 0, location 2, and sets it as the first boot device. |
| `Remove-VmDvd -Name` | Detaches the DVD drive at controller 0, location 2. |
| `Send-VmEnterKey -Name` | Injects an Enter keypress via `Msvm_Keyboard` WMI — works around WinPE/Setup stages that have no other input path. Returns `$false` if the keyboard WMI object isn't available (some VM states). |
| `Wait-VmHeartbeat -Name -TimeoutMinutes [-OnPoll <scriptblock>]` | Polls the Hyper-V heartbeat integration service every 10s until it reports `OK` or the timeout elapses. The optional `-OnPoll` scriptblock runs each iteration (used by callers to keep sending keystrokes). Returns `$true`/`$false`. |
| `Save-VmScreenshot -Name -OutFile` | Grabs a 640x480 PNG thumbnail via WMI. Best-effort — never throws, logs and returns on failure. |

## Consumer 1: `scripts/Test-IsoBoot.ps1`

Mise task: `test-iso`. Windows-only, `#Requires -RunAsAdministrator`.

Boots the newest `output/*.iso` (or `-IsoPath`) in a throwaway VM and waits for the Hyper-V
heartbeat to confirm a full Windows install completed. Heartbeat `OK` is the earliest signal that
transitively proves: the ISO booted, `ventoy/answer/autounattend.xml`'s `pe.cmd` disk assertions
passed, and `dism /Apply-Image` plus `bcdboot` succeeded.

### Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `-IsoPath` | string | newest `output/*.iso` | |
| `-Profile` | `Compliant`\|`Bypass` | `Bypass` | `Bypass`: no vTPM/SecureBoot, 2 GB RAM — exercises the answer file's `BypassTPMCheck`/`BypassSecureBootCheck`/`BypassRAMCheck`. `Compliant`: vTPM+SecureBoot on, 4 GB RAM — normal install path. |
| `-TimeoutMinutes` | int | 45 | |
| `-VMName` | string | `winiso-isotest` | |
| `-KeepVM` | switch | off | Skip teardown for interactive inspection. |
| `-Recreate` | switch | off | Remove a pre-existing same-named VM first. |

### Behavior notes

- Test VM disk is fixed at **110 GiB** (118111600640 bytes) regardless of `-Profile` — the answer
  file's `assert.vbs` refuses to proceed below 100 GiB.
- The answer file's diskpart stage is preceded by a deliberate data-loss-guard `pause`, and WinPE
  itself never reports a Hyper-V heartbeat, so the harness auto-injects Enter via
  `Send-VmEnterKey` on every poll to clear that pause. If `Msvm_Keyboard` isn't available, it falls
  back to launching `vmconnect.exe` so a human can press Enter manually.
- On timeout, saves a screenshot to `output/isotest-<timestamp>.png` for offline diagnosis.
- Exit code 0 on success.

### Example

```powershell
pwsh -File scripts/Test-IsoBoot.ps1 -Profile Bypass -TimeoutMinutes 45
```

Or via mise (Windows only; the task errors out immediately on Linux/macOS):

```
mise run test-iso
```

## Consumer 2: `scripts/Invoke-OnlineServicing.ps1`

Mise task: `online-service`. Windows-only, ADK-gated, `#Requires -RunAsAdministrator`.

A second, opt-in, manual workflow — never invoked from `build.py`, and mutually exclusive per
build with the offline Linux pipeline's WIM (same caveat as the NTLite manual path documented in
`AGENTS.md`). Ported from [CleanWin11IsoMaker](https://github.com/pitomec/CleanWin11IsoMaker)'s
`functions/winpe.ps1` and `script.ps1`. Deploys a given `install.wim` into a Hyper-V VM, pauses for
interactive live tweaks via `vmconnect.exe`, then recaptures the result as a new WIM.

### Parameters

| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| `-InstallWimPath` | yes | — | Source install.wim. |
| `-OutputWim` | yes | — | Where the recaptured WIM is written. |
| `-InstallersPath` | no | — | Folder of offline installers copied onto a scratch VHDX (`USB-B` volume) for use inside the VM. |
| `-MountDir` | no | `C:\Mount` | DISM mount dir for the WinPE boot.wim. |
| `-VMName` | no | `winiso-servicing` | |

### Prerequisites

Windows ADK + WinPE add-on, resolved from the registry
(`HKLM:\Software\Wow6432Node\Microsoft\Windows Kits\Installed Roots` or
`HKLM:\Software\Microsoft\Windows Kits\Installed Roots`, value `KitsRoot10`) — errors out if not
found. Also requires Hyper-V.

### Pipeline stages

1. **Build WinPE media.** `copype` + `dism.exe /Add-Package` add `WinPE-WMI`, `WinPE-WDS-Tools`,
   `WinPE-SecureStartup`, `WinPE-Scripting`, `WinPE-EnhancedStorage` (plus en-us language packs),
   then `MakeWinPEMedia /ISO` produces `WinPE_D.iso` (deployment) and `WinPE_C.iso` (capture).
   Deployment media gets `scripts/winpe/deployment/*` copied in and calls `X:\scripts\install.cmd`
   from `startnet.cmd`; capture media gets `scripts/winpe/capture/*` and calls
   `X:\scripts\capture.cmd`.
2. **Build a scratch VHDX.** 32 GB dynamic, labeled `USB-B`, containing `Images\install.wim`
   (copy of `-InstallWimPath`), a generated `sysprep.bat`
   (`sysprep /oobe /generalize /shutdown`), and optionally `-InstallersPath`'s contents under
   `Install\`.
3. **Apply the image.** Creates a 64 GB, 4 GB RAM, SecureBoot+vTPM servicing VM, attaches the
   scratch VHDX, boots the deployment ISO to apply the image (`Wait-VmOff` polls VM state), then
   removes the DVD.
4. **Interactive tweaks.** Reboots the VM with no DVD attached and opens `vmconnect.exe` for the
   operator to make live changes, then run `USB-B:\sysprep.bat` themselves from inside the VM.
   This stage is interactive by design — there is no automation for the actual tweaks.
5. **Recapture.** Once the VM shuts itself down (post-sysprep), attaches the capture ISO and boots
   again to recapture the image onto the scratch VHDX.
6. **Extract output.** Mounts the scratch VHDX back on the host, copies `Images\install.wim` out
   to `-OutputWim`, tears down the VM and temp files (`$env:TEMP\<VMName>-work`).

### Deviation from upstream

Per `AGENTS.md`'s DISM-only rule, every PowerShell DISM *module* cmdlet from the upstream project
(`Mount-WindowsImage`, `Dismount-WindowsImage`, `Get-WindowsImage`, `Export-WindowsImage`,
`Add-WindowsPackage`) is replaced with `Invoke-Dism` calling `dism.exe` directly. Only Hyper-V and
Storage module cmdlets remain — those have no `dism.exe` equivalent.

### Example

```powershell
pwsh -File scripts/Invoke-OnlineServicing.ps1 -InstallWimPath output\install.wim -OutputWim output\install-serviced.wim
```

`mise run online-service` is a stub that just tells you to run the script directly with its
required params — mise's task syntax can't forward `-InstallWimPath`/`-OutputWim`. Errors on
Linux/macOS, since the workflow is ADK+Hyper-V-only.
