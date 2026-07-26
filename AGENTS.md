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
| **Servicing DISM-only** | Windows servicing scripts shell out to `dism.exe`; no PowerShell DISM module cmdlets |

---

## Repository Layout

Key source files (all paths relative to repo root):

```
scripts/build.py                    # Main orchestrator — runs the full pipeline
scripts/custom_convert.sh           # UUP→WIM converter (upstream-derived, patch-only, stays bash)
scripts/convert_config.sh           # Compression/editions config, sourced by custom_convert.sh (stays bash)
scripts/utils.sh                    # Bash logging/tool-check helpers — kept only as custom_convert.sh's dependency
scripts/debloat_wim.py              # AppX removal + offline registry hardening
scripts/download_uup.py             # UUP API client (Python 3, stdlib-first)
scripts/setup_env.py                # Installs system dependencies (Linux only)
scripts/pyutils.py                  # Shared logging/tool-check helpers (import this, never copy)
scripts/validate_prereqs.py         # Pre-build checks (tools, disk space, UUP files)
scripts/sign_iso.py                 # SHA256/SHA512 checksums + optional GPG signature for the built ISO
scripts/windows_service.cmd         # Optional Windows-side DISM servicing (standalone batch, no Python needed)
scripts/apply_image_settings.py     # ISO extraction, unattend injection, debloat (Windows-side)
scripts/win_config.py               # Windows servicing config (mount dir, oscdimg path, volume label)
scripts/win_utils.py                # Shared Windows servicing helpers (dism.exe/oscdimg wrappers)
scripts/invoke_system_cleanup.py    # Live-OS disk cleanup helper (Windows-side)
scripts/new_iso.py                  # oscdimg ISO builder (Windows-side)
scripts/remove_short_names.py       # 8.3 short-name stripping (Windows-side)
scripts/repair_wim.py               # DISM RestoreHealth against a reference image (Windows-side)

config/autounattend.xml             # Unattended Windows setup answers (UTF-8, no BOM)
config/debloat_list.txt             # Bloatware glob patterns (grouped by category)
config/oem/SetupComplete.cmd        # First-boot CMD script (CRLF required); injected via $OEM$ and directly by apply_image_settings.py
config/ntlite-presets/*.xml         # NTLite presets — manual alternative path, not consumed by build.py/debloat_wim.py
scripts/apply.reg                   # Manual TPM/RAM/CPU/SecureBoot bypass — companion to the NTLite alternative path, not called by any script

ventoy/answer/                      # Canonical autounattend.xml source; config/autounattend.xml is a copy of it

tests/test_download_uup.py          # Unit tests (40+ cases, unittest + mock)
tests/test_security.py              # Path traversal validation tests
docs/autounattend.md                # Autounattend customisation guide

PLAN.md                             # 54 tasks, 4 priority tiers, ~660h total
TODO.md                             # 50-item feature roadmap (v5.0)
CHANGELOG.md                        # Contributor-facing change log
mise.toml                           # Dev env (Python 3.14, ruff, uv, shellcheck)
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
make sign ISO=output/Win11.iso [GPG=1 KEY=<key-id>]  # SHA256/SHA512 (+ optional GPG) for a built ISO
make clean      # Remove build artifacts
make validate-xml  # xmllint check of config/autounattend.xml only
```

Equivalent `mise` tasks exist in `mise.toml` (`mise run install-deps`, `mise run test`, `mise run lint`, `mise run lint-xml`, `mise run lint-biome`, `mise run pwsh-install`) — use whichever entrypoint fits; both call the same underlying scripts/tools.

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
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Pause after WIM export for Windows DISM servicing via `scripts/windows_service.cmd` or `scripts/apply_image_settings.py` |
| `NANO` | `0` | Enable aggressive debloating mode |
| `WIMLIB_IMAGEX_IGNORE_CASE` | `1` | Set automatically by build pipeline |

### Windows Servicing Path (optional)

When `PAUSE_FOR_WINDOWS_STAGE=1`, the build pauses after the WIM is created.
Copy `install.wim` to a Windows machine, run `scripts/windows_service.cmd` against it
(DISM cleanup, 8.3 stripping), then copy the serviced WIM back and resume.

---

## Pipeline Script Rules

The Linux build pipeline (`build.py`, `setup_env.py`, `sign_iso.py`, `validate_prereqs.py`,
`debloat_wim.py`) and the Windows servicing scripts (`apply_image_settings.py`,
`invoke_system_cleanup.py`, `new_iso.py`, `remove_short_names.py`, `repair_wim.py`)
are Python 3, stdlib-first, cross-platform where the
underlying tools allow it. `scripts/custom_convert.sh` and `scripts/convert_config.sh`
are the one exception — upstream-derived, patch-only, and stay bash. `scripts/utils.sh`
also stays bash, solely because `custom_convert.sh` sources it (`REQUIRED_TOOLS`,
`check_iso_tool`); do not add new Python consumers of it — use `pyutils.py` instead.

### Required shape

Every pipeline script:
- Resolves `SCRIPT_DIR = Path(__file__).resolve().parent` and derives other paths from it — no absolute paths with usernames or machine-specific prefixes.
- `import pyutils` (Linux pipeline) or `import win_utils` / `win_config` (Windows servicing) for logging and tool checks — never duplicate these helpers in a script.
- Returns a process exit code from `main()` via `sys.exit(main())`; no bare `exit()` calls.

