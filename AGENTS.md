# AGENTS.md — Debloated Windows 11 ISO Builder

Canonical agent guide. `CLAUDE.md` is a symlink to this file — edit `AGENTS.md`, not `CLAUDE.md`.

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
scripts/apply_image_settings.py     # ISO extraction, unattend injection, debloat, --driver-path injection (Windows-side)
scripts/win_config.py               # Windows servicing config (mount dir, oscdimg path, volume label)
scripts/win_utils.py                # Shared Windows servicing helpers (dism.exe/oscdimg wrappers)
scripts/new_iso.py                  # oscdimg ISO builder (Windows-side)
scripts/validate_xml.py             # XML validator: well-formed, UTF-8 no-BOM, autounattend symlink sync (make/mise validate-xml)
scripts/validate_debloat.py         # config/debloat_list.txt validator: syntax, duplicates, keep-list collisions (make validate-debloat)
scripts/validate_reg_files.py       # .reg header validator: standalone files + embedded reg blocks in autounattend.xml (make validate-reg)
scripts/WinUtils.ps1                # Shared PowerShell helpers (dism.exe wrappers) — dot-source this, never copy
scripts/Invoke-SystemCleanup.ps1    # Live-OS disk cleanup helper (Windows-side, PowerShell)
scripts/Remove-ShortNames.ps1       # 8.3 short-name stripping for install.wim (Windows-side, PowerShell); GUI folder pickers, no boot.wim/Winre.wim handling
scripts/Repair-Wim.ps1              # DISM RestoreHealth against a reference image (Windows-side, PowerShell); GUI file/folder pickers, no hardcoded paths
scripts/Mount-WimGui.ps1            # Native WinForms GUI to pick a WIM + mount folder and run dism /Mount-Image

