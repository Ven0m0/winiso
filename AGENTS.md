# AGENTS.md — Debloated Windows 11 ISO Builder
Canonical guide. `.github/copilot-instructions.md`=short.

## Mission
Build debloated Windows 11 ISO from UUP dumps on Linux. No macOS.

## Invariants
- **AppX keep**: `*Store* *WebView* *VCLibs* *UI.Xaml* *Defender* *DesktopAppInstaller*`
- **Non-root**: `wimlib` FUSE as user
- **Flat UUP**: `uup_files/*.cab|*.esd` no subdirs
- **Converter**: `custom_convert.sh`=upstream patch-only
- **Downloads**: `download_uup.py` via uupdump.net only

## Flow
```bash
make deps -> make download -> make validate -> make build
```

## Files
```
scripts/build.sh          # Main orchestrator
scripts/download_uup.py   # UUP API client (Python3)
scripts/custom_convert.sh # WIM converter (upstream)
scripts/debloat_wim.sh    # AppX removal
scripts/utils.sh          # Shared logging
config/autounattend.xml   # Unattended setup
config/debloat_list.txt   # Debloat patterns
tests/                    # pytest
```

## Shell Scripts
```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils.sh"
```
Rules: Use `log_info|success|warn|error`, no hardcoded paths, `set -euo pipefail`.

## Python (download_uup.py)
- Python 3+ only, stdlib-first
- Stable CLI, no renames
- `aria2c` required
- Path traversal safeguards
- Tests cover safety

## Makefile
- Sync `.PHONY`
- `chmod +x scripts/*.sh` before invoke
- Document in `help`
- Align with `scripts/build.sh` env

## Config
- `autounattend.xml`: UTF-8 no BOM
- `SetupComplete.cmd`: CRLF
- `debloat_list.txt`: Grouped comments, one glob/line

## Validation
```bash
for f in scripts/*.sh; do bash -n "$f"; done
xmllint --noout config/autounattend.xml
python3 -m pytest tests/
make validate
```

## CI/CD
`.github/workflows/`: lint-and-format, test-matrix, build-and-deploy, copilot-setup-steps

## Change Management
- Update `CHANGELOG.md`
- Concise, repo-specific
- Improve vs duplicate

## Platform
- Linux (Arch/Debian/Fedora) primary
- WSL2 for Windows servicing
- No macOS support

## Python Integration
- `mise.toml`: Python 3.14+uv+ruff+pytest
- UV venv auto-create/seed
- Type hints enabled
- Pre-commit hooks

## Plan/TODO
- `PLAN.md`: 52 tasks, 4 tiers, 630h
- `TODO.md`: 50 features, 10 cats

---
*2026-04-29*