### Logging (from `scripts/pyutils.py`)

```python
from pyutils import log_info, log_success, log_warn, log_error, log_debug
check_tool(name)                 # returns True/False, logs result
check_required_tools(tools)      # returns count of missing tools
check_iso_tool()                 # checks for genisoimage or mkisofs
```

Do not add new logging functions or styles — use what `pyutils.py` (or `win_utils.py` on
the Windows-servicing side) provides.

### Rules

- Never add `sudo`/elevation to `build.py` or any Linux-pipeline script
- Windows servicing scripts call `dism.exe` directly via `subprocess`; do not add a
  PowerShell DISM module or `pywin32` dependency for something `dism.exe` already does
- Syntax-check after edits: `python -m py_compile scripts/<changed>.py`
- When editing `scripts/debloat_wim.py` or `config/debloat_list.txt`, verify the AppX keep-list is intact
- CLI interface of `scripts/download_uup.py` is stable — do not rename flags or change positional arguments
- Path traversal protection is mandatory in `download_uup.py`; all output paths must be validated against the intended output directory
- Tests in `tests/test_security.py` cover path traversal — do not weaken them
- Type hints required on all new functions
- Lint: `ruff check scripts/ tests/ && ruff format --check scripts/ tests/`
- Type-check: `basedpyright scripts/download_uup.py` (or `ty check`) — other scripts are not yet gated on this

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

### NTLite manual alternative (`config/ntlite-presets/`, `scripts/apply.reg`)

Separate, manual, Windows-only workflow — not consumed by `build.py` or `debloat_wim.py`.
For users who prefer NTLite's GUI over the automated Linux pipeline:

1. Mount the install.wim (UUP-converted or vanilla) in NTLite on Windows.
2. Import `config/ntlite-presets/Win11-25H2.xml` (current target). `Clean10.xml` targets
   Windows 10 and is kept for reference only.
3. Import `scripts/apply.reg` via NTLite's Registry tab (or `regedit`/`chntpw` against the
   mounted hive) to add the bypasses the preset's own `LabConfig` tweaks don't cover
   (`BypassCPUCheck`, `BypassStorageCheck`, `BypassSecureBootCheck`, `BypassNRO`,
   `OOBEBypassNRO`, `BypassMSARequirement`, and the `MoSetup` bypasses) — the preset only
   sets `BypassRAMCheck`/`BypassTPMCheck`.

The presets' `RemoveComponents` AppX entries that map to real bloatware packages have been
mined into `config/debloat_list.txt`/`config/component_groups.json` so the automated
pipeline covers them too (`*GamingApp*`, `*Client.AIX*`, `*CrossDevice*`, `*OutlookPWA*`,
`*Flipgrid*`). DISM-only entries (drivers, keyboard layouts, language packs, print/scan
stacks) were left out — `debloat_wim.py` only deletes `WindowsApps`/`AppRepository` folders
by glob, it doesn't do DISM feature removal.

---

## Testing

```bash
python3 -m pytest tests/ -v                                # All tests
python3 -m pytest tests/ --cov --cov-report=term-missing  # With coverage report
for f in scripts/*.py scripts/files/*.py; do python3 -m py_compile "$f"; done  # Python syntax check
bash -n scripts/custom_convert.sh scripts/convert_config.sh scripts/utils.sh  # Remaining shell syntax check
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
mise trust && mise install   # Install Python 3.14, ruff, shellcheck, ripgrep, prek, etc.
mise run precommit-install   # One-time: install git hooks (prek, same config as pre-commit)
mise run precommit           # Run all .pre-commit-config.yaml hooks against all files
```

`.pre-commit-config.yaml` is run by `prek` (a Rust drop-in replacement, already in `mise.toml`) but
stays plain pre-commit-compatible — `pre-commit run --all-files` / `pre-commit install` work
identically against the same file for contributors without prek. Renovate keeps hook `rev:`
pins current via its `pre-commit` manager (`renovate.json`).

Tools managed by `mise.toml`: `python 3.14`, `uv`, `ruff`, `ty`, `basedpyright`,
`shellcheck`, `shfmt`, `actionlint`, `ripgrep`, `fd`, `powershell` (needed only for
`Mount-DiskImage`/`Dismount-DiskImage` inside `apply_image_settings.py`; DISM itself is
invoked via `dism.exe`, not the PowerShell DISM module).

System packages (install via `make deps` / `setup_env.py`):
`xmllint`, `aria2c`, `cabextract`, `wimlib-imagex`, `chntpw`, `genisoimage` or `mkisofs`.

---

## Plan & Roadmap

- `PLAN.md` — 54 tasks, 4 priority tiers, ~660h total
- `TODO.md` — 50-item feature roadmap (v5.0, 10 categories)
- Priority 1 (0-30d): T003 type hints, T005 log_debug, T006 coverage to 80%
- Priority 2 (30-90d): T007-T015 API + build features
- Priority 3 (90-180d): T020-T041 debloat, post-install, testing
- Priority 4 (180+d): T042-T056 architecture, AI, new features

---

*Updated: 2026-05-15*
