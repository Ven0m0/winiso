# AGENTS.md — Debloated Windows 11 ISO Builder
> @.github/copilot-instructions.md

Read this file fully before making any changes. It is the authoritative reference for AI coding agents working in this repository.

---

## Quick Orientation

**What this project does:** Converts UUP (Unified Update Platform) dump files into debloated, unattended Windows 11 ISO images — entirely on Linux.

**Entry point for users:** `Makefile` (run `make help` to see all targets)

**Entry point for the build:** `scripts/build.sh`

**Standard workflow:**
```
make deps → make download → make validate → make build → output/*.iso
```

---

## Critical Constraints — Read First

These rules are non-negotiable. Violating them will break functionality or corrupt ISOs.

### AppX packages you must NEVER remove
When touching `config/debloat_list.txt` or `scripts/debloat_wim.sh`:
```
*Store*              # Microsoft Store
*WebView*            # WebView2 runtime
*VCLibs*             # Visual C++ libraries
*UI.Xaml*            # UWP UI framework
*Defender*           # Windows Defender
*DesktopAppInstaller* # App installer framework
```

### Build must run as a regular user (not root)
`wimlib` FUSE mounts do not require elevation. Never introduce `sudo` or `su` into the main build pipeline.

### UUP files must be at the root of `uup_files/`
`.cab` and `.esd` files go directly in `uup_files/` — **no subdirectories**.

### Do not touch `upstream/`
Files under `upstream/` are reference-only copies of the upstream UUP converter. Treat them as read-only.

---

## Repository Layout

```
config/
  autounattend.xml          # Windows unattended answer file (OOBE bypass)
  debloat_list.txt          # Glob patterns for AppX packages to remove
  README_AUTOUNATTEND.md    # Guide for editing autounattend.xml
  oem/
    SetupComplete.cmd        # First-boot tweaks (telemetry, perf, advertising)

scripts/
  build.sh                  # Main orchestrator — start here
  custom_convert.sh         # Modified UUP → WIM converter (wimlib-based)
  debloat_wim.sh            # Removes AppX packages from install.wim
  download_uup.py           # Interactive UUP downloader (uupdump.net API)
  setup_env.sh              # Installs system deps (Arch / Debian / Fedora)
  validate_prereqs.sh       # Pre-build validation (deps, files, disk space)
  convert_config.sh         # Shared converter config (synced from upstream)
  automerge_open_prs.sh     # GitHub PR auto-merge helper
  utils.sh                  # Color-coded log helpers (source this, don't copy)
  windows_service.cmd       # Optional Windows-side DISM servicing (run as Admin)
  README_DOWNLOAD.md        # Downloader usage docs

tests/
  test_download_uup.py      # Unit tests for download_uup.py

uup_files/                  # INPUT — place .cab / .esd files here (gitignored)
output/                     # OUTPUT — final ISO lands here (gitignored)
upstream/                   # Reference-only upstream converter files (do not modify)
ventoy/                     # Ventoy multi-boot plugin and themes

Makefile                    # Primary user interface
CHANGELOG.md                # Version history (Keep a Changelog format)
```

---

## Build Pipeline (scripts/build.sh)

Steps executed in order:
1. `validate_prereqs.sh` — fail-fast on missing tools or files
2. Detect `.cab`/`.esd` files in `uup_files/`
3. `custom_convert.sh` — UUP → WIM via wimlib
4. Export only the target edition (`ProfessionalWorkstation`, fallback `Professional`)
5. `debloat_wim.sh` — remove apps matching patterns in `config/debloat_list.txt`
6. Inject `autounattend.xml` into ISO root; inject OEM scripts into WIM
7. Optional pause for Windows-side DISM servicing (`PAUSE_FOR_WINDOWS_STAGE=1`)
8. Generate bootable ISO with `genisoimage` / `mkisofs` (auto-detected)

---

## Shell Scripting Standards

Every script in `scripts/` follows these rules — maintain them:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/utils.sh"   # provides log_info, log_success, log_warn, log_error
```

**Log helpers** (always use these — never raw `echo` for user-facing output):
```bash
log_info    "message"   # [INFO]  cyan
log_success "message"   # [OK]    green
log_warn    "message"   # [WARN]  yellow
log_error   "message"   # [ERROR] red
```

**Rules:**
- No hardcoded absolute paths — derive everything from `PROJECT_ROOT`
- Don't swallow errors — let `set -euo pipefail` surface them
- Validate syntax after every edit: `bash -n scripts/<file>.sh`

---

## Configuration Files

### config/debloat_list.txt
- Case-insensitive glob patterns, one per line
- Group patterns under `# category` comment headers
- Patterns are matched against paths in:
  - `/Program Files/WindowsApps/`
  - `/ProgramData/Microsoft/Windows/AppRepository/Packages/`

