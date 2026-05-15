# AGENTS.md — Debloated Windows 11 ISO Builder

Canonical agent guide. `.github/copilot-instructions.md` is a short summary that defers here.
`CLAUDE.md` is a symlink to this file — edit `AGENTS.md`, not `CLAUDE.md`.

---

## Mission

Build a debloated Windows 11 ISO from UUP dump packages on Linux.
Output: a bootable `.iso` written to the `output/` directory (created at runtime).
No macOS support. No Windows required for the Linux build path.

---

## Hard Invariants — Never Violate

| Rule | Detail |
|------|--------|
| **AppX keep-list** | Never remove: `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*` |
| **Non-root** | `wimlib-imagex` runs as the current user via FUSE — never add `sudo` to the build pipeline |
| **Flat UUP layout** | UUP files land in `uup_files/` as `*.cab` / `*.esd`, no subdirectories (`uup_files/` is a runtime directory, not committed) |
| **Converter is upstream** | `scripts/custom_convert.sh` is patch-only; never rewrite its logic |
| **Download source** | `scripts/download_uup.py` fetches from `uupdump.net` only |
| **XML encoding** | `config/autounattend.xml` must be UTF-8 without BOM |
| **SetupComplete.cmd** | `config/oem/SetupComplete.cmd` must use CRLF line endings |
| **No hardcoded paths** | All scripts derive paths from `SCRIPT_DIR` / `PROJECT_ROOT` |

---

## Repository Layout

Key source files (all paths relative to repo root):

```
scripts/build.sh                    # Main orchestrator — runs the full pipeline
scripts/custom_convert.sh           # UUP→WIM converter (upstream-derived, patch-only)
scripts/debloat_wim.sh              # AppX removal + offline registry hardening
scripts/download_uup.py             # UUP API client (Python 3, stdlib-first)
scripts/setup_env.sh                # Installs system dependencies
scripts/utils.sh                    # Shared logging helpers (source this, never copy)
scripts/validate_prereqs.sh         # Pre-build checks (tools, disk space, UUP files)
scripts/windows_service.cmd         # Optional Windows-side DISM servicing
scripts/Apply-ImageSettings.ps1     # PowerShell image settings (Windows-side)
scripts/config.ps1                  # PowerShell config helper (Windows-side)
scripts/convert_config.sh           # Config conversion helper
scripts/files/Setup-PostInstall.ps1 # First-boot PowerShell script

config/autounattend.xml             # Unattended Windows setup answers (UTF-8, no BOM)
config/debloat_list.txt             # Bloatware glob patterns (grouped by category)
config/oem/SetupComplete.cmd        # First-boot CMD script (CRLF required)

ventoy/answer/                      # Alternative autounattend variants (safe, debloat)

tests/test_download_uup.py          # Unit tests (40+ cases, unittest + mock)
tests/test_security.py              # Path traversal validation tests
docs/autounattend.md                # Autounattend customisation guide

PLAN.md                             # 54 tasks, 4 priority tiers, ~660h total
TODO.md                             # 50-item feature roadmap (v5.0)
CHANGELOG.md                        # Contributor-facing change log
mise.toml                           # Dev env (Python 3.14, ruff, uv, shellcheck)
PSScriptAnalyzerSettings.psd1       # PSScriptAnalyzer lint config
```

Runtime directories created during a build (not committed to git):
- `uup_files/` — UUP `.cab` / `.esd` packages downloaded before building
- `output/` — final ISO written here after a successful build
- `scripts/ISODIR/` — intermediate ISO staging area, deleted after build

---

## Build Flow

```
make deps       # Install: aria2c, cabextract, wimlib-imagex, chntpw, genisoimage/mkisofs
make download   # Fetch UUP packages (written to uup_files/ — runtime dir, not committed)
make validate   # Check tools, disk space, UUP files, config
make build      # Full pipeline (ISO written to output/ — runtime dir, not committed)
```

### Build Variants

| Target | Effect |
|--------|--------|
| `make build` | Default: `TARGET_EDITION=ProfessionalWorkstation`, fallback `Professional` |
| `make build-pro` | Forces `Professional` edition only |
| `make build-nano` | `NANO=1` — aggressive debloating, removes more components |
| `make build-pause` | `PAUSE_FOR_WINDOWS_STAGE=1` — pauses after WIM export for Windows DISM servicing |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred WIM edition name |
| `FALLBACK_EDITION` | `Professional` | Used if target edition not found |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Pause after WIM export for Windows DISM servicing via `scripts/windows_service.cmd` |
| `NANO` | `0` | Enable aggressive debloating mode |
| `WIMLIB_IMAGEX_IGNORE_CASE` | `1` | Set automatically by build pipeline |

### Windows Servicing Path (optional)

When `PAUSE_FOR_WINDOWS_STAGE=1`, the build pauses after the WIM is created.
Copy `install.wim` to a Windows machine, run `scripts/windows_service.cmd` against it
(DISM cleanup, 8.3 stripping), then copy the serviced WIM back and resume.

---

## Shell Script Rules

### Required Prologue

