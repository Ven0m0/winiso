---
paths:
  - "scripts/windows_service.cmd"
  - "scripts/apply_image_settings.py"
  - "scripts/win_config.py"
  - "scripts/win_utils.py"
  - "scripts/new_iso.py"
  - "scripts/WinUtils.ps1"
  - "scripts/Invoke-SystemCleanup.ps1"
  - "scripts/Remove-ShortNames.ps1"
  - "scripts/Repair-Wim.ps1"
  - "scripts/Mount-WimGui.ps1"
---

# Windows servicing rules

- Keep `scripts/windows_service.cmd`, the Python servicing scripts (`apply_image_settings.py`, `new_iso.py`), and the PowerShell servicing scripts (`Invoke-SystemCleanup.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`, `Mount-WimGui.ps1`) scoped to the optional Windows servicing stage; do not make them required for the default Linux build flow.
- Preserve the repository line-ending rules: `*.cmd` stays CRLF, while Python, PowerShell, and documentation stay normal text files.
- Servicing scripts call `dism.exe` directly — via `subprocess` in Python (see `win_utils.invoke_dism`), via `&`/the call operator in PowerShell (see `WinUtils.ps1`'s `Invoke-Dism`); do not add a PowerShell DISM *module* cmdlet or `pywin32` dependency for something `dism.exe` already does. `powershell.exe` is shelled out to only for `Mount-DiskImage`/`Dismount-DiskImage` in `apply_image_settings.py`, since Python has no stdlib way to mount an ISO on Windows.
- PowerShell servicing scripts dot-source `scripts/WinUtils.ps1` for logging (`Write-Step`/`Write-Success`/`Write-ErrorExit`), admin checks (`Assert-Admin`), and DISM calls (`Invoke-Dism`) — never duplicate these functions in an individual script.
- Keep paths relative to the repository layout used by the Linux pipeline and the paused servicing handoff; adjustable settings (mount dir, oscdimg path, volume label) live in `scripts/win_config.py`.
- Do not claim Windows servicing runtime validation unless the edited handoff was exercised on Windows.
