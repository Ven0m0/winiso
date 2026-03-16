# GitHub Copilot Instructions

## Project: Debloated Windows 11 ISO Builder

A Linux shell/Python toolset that converts UUP dump files into debloated, unattended Windows 11 ISO images. The build pipeline is driven entirely by `make`.

---

## Architecture

| Layer | Files | Role |
|---|---|---|
| User interface | `Makefile` | All user-facing commands |
| Orchestration | `scripts/build.sh` | Drives the full pipeline |
| Conversion | `scripts/custom_convert.sh` | UUP → WIM via wimlib |
| Debloating | `scripts/debloat_wim.sh` | Removes AppX packages from WIM |
| Validation | `scripts/validate_prereqs.sh` | Pre-build dependency/file checks |
| Downloading | `scripts/download_uup.py` | Interactive UUP fetcher (uupdump.net) |
| Setup | `scripts/setup_env.sh` | Installs system packages |
| Configuration | `config/autounattend.xml` | Windows unattended answer file |
| Configuration | `config/debloat_list.txt` | Glob patterns for app removal |
| First-boot | `config/oem/SetupComplete.cmd` | Post-install tweaks (telemetry, perf) |

---

## Coding Conventions

### Shell Scripts
- Always start with `#!/bin/bash` and `set -euo pipefail`
- Resolve script directory with: `SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"`
- Use the four standard log helpers — **never raw `echo`** for user-facing messages:
  ```bash
  log_info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
  log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
  log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
  log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
  ```
- All paths must derive from `PROJECT_ROOT` — no hardcoded absolute paths
- Validate syntax after any edit: `bash -n scripts/<file>.sh`

### Python (download_uup.py)
- Python 3 only; prefer stdlib; `requests` is optional
- Preserve existing CLI argument interface
- No root/sudo usage

### Makefile
- New targets must be added to the `.PHONY` list
- Include `chmod +x scripts/*.sh` before invoking shell scripts
- Document every new target inside the `help` target

### XML (autounattend.xml)
- Encoding must stay UTF-8, no BOM
- Validate with: `xmllint --noout config/autounattend.xml`

---

## Critical Rules

### Never Remove These AppX Patterns
When editing `config/debloat_list.txt` or `scripts/debloat_wim.sh`:
- `*Store*`
- `*WebView*`
- `*VCLibs*`
- `*UI.Xaml*`
- `*Defender*`
- `*DesktopAppInstaller*`

These are hard dependencies. Removing them will break app installation and system functionality.

### Never Use Root During Build
The main build pipeline must run as a regular user. wimlib FUSE mounts do not require root.

### UUP Files Must Be at the Root of uup_files/
`.cab` and `.esd` files must be placed **directly** in `uup_files/` — not in subdirectories.

---

## Environment Variables

```bash
TARGET_EDITION=ProfessionalWorkstation   # Preferred edition
FALLBACK_EDITION=Professional            # Used if target not found
PAUSE_FOR_WINDOWS_STAGE=0               # Set 1 to pause for DISM servicing
```

---

## Validation Quick Reference

```bash
# Syntax-check all shell scripts
for f in scripts/*.sh; do bash -n "$f" && echo "OK: $f"; done

# Validate answer file XML
xmllint --noout config/autounattend.xml

# Check prerequisites (no UUP files needed)
make validate

# Full build (requires UUP files + ~20 GB free disk space)
make build
```

---

## What NOT to Do

- Do not modify files under `upstream/` — they are reference-only
- Do not add direct calls to Microsoft servers; use uupdump.net via `scripts/download_uup.py`
- Do not introduce `sudo` or `su` calls into the build pipeline
- Do not use `echo` for user-facing output — use the `log_*` helpers
- Do not hardcode paths — derive everything from `SCRIPT_DIR` / `PROJECT_ROOT`
- Do not silently swallow errors — let `set -euo pipefail` surface them

---

## Supported Linux Distributions

Arch Linux, Debian/Ubuntu, Fedora — dependency installer at `scripts/setup_env.sh`.