config/autounattend.xml             # Unattended Windows setup answers (UTF-8, no BOM)
config/debloat_list.txt             # Bloatware glob patterns (grouped by category)
config/oem/SetupComplete.cmd        # First-boot CMD script (CRLF required); injected via $OEM$ and directly by apply_image_settings.py
config/ntlite-presets/*.xml         # NTLite presets — manual alternative path, not consumed by build.py/debloat_wim.py
config/ntlite-presets/InstallApps.cmd # Winget app installer for NTLite's Post-Setup > Commands (After Logon) — not called by any script
config/unattend-generator/apply.reg # Manual TPM/RAM/CPU/SecureBoot bypass + 8.3/power-plan tweaks — companion to the NTLite alternative path, not called by any script
config/unattend-generator/after-logon.cmd # Reference copy of the generator's FirstLogonScript0 (winget installs + powercfg) — not called by any script
config/unattend-generator/system.ps1 # Reference copy of the generator's SystemScript1 (disables Defender realtime/behavior monitoring) — not called by any script
config/component_groups.json        # Named AppX package groups mined from NTLite presets, consumed by validate_debloat.py's `.uup-groups` selection

ventoy/answer/                      # Canonical autounattend.xml source; config/autounattend.xml is a symlink to it

tests/test_download_uup.py          # Unit tests (40+ cases, unittest + mock)
tests/test_security.py              # Path traversal validation tests
docs/autounattend.md                # Autounattend customisation guide

PLAN.md                             # Real remaining work (Next / Someday-maybe)
TODO.md                             # Unevaluated external-repo inspiration links
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
make validate-xml     # validates every *.xml file (well-formed, UTF-8 no BOM) + autounattend symlink sync
make validate-reg     # validates .reg headers (standalone files + embedded in autounattend.xml)
make validate-debloat # validates config/debloat_list.txt: syntax, duplicates, keep-list collisions
```

Equivalent `mise` tasks exist in `mise.toml` (`mise run install-deps`, `mise run test`, `mise run lint`, `mise run lint-shell`, `mise run lint-ps`, `mise run lint-xml`, `mise run lint-biome`, `mise run pwsh-install`) — use whichever entrypoint fits; both call the same underlying scripts/tools.

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
`debloat_wim.py`) and the still-Python Windows servicing scripts (`apply_image_settings.py`,
`new_iso.py`) are Python 3, stdlib-first, cross-platform where the
underlying tools allow it. `scripts/custom_convert.sh` and `scripts/convert_config.sh`
are the one exception — upstream-derived, patch-only, and stay bash. `scripts/utils.sh`
also stays bash, solely because `custom_convert.sh` sources it (`REQUIRED_TOOLS`,
`check_iso_tool`); do not add new Python consumers of it — use `pyutils.py` instead.
`Invoke-SystemCleanup.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`, and `Mount-WimGui.ps1`
are native PowerShell (converted back from Python by user request) — they dot-source
`scripts/WinUtils.ps1` for logging/admin-check/DISM helpers, never duplicate those functions.

### Required shape

Every pipeline script:
- Resolves `SCRIPT_DIR = Path(__file__).resolve().parent` and derives other paths from it — no absolute paths with usernames or machine-specific prefixes.
- `import pyutils` (Linux pipeline) or `import win_utils` / `win_config` (Windows servicing) for logging and tool checks — never duplicate these helpers in a script.
- Returns a process exit code from `main()` via `sys.exit(main())`; no bare `exit()` calls.

### Logging (from `scripts/pyutils.py`)

```python
from pyutils import log_info, log_success, log_warn, log_error, log_debug

check_tool(name)  # returns True/False, logs result
check_required_tools(tools)  # returns count of missing tools
check_iso_tool()  # checks for genisoimage or mkisofs
```

Do not add new logging functions or styles — use what `pyutils.py` (or `win_utils.py` on
the Windows-servicing side) provides.

### Rules

- Never add `sudo`/elevation to `build.py` or any Linux-pipeline script
- Windows servicing scripts call `dism.exe` directly (via `subprocess` in Python, via `&`/call
  operator in PowerShell); do not add a PowerShell DISM *module* cmdlet or `pywin32` dependency
  for something `dism.exe` already does
- Syntax-check after edits: `python -m py_compile scripts/<changed>.py` for Python scripts,
  or `pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('scripts/<changed>.ps1', [ref]$null, [ref]$null)"` for PowerShell scripts
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
- No `ProductKey`/`UserData` element, deliberately: the windowsPE `Microsoft-Windows-Setup`
  component has none. Edition selection instead happens via `dism.exe /Apply-Image`'s
  `/Name:"Windows %OS_VERSION% Pro"` filter (windowsPE Order 20-21), which is how the schneegans
  generator's own "generic key" mode picks an edition from a multi-edition install.wim/install.esd
  without embedding any key at all. Never add a real or unverified product key back into this
  file — if the generator's own output for your settings includes one, replace it with the
  `/Name:` filter approach instead, or drop it and rely on the WIM already being scoped to one
  edition (this repo's Linux pipeline exports a single edition via `custom_convert.sh`).

### `config/oem/SetupComplete.cmd`

- CRLF line endings required (Windows CMD)
- Runs on first Windows boot after installation

### NTLite manual alternative (`config/ntlite-presets/`, `config/unattend-generator/`)

Separate, manual, Windows-only workflow — not consumed by `build.py` or `debloat_wim.py`.
For users who prefer NTLite's GUI over the automated Linux pipeline. **Mutually exclusive with
the Linux pipeline per build**: NTLite generates its own unattend answer file (written to
Panther/boot per the preset's `AnswerFileLocationPanther`/`AnswerFileLocationBoot`), which is a
separate mechanism from `config/autounattend.xml` — Windows Setup reads whichever one physically
ends up at the answer-file location, there's no merge. Never run `apply_image_settings.py` (or
`custom_convert.sh`'s autounattend injection) against a WIM already serviced by NTLite with its
own `<Unattended>` block: it silently overwrites Panther's `unattend.xml`, discarding NTLite's
AutoLogon/OOBE/ProductKey settings (`apply_image_settings.py` now warns before doing this, but
does not block it). NTLite also has its own native power-scheme import feature (`<PowerScheme>`,
e.g. importing a custom `.pow` file); `config/unattend-generator/apply.reg`'s registry-based
`ActivePowerScheme` write targets the same High Performance scheme, so importing both is redundant
but not conflicting.

**Building with NTLite, booting via `ventoy/answer/autounattend.xml`:** supported, but requires
turning off *both* `AnswerFileLocationPanther` and `AnswerFileLocationBoot` in the NTLite preset.
`ventoy/answer/autounattend.xml`'s windowsPE pass has no `<DiskConfiguration>`/`<ImageInstall>` —
it works entirely by having Windows Setup discover it and run its custom `RunSynchronousCommand`
chain (builds and executes a `pe.cmd` that does diskpart + `dism /Apply-Image` + `bcdboot`
manually), which then copies itself into `Windows\Panther\unattend.xml` (windowsPE Order 23) to
also drive the specialize/oobeSystem passes. Windows Setup only ever discovers *one* windowsPE
answer file — if NTLite's own (`AnswerFileLocationBoot=true`) is also written to the boot media,
it wins the race instead, and the pe.cmd chain never runs. With both flags off, NTLite's own
`<Unattended>` block becomes inert everywhere, so its AutoLogon/OOBE settings are ported into
`ventoy/answer/autounattend.xml` directly instead (`SkipAutoActivation`, `NetworkLocation`,
`HideLocalAccountScreen`) — mechanically safe since none of NTLite's `RemoveComponents`/
`Features`/Tweaks in this preset touch WinPE's own binaries (`dism.exe`/`diskpart.exe`/
`bcdboot.exe`/etc.), only the installed OS (install.wim). No `ProductKey` is set or ported —
see the note below.

`config/unattend-generator/` mirrors the scripts embedded in the generator-URL comment at the top
of `ventoy/answer/autounattend.xml` (SystemScript/FirstLogonScript entries) as standalone,
readable files — kept in sync with that comment when the answer file is regenerated. `apply.reg`
there is the NTLite manual-path companion (formerly `scripts/apply.reg`): it now also sets the
High Performance `ActivePowerScheme`, matching the answer file's own tweak — no conflict with
NTLite's native `<PowerScheme>` import is expected since the offline registry write and NTLite's
import both target the same scheme.

1. Mount the install.wim (UUP-converted or vanilla) in NTLite on Windows.
2. Import `config/ntlite-presets/win11.xml` (current target). `win10.xml` targets
   Windows 10 and is kept for reference only.
3. Import `config/unattend-generator/apply.reg` via NTLite's Registry tab (or `regedit`/`chntpw`
   against the mounted hive) to add the bypasses the preset's own `LabConfig` tweaks don't cover
   (`BypassCPUCheck`, `BypassStorageCheck`, `BypassSecureBootCheck`, `BypassNRO`,
   `OOBEBypassNRO`, `BypassMSARequirement`, and the `MoSetup` bypasses) — the preset only
   sets `BypassRAMCheck`/`BypassTPMCheck`.
4. Optional: in NTLite's Post-Setup > Commands, add `config/ntlite-presets/InstallApps.cmd`
   with timing "After Logon" to install software via `winget` on first logon. Edit the
   `PACKAGES` list inside the file before importing; it logs to `%TEMP%\InstallApps.log`.

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
python3 -m pytest tests/ --cov --cov-report=term-missing  # With coverage report (.coveragerc scopes to scripts/)
for f in scripts/*.py; do python3 -m py_compile "$f"; done  # Python syntax check
bash -n scripts/custom_convert.sh scripts/convert_config.sh scripts/utils.sh  # Remaining shell syntax check
xmllint --noout config/autounattend.xml                    # XML validation
ruff check scripts/ tests/                                 # Python lint
python3 scripts/validate_xml.py       # Same check as make/mise validate-xml, over every *.xml file
python3 scripts/validate_debloat.py   # Same check as make/mise validate-debloat
python3 scripts/validate_reg_files.py # Same check as make/mise validate-reg
```

`make validate` runs the full prereq check but requires the `uup_files/` runtime directory to be populated with downloaded UUP packages — do not run in CI without them.

Current test coverage: ~90% of `scripts/download_uup.py` (up from 60% after adding coverage for
`_process_selected_build`, `_prepare_output_directory`, `_prepare_download_list`,
`_run_aria2_download`, and 5 path-traversal tests against the real `_resolve_output_dir()` guard).

---

## CI/CD

Workflows in `.github/workflows/`:

| File | Triggers | Checks |
|------|----------|--------|
| `lint-and-format.yml` | push, PR | ShellCheck, Ruff, xmllint, PSScriptAnalyzer |
| `test-matrix.yml` | push, PR | pytest on Python 3.13 + 3.14 |

No ISO-build or Copilot-setup workflow exists — building the ISO is a local-only `make build` step, not run in CI.

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

Tools managed by `mise.toml`: `python 3.14`, `uv`, `ruff`, `ty`, `shellcheck`, `shfmt`,
`powershell` (needed only for `Mount-DiskImage`/`Dismount-DiskImage` inside
`apply_image_settings.py`; DISM itself is invoked via `dism.exe`, not the PowerShell DISM
module). `basedpyright` is pre-commit-managed only (pinned via `.pre-commit-config.yaml`,
scoped to `scripts/download_uup.py`), not a mise tool. `PSScriptAnalyzer` is a PowerShell
Gallery module, bootstrapped by `mise run pwsh-install` rather than mise itself; its ruleset
lives in `PSScriptAnalyzerSettings.psd1` at the repo root.

```bash
mise run lint         # ruff check + ruff format --check + ty check (scripts/download_uup.py)
mise run lint-shell    # shellcheck + shfmt -d over scripts/{custom_convert,convert_config,utils}.sh
mise run lint-ps       # PSScriptAnalyzer over every *.ps1/*.psm1/*.psd1 (bootstraps the module first)
mise run lint-xml      # scripts/validate_xml.py — well-formed, UTF-8 no-BOM, autounattend symlink sync
mise run lint-reg      # scripts/validate_reg_files.py — .reg headers, standalone + embedded
mise run lint-debloat  # scripts/validate_debloat.py — config/debloat_list.txt syntax/dupes/keep-list
```

System packages (install via `make deps` / `setup_env.py`):
`xmllint`, `aria2c`, `cabextract`, `wimlib-imagex`, `chntpw`, `genisoimage` or `mkisofs`.

---

## Plan & Roadmap

- `PLAN.md` — real remaining work (Next / Someday-maybe); completed work lives in `CHANGELOG.md`, not here
- `TODO.md` — unevaluated external-repo inspiration links only

---

*Updated: 2026-08-17*