### config/autounattend.xml
- UTF-8 encoding, **no BOM** — Windows setup is sensitive to both
- Skips OOBE, creates local user, sets telemetry to minimum (Security level)
- Validate before committing: `xmllint --noout config/autounattend.xml`
- Reference: [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/)

### config/oem/SetupComplete.cmd
- Runs as Administrator on first boot after Windows installation
- Applies telemetry, advertising, and performance tweaks
- Must use CRLF line endings (Windows CMD requirement) — enforced by `.gitattributes`

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred Windows edition to export |
| `FALLBACK_EDITION` | `Professional` | Used when target edition is not found in WIM |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Set to `1` to pause build for optional DISM servicing on Windows |

---

## Make Targets

| Target | Purpose |
|---|---|
| `make deps` | Install system dependencies (run once per machine) |
| `make download` | Interactive UUP downloader — fetches files from uupdump.net |
| `make validate` | Pre-build validation; safe to run without UUP files |
| `make build` | Standard build (Pro for Workstations → Pro fallback) |
| `make build-pro` | Forces `Professional` edition |
| `make build-pause` | Pauses before ISO creation for optional Windows DISM step |
| `make clean` | Remove build artifacts (`scripts/ISODIR`, `output/*.iso`) |
| `make help` | Show all available targets |

Adding a new target: add to `.PHONY`, include `chmod +x scripts/*.sh` if invoking shell scripts, document it in the `help` target.

---

## Testing and Validation

### Automated tests
```bash
# Unit tests for download_uup.py
python3 -m pytest tests/
# or
python3 -m unittest discover tests/
```

### Manual validation (no UUP files required)
```bash
# 1. Syntax-check all shell scripts
for f in scripts/*.sh; do bash -n "$f" && echo "OK: $f"; done

# 2. Validate XML
xmllint --noout config/autounattend.xml

# 3. Dry-run prerequisite check
make validate
```

### Full integration test (requires UUP files + ~20 GB free disk)
```bash
make build
```

### CI checks (run locally before pushing)
```bash
shellcheck scripts/*.sh   # excludes custom_convert.sh (upstream)
flake8 scripts/*.py       # max line length: 120
black --check scripts/*.py
```

---

## CI/CD (GitHub Actions)

| Workflow | Trigger | What it does |
|---|---|---|
| `lint-and-format.yml` | push / PR | ShellCheck, Flake8, Black, xmllint |
| `test-matrix.yml` | push / PR | Python unit tests on Ubuntu + macOS, Python 3.9–3.12 |
| `build-and-deploy.yml` | push / PR | Mock build; uploads ISO artifact (7-day retention) |
| `automerge-open-prs.yml` | manual dispatch | Merges open PRs via `scripts/automerge_open_prs.sh` |

All workflows use concurrency groups to cancel in-progress runs on new pushes to the same branch.

**Note:** `custom_convert.sh` is excluded from ShellCheck — it is synced from upstream and not modified directly.

---

## Python (download_uup.py)

- Python 3 only; uses stdlib only (`requests` is optional)
- No root/sudo usage
- Preserve the existing CLI argument interface — do not rename or remove flags
- External dependency: `aria2c` for parallel downloads

---

## Common Pitfalls

| Pitfall | Correct approach |
|---|---|
| Removing a critical AppX pattern | Check the six protected patterns before editing `debloat_list.txt` |
| Running build as root | Build as regular user — FUSE mounts don't need elevation |
| UUP files in a subdirectory | Place `.cab`/`.esd` directly in `uup_files/` |
| Raw `echo` in shell scripts | Use `log_info` / `log_warn` / `log_error` / `log_success` from `utils.sh` |
| Editing `upstream/` files | Those are reference-only — edit `scripts/convert_config.sh` instead |
| Hardcoded absolute paths | Always derive paths from `SCRIPT_DIR` / `PROJECT_ROOT` |
| Forgetting CRLF on `.cmd` files | `.gitattributes` enforces it — don't override |

---

## Out of Scope

Do not add or modify:
- Files under `upstream/` — reference-only
- Any code that contacts Microsoft servers directly (use uupdump.net via `download_uup.py`)
- Any feature requiring root/sudo in the main build pipeline

---

## Versioning

Follow [Keep a Changelog](https://keepachangelog.com/) format. Update `CHANGELOG.md` for every user-facing change. Current version: **1.1.0**