Every script in `scripts/` must start with:

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils.sh"
```

### Logging (from `scripts/utils.sh`)

```bash
log_info "Informational message"
log_success "Step completed"
log_warn "Non-fatal issue"
log_error "Fatal error"
check_tool <name>                       # returns 0/1, logs result
check_required_tools "${REQUIRED_TOOLS[@]}"  # checks all required tools
check_iso_tool                          # checks for genisoimage or mkisofs
```

Do not add new logging functions or styles — use what `utils.sh` provides.

### Rules

- `set -euo pipefail` required in all pipeline scripts except `custom_convert.sh` (upstream-derived; uses `# shellcheck disable` instead): `build.sh`, `debloat_wim.sh`, `setup_env.sh`, `validate_prereqs.sh`
- Derive all paths from `SCRIPT_DIR` / `PROJECT_ROOT` — no absolute paths with usernames or machine-specific prefixes
- Never add `sudo` to `build.sh` or any Linux-pipeline script
- ShellCheck must pass with zero warnings: `shellcheck scripts/*.sh`
- Syntax-check after edits: `bash -n scripts/<changed>.sh`
- When editing `scripts/debloat_wim.sh` or `config/debloat_list.txt`, verify the AppX keep-list is intact

---

## Python Rules (`scripts/download_uup.py`)

- Python 3.14+, stdlib-first — no third-party imports
- `aria2c` is the only external binary it shells out to
- CLI interface is stable — do not rename flags or change positional arguments
- Path traversal protection is mandatory; all output paths must be validated against the intended output directory
- Tests in `tests/test_security.py` cover path traversal — do not weaken them
- Type hints required on all new functions (existing coverage: partial — T003 in PLAN.md)
- Lint: `ruff check scripts/download_uup.py && ruff format --check scripts/download_uup.py`
- Type-check: `basedpyright scripts/download_uup.py` (or `ty check`)

---

## Config Rules

### `config/debloat_list.txt`

- One glob pattern per line
- Group patterns under `# Category` comments
- Never add patterns that could match the AppX keep-list (`*Store*`, `*WebView*`, etc.)

### `config/autounattend.xml`

- UTF-8, no BOM
- Validate before building: `xmllint --noout config/autounattend.xml`
- Reference generator: https://schneegans.de/windows/unattend-generator/

### `config/oem/SetupComplete.cmd`

- CRLF line endings required (Windows CMD)
- Runs on first Windows boot after installation

---

## Testing

```bash
python3 -m pytest tests/ -v                                # All tests
python3 -m pytest tests/ --cov --cov-report=term-missing  # With coverage report
bash -n scripts/*.sh                                       # Shell syntax check
shellcheck scripts/*.sh                                    # Shell lint
xmllint --noout config/autounattend.xml                    # XML validation
ruff check scripts/ tests/                                 # Python lint
```

`make validate` runs the full prereq check but requires the `uup_files/` runtime directory to be populated with downloaded UUP packages — do not run in CI without them.

Current test coverage: ~60% of `scripts/download_uup.py`. Target: 80% (T006).
Uncovered paths: `_process_selected_build`, `_prepare_output_directory`, `_prepare_download_list`, `_run_aria2_download` (happy path).

---

## CI/CD

Workflows in `.github/workflows/`:

| File | Triggers | Checks |
|------|----------|--------|
| `lint-and-format.yml` | push, PR | ShellCheck, Ruff, xmllint |
| `test-matrix.yml` | push, PR | pytest on Python 3.13 + 3.14 |
| `build-and-deploy.yml` | push to main | Full ISO build |
| `copilot-setup-steps.yml` | Copilot | Dev environment setup |

When editing workflows: use minimal `permissions`, pin action refs to exact SHA or version tag, only install tools the repo actually uses.

---

## Change Management

- Update `CHANGELOG.md` for any contributor-facing change (new feature, fix, breaking change)
- Keep entries concise and repo-specific
- Improve existing entries rather than duplicating them

---

## Platform Support

| Platform | Status |
|----------|--------|
| Linux (Arch, Debian, Fedora) | Primary — fully supported |
| WSL2 | Supported for Windows servicing stage only |
| macOS | Not supported |
| Windows (native) | Not supported for the Linux build pipeline |

---

## Development Environment

```bash
mise trust && mise install   # Install Python 3.14, ruff, shellcheck, ripgrep, etc.
```

Tools managed by `mise.toml`: `python 3.14`, `uv`, `ruff`, `ty`, `basedpyright`,
`shellcheck`, `shfmt`, `actionlint`, `ripgrep`, `fd`, `powershell`.

System packages (install via `make deps` / `setup_env.sh`):
`xmllint`, `aria2c`, `cabextract`, `wimlib-imagex`, `chntpw`, `genisoimage` or `mkisofs`.

---

## Plan & Roadmap

- `PLAN.md` — 54 tasks, 4 priority tiers, ~660h total
- `TODO.md` — 45-item feature roadmap (v5.0, 10 categories)
- Priority 1 (0-30d): T003 type hints, T005 log_debug, T006 coverage to 80%
- Priority 2 (30-90d): T007-T015 API + build features
- Priority 3 (90-180d): T020-T041 debloat, post-install, testing
- Priority 4 (180+d): T042-T056 architecture, AI, new features

---

*Updated: 2026-05-15*
