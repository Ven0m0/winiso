---
paths:
  - "scripts/windows_service.cmd"
  - "scripts/apply_image_settings.py"
  - "scripts/win_config.py"
  - "scripts/win_utils.py"
  - "scripts/invoke_system_cleanup.py"
  - "scripts/new_iso.py"
  - "scripts/remove_short_names.py"
  - "scripts/repair_wim.py"
---

# Windows servicing rules

- Keep `scripts/windows_service.cmd` and the Python servicing scripts (`apply_image_settings.py`, `invoke_system_cleanup.py`, `new_iso.py`, `remove_short_names.py`, `repair_wim.py`) scoped to the optional Windows servicing stage; do not make them required for the default Linux build flow.
- Preserve the repository line-ending rules: `*.cmd` stays CRLF, while Python and documentation stay normal text files.
- Servicing scripts call `dism.exe` directly via `subprocess` (see `win_utils.invoke_dism`); do not add a PowerShell DISM module or `pywin32` dependency for something `dism.exe` already does. `powershell.exe` is shelled out to only for `Mount-DiskImage`/`Dismount-DiskImage` in `apply_image_settings.py`, since Python has no stdlib way to mount an ISO on Windows.
- Keep paths relative to the repository layout used by the Linux pipeline and the paused servicing handoff; adjustable settings (mount dir, oscdimg path, volume label) live in `scripts/win_config.py`.
- Do not claim Windows servicing runtime validation unless the edited handoff was exercised on Windows.
