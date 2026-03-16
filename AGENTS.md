# AGENTS.md — Debloated Windows 11 ISO Builder

This file gives AI coding agents the context needed to work effectively in this repository. Read it fully before making any changes.

---

## Project Overview

A Linux-based toolset that builds debloated Windows 11 ISO images from UUP (Unified Update Platform) dump files. The pipeline removes bloatware AppX packages, injects an unattended setup answer file (`autounattend.xml`), applies first-boot performance tweaks, and produces a bootable ISO.

**Primary workflow:**
```
make deps → make download → make validate → make build → output/*.iso
```

---

## Repository Layout

```
├── config/
│   ├── autounattend.xml          # Windows unattended setup answer file
│   ├── debloat_list.txt          # Glob patterns for apps to remove
│   ├── README_AUTOUNATTEND.md    # Guidance for editing autounattend.xml
│   └── oem/
│       └── SetupComplete.cmd     # First-boot tweaks (telemetry, perf, etc.)
├── scripts/
│   ├── build.sh                  # Main build orchestrator (entry point)
│   ├── custom_convert.sh         # Modified UUP-to-WIM converter (wimlib-based)
│   ├── debloat_wim.sh            # Removes AppX packages from install.wim
│   ├── download_uup.py           # Interactive UUP downloader (uupdump.net API)
│   ├── setup_env.sh              # Installs system dependencies
│   ├── validate_prereqs.sh       # Pre-build validation checks
│   ├── windows_service.cmd       # Optional Windows-side DISM servicing
│   └── README_DOWNLOAD.md        # Downloader usage documentation
├── uup_files/                    # Input: place .cab / .esd files here
├── output/                       # Output: final ISO appears here
├── upstream/                     # Upstream UUP converter reference files
├── ventoy/                       # Ventoy plugin support files
├── Makefile                      # Primary user interface
└── CHANGELOG.md                  # Version history
```

---

## Key Technical Details

### Build Pipeline (scripts/build.sh)
1. Runs `validate_prereqs.sh` — fails fast on missing deps or files
2. Detects available `.cab`/`.esd` files in `uup_files/`
3. Calls `custom_convert.sh` to convert UUP → WIM using wimlib
4. Exports only the target edition (`ProfessionalWorkstation` or fallback `Professional`)
5. Calls `debloat_wim.sh` to remove apps matching patterns in `config/debloat_list.txt`
6. Injects `autounattend.xml` into ISO root and OEM scripts into WIM
7. Optionally pauses for Windows-side DISM servicing (`PAUSE_FOR_WINDOWS_STAGE=1`)
8. Generates bootable ISO with `genisoimage`/`mkisofs`

### Shell Scripting Standards
- All scripts use `set -euo pipefail` — fail on error, undefined vars, and pipe failures
- Paths resolved via `readlink -f` to handle symlinks correctly
- Color-coded log helpers: `log_info`, `log_success`, `log_warn`, `log_error`
- Test coverage: always run `bash -n script.sh` after edits to validate syntax

### Debloat Logic (scripts/debloat_wim.sh)
- Processes **all** WIM indexes (not just index 1)
- Patterns in `debloat_list.txt` are case-insensitive globs
- CRLF-tolerant config parsing
- **Never remove:** `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`

### Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred Windows edition |
| `FALLBACK_EDITION` | `Professional` | Fallback if target not found |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Set `1` to pause for DISM servicing |

---

## Make Targets

| Target | Command | Notes |
|---|---|---|
| Install deps | `make deps` | Run once per machine |
| Download UUPs | `make download` | Interactive; uses uupdump.net API |
| Validate | `make validate` | Always run before first build |
| Standard build | `make build` | Pro for Workstations → Pro fallback |
| Pro-only build | `make build-pro` | Forces `Professional` edition |
| Servicing build | `make build-pause` | Pauses for optional Windows DISM step |
| Clean artifacts | `make clean` | Removes `scripts/ISODIR`, `output/*.iso` |

---

## Development Guidelines

### When Modifying Shell Scripts
1. Preserve `set -euo pipefail` at the top of every script
2. Use the existing `log_*` helper functions for output — do not `echo` directly
3. Keep path resolution using `SCRIPT_DIR` / `PROJECT_ROOT` pattern
4. Validate syntax after changes: `bash -n scripts/<file>.sh`
5. Do not hardcode absolute paths — all paths derive from `PROJECT_ROOT`

### When Modifying debloat_list.txt
- Use glob patterns only (`*AppName*`)
- Add a comment line (`# category`) before each group
- Never add patterns that match Store, WebView2, VCLibs, Defender, or DesktopAppInstaller

### When Modifying autounattend.xml
- Validate XML before committing: `xmllint --noout config/autounattend.xml`
- Keep encoding as UTF-8 — Windows setup is sensitive to BOM and encoding

### When Modifying download_uup.py
- Python 3 only; uses only stdlib + `requests` (optional) and `aria2c`
- Preserve existing CLI argument interface

### Adding New Make Targets
- Add to the `.PHONY` list at the top of the Makefile
- Mirror the `chmod +x scripts/*.sh` pattern if invoking shell scripts
- Document new targets in the `help` target

---

## Testing

There is no automated test suite. Validation is manual:

```bash
# 1. Syntax-check all shell scripts
for f in scripts/*.sh; do bash -n "$f" && echo "OK: $f"; done

# 2. Validate XML
xmllint --noout config/autounattend.xml

# 3. Dry-run prereq check (no UUP files needed)
make validate

# 4. Full integration test (requires UUP files + ~20GB disk space)
make build
```

---

## Dependencies

**Required Linux tools:**
- `wimlib-imagex` — WIM manipulation
- `aria2c` — parallel file downloads
- `cabextract` — CAB file extraction
- `chntpw` — registry editing
- `genisoimage` or `mkisofs` — ISO creation
- `python3` — download script

**Supported distros:** Arch Linux (pacman), Debian/Ubuntu (apt), Fedora (dnf)

**Disk space:** ~20 GB during build; final ISO is 3–6 GB

---

## Common Pitfalls

- `.cab`/`.esd` files must be **directly** in `uup_files/` — no subdirectories
- Build must run as a regular user, **not** root (wimlib mounts use FUSE)
- `genisoimage` and `mkisofs` are interchangeable; the script auto-detects whichever is present
- Windows servicing script (`windows_service.cmd`) must run as Administrator on Windows

---

## Out of Scope

Do not add or modify:
- The upstream converter files in `upstream/` — these are reference-only
- Any code that contacts Microsoft servers directly (use uupdump.net via the downloader)
- Any feature that requires root/sudo during the main build

---

## Versioning

Follow [Keep a Changelog](https://keepachangelog.com/) format. Update `CHANGELOG.md` for every user-facing change. Current version: **1.1.0**
