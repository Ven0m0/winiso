---
paths:
  - "scripts/**/*.ps1"
  - "scripts/**/*.cmd"
  - "PSScriptAnalyzerSettings.psd1"
---

# Windows servicing rules

- Keep `scripts/windows_service.cmd` and the PowerShell helpers scoped to the optional Windows servicing stage; do not make them required for the default Linux build flow.
- Preserve the repository line-ending rules: `*.cmd` stays CRLF, while PowerShell settings and documentation stay normal text files.
- Keep PowerShell paths relative to the repository layout used by the Linux pipeline and the paused servicing handoff.
- Prefer `PSScriptAnalyzer`-compatible changes when touching `*.ps1` files and keep `PSScriptAnalyzerSettings.psd1` aligned with the scripts that actually ship in the repo.
- Do not claim Windows servicing runtime validation unless the edited handoff was exercised on Windows.
