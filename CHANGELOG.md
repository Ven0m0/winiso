# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- Fixed a gap in the `RunSynchronousCommand` `<Order>` sequence in `ventoy/answer/autounattend.xml`'s WindowsPE pass (jumped from 20 to 22, and 24 to 26) left over from a prior edit that removed commands without renumbering the rest. Windows Setup requires these values to be contiguous starting at 1; the gap silently truncated the WindowsPE command chain after disk formatting, skipping image apply, bcdboot, driver injection, and the post-format reboot. Also fixed stray non-indented markup and trailing blank lines introduced by the same edit. Re-synced `config/autounattend.xml` to the corrected canonical copy, which carried the same class of gap.
- Made the WindowsPE `diskpart.exe` and `dism.exe /Apply-Image` steps in `ventoy/answer/autounattend.xml` / `config/autounattend.xml` retry once (after a 5s pause) instead of aborting setup on the first failure, since both can fail transiently right after boot (disk not yet settled, USB enumeration races). If the retry also fails, setup still exits with `pause`/`exit /b 1` (the on-screen diskpart/dism error is preserved either way) rather than continuing on an unformatted or partially-applied disk.

### Changed
- Converted the Linux build pipeline (`build.sh`, `setup_env.sh`, `sign_iso.sh`, `validate_prereqs.sh`, `debloat_wim.sh`) and the Windows servicing scripts (`Apply-ImageSettings.ps1`, `config.ps1`, `ps-utils.ps1`, `Invoke-SystemCleanup.ps1`, `New-Iso.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`, `Setup-PostInstall.ps1`) to Python for cross-platform maintainability. New modules: `pyutils.py`, `build.py`, `setup_env.py`, `sign_iso.py`, `validate_prereqs.py`, `debloat_wim.py`, `win_config.py`, `win_utils.py`, `apply_image_settings.py`, `invoke_system_cleanup.py`, `new_iso.py`, `remove_short_names.py`, `repair_wim.py`, `files/setup_post_install.py`. Windows servicing now shells out to `dism.exe` directly instead of the PowerShell DISM module. `custom_convert.sh`, `convert_config.sh`, and `utils.sh` (its dependency) stay bash — `custom_convert.sh` is upstream-derived and patch-only; its debloat hook now calls `debloat_wim.py` via `python3`. Removed the now-unused `PSScriptAnalyzerSettings.psd1` and the `mise.toml` `pwsh-install`/pwsh-essentials tasks. Updated `Makefile`, `mise.toml`, `README.md`, `AGENTS.md`, and the `.claude`/`.github` rule files accordingly.
- Consolidated the five `ventoy/answer/*.xml` autounattend variants (main, `-simple`, and three `old/` ancestors) into a single corrected `ventoy/answer/autounattend.xml`: dropped the conflicting Winhance debloat layer in favor of the schneegans-style script suite + winget install list, removed dead x86/arm64 Setup stubs, fixed a duplicate `FirstLogon.ps1` file entry that silently overwrote itself, fixed a duplicate `RunSynchronous` reboot order, removed an invalid placeholder `ProductKey`, and corrected `AutoLogon` `LogonCount` for the actual post-install reboot chain. `config/autounattend.xml` is now a copy of this file so the Linux UUP-dump build pipeline injects it too.
- Converted `iso-cmd/*.cmd` WIM-servicing scripts to PowerShell. Merged the three near-duplicate 8.3-shortname-stripping scripts into one parameterized `iso-cmd/Remove-ShortNames.ps1` (`-InstallOnly`, `-IncludeWinre` switches); converted `Repair Wim.cmd` -> `Repair-Wim.ps1`, `ISO.cmd` -> `New-Iso.ps1`, and `Cleanup.cmd` -> `Invoke-SystemCleanup.ps1` (fixing undefined `%REG%`/`%LOGPATH%`/`%WIN_VER%` variables the original never defined). Removed `Commands.cmd` (unrunnable wimlib scratch notes).
- Synced `config/component_groups.json` groups with `config/debloat_list.txt` patterns that had drifted out of the JSON groups (Utilities, Dev Tools, Extensions/Codecs sections folded into the `system`/`media` groups).
- Folded the placeholder `config/TODO.md` reference link into the root `TODO.md`.

### Added
- Documented `config/ntlite-presets/*.xml` and `scripts/apply.reg` as a manual, Windows-only
  NTLite alternative to the automated build pipeline (`AGENTS.md` Config Rules, `README.md`).
  Neither was previously referenced by any script or doc.
- Mined the NTLite presets' `RemoveComponents` AppX entries that map to real bloatware
  packages into `config/debloat_list.txt`/`config/component_groups.json`: `*GamingApp*`
  (Xbox app's newer package identity, not matched by `*Xbox*`), `*Client.AIX*` (Windows
  Copilot Feature Experience Pack, not matched by `*Copilot*`), `*CrossDevice*`,
  `*OutlookPWA*`, `*Flipgrid*`, plus two opt-in/commented entries (`*WidgetsPlatformRuntime*`,
  `*ParentalControls*`) paired with the existing Widgets/Family opt-in lines. Left out
  DISM-only entries (drivers, keyboard layouts, language packs) — outside what
  `debloat_wim.py`'s glob-based `WindowsApps` deletion can act on.
- Added delta downloads support (T008): `--delta-from <build_id>` and `--delta-store <dir>` CLI flags for downloading only files added or modified compared to a previous build, plus `--save-delta-manifest` and `--delta-info` info modes. Per-build file lists are persisted to the local delta store after a successful download so subsequent delta runs have a baseline. New helpers: `get_build_files`, `calculate_delta`, `compute_changed_files`, `save_delta_manifest`, `load_delta_manifest`, `format_delta_summary`.
- Added language packs support (T014): `--language` and `--languages-download` CLI flags, `download_language_packs()` function for multi-language ISO creation, and language-aware `get_build_info()`.
- Added unit tests for `download_language_packs()` in `tests/test_download_uup.py`.
- Added `get_update_info()` function for `updateinfo.php` endpoint (T007).
- Added `--update-info` CLI flag for fetching update information.
- Added unit tests for `get_update_info()` in `tests/test_download_uup.py`.
- Added aria2c session persistence for download resume (T009): `--save-session` and `--save-session-interval 60` flags, session file at `uup_files/aria2_session.txt`, `--log` capture when `--verbose`, and `--no-resume` CLI flag to disable.
- Added mirror sources support (T010): `--mirrors` CLI option for custom download URLs, `.uup-mirrors` config file support, and fallback source configuration.
- Added unit tests for `get_available_languages` in `tests/test_download_uup.py` to improve coverage of API functions.
- Added a dedicated `test-matrix.yml` workflow for Python tests on uv-managed Python runtimes.
- Added `.github/instructions/windows-servicing.instructions.md` to keep Windows-only servicing changes separate from the default Linux build path.
- Added matching `.claude/rules/` and `.kilo/rules/` guidance so Claude and Kilo can reuse the same repo-specific rule set.
- Added `xmllint` documentation to `mise.toml` (system package via libxml2-utils on Debian/Ubuntu, libxml2 on Arch/Fedora).
- Added `biome` to `mise.toml` for JS/TS/JSON/HTML/CSS linting and formatting (via bun x @biomejs/biome).
- Added `mise run lint-xml` and `mise run lint-biome` tasks for linting workflows.
- Added `--verbose` CLI option to download_uup.py for capturing aria2c stderr/stdout on failure.
- Added `log_debug()` function to utils.sh with LOG_LEVEL environment variable support.
- Added complete type annotations to all functions in `scripts/download_uup.py`.
- Added test coverage for `_prepare_download_list`, `_run_aria2_download` success, `_process_selected_build`, and `_prepare_output_directory`.
- Added build profiles support (T016): `config/profiles.json` with minimal/standard/gaming/enterprise/dev presets, plus `--preset` and `--list-presets` CLI flags in `scripts/download_uup.py`.
- Added `get_profiles()`, `display_profiles()`, and `get_profile()` functions to `scripts/download_uup.py` for non-interactive profile selection.
- Added version pinning support (T018): `get_pinned_build()` and `save_pinned_build()` functions plus `--pin-build`, `--use-pin`, and `--show-pin` CLI flags for reproducible builds.
- Added ISO signing (T019): new `scripts/sign_iso.sh` that generates SHA256/SHA512 checksums and (optionally) a GPG detached signature, plus a `make sign` target.
- Added build history cache (T011): TTL-based local cache for build list and build info, with `cache_get`, `cache_set`, `cache_clear`, `get_latest_builds_cached`, and `get_build_info_cached` helpers, plus `--no-cache`, `--clear-cache`, and `--cache-ttl` CLI flags.
- Added custom edition selection (T012): `--edition` CLI flag for non-interactive edition filtering, plus `list_edition_files()` and `resolve_edition_filter()` helpers.
- Added component groups (T017): `config/component_groups.json` with 8 toggleable groups (gaming, productivity, social, telemetry, media, system, news, oem), `load_component_groups()`, `list_component_groups()`, `get_component_group()`, `validate_component_groups()`, `collect_component_patterns()`, `write_component_groups_for_build()`, and `display_component_groups()` helpers, plus `--groups`, `--list-groups`, and `--write-groups` CLI flags. Profiles now declare a `component_groups` list that is auto-persisted to `.uup-groups` for the build pipeline.

### Changed
- Added xmllint validation for autounattend.xml in validate_prereqs.sh (T055).
- Added `validate-xml` Makefile target for standalone XML validation.
- Added xmllint to required tools in utils.sh.
- Captured subprocess stderr/stdout in `_run_aria2_download` for better error diagnostics (T056).
- Refactored shell scripts (utils.sh, debloat_wim.sh, setup_env.sh, validate_prereqs.sh) to use consistent 2-space indentation.
- Inlined `generate_commands()` function in debloat_wim.sh (single-use function).
- Removed redundant section comments from shell scripts.
- Streamlined debloat_wim.sh command generation by inlining the generate_commands function.

### Changed
- Refreshed `AGENTS.md`, `.github/copilot-instructions.md`, and repo-specific Copilot instructions/skills to use a canonical long-form guide plus focused instruction files.
- Updated `.github/workflows/copilot-setup-steps.yml` to install only the toolchain this repository actually uses.
- Switched `.github/workflows/copilot-setup-steps.yml` to use `uv` for Python tooling bootstrap while validating the uv-managed runtime.
- Refined `.github/workflows/copilot-setup-steps.yml` to run shell syntax, XML, and Python test checks while skipping `make validate` unless real local UUP inputs are present.
- Updated `.github/workflows/lint-and-format.yml` to use repo-native shell and Ruff checks instead of generic Python linting.
- Narrowed `.github/workflows/test-matrix.yml` to Linux-based Python coverage aligned with the repository's active toolchain.
- Added frontmatter descriptions and input-aware validation rules to the focused `.github/instructions/*.instructions.md` files and `.github/skills/iso-build-pipeline/SKILL.md`.
- Normalized `mise.toml` to `[tools]` entries and wired `UV_PYTHON` to the mise-managed interpreter for consistent uv integration.
- Replaced Black with Ruff in workflow-based Python formatting checks and Copilot setup tool bootstrap.
- Updated the repository Python toolchain to 3.13 and switched CI/bootstrap Python provisioning to uv-managed Python.

## [1.2.0] - 2026-04-21 - UUP JSON API Completion

### Added
- **Complete UUP JSON API integration** (`scripts/download_uup.py`)
  - `get_available_editions()` - List editions for a build via `listeditions.php`
  - `get_available_languages()` - List languages for a build via `listlangs.php`
  - `fetch_latest_from_wu()` - Fetch latest build from Windows Update servers via `fetchupd.php`
  - `get_api_version()` - Check API status via `index.php`
- **New CLI options** for API queries:
  - `--editions UUID` - List available editions for a build
  - `--languages [UUID]` - List available languages (optionally filtered by build)
  - `--latest` - Fetch latest build from Windows Update
  - `--arch` - Architecture filter for `--latest` (amd64, x86, arm64, all)
  - `--ring` - Update ring for `--latest` (Dev, Beta, ReleasePreview, Retail)
  - `--version` - Show API version info
- **Cross-platform environment** (`mise.toml`)
  - mise (formerly rtx) configuration for tool version management
  - Task aliases for build commands (install-deps, build, download, clean, etc.)
  - Platform-specific dependency installation (Arch, Debian, Fedora, macOS, Windows)
  - Python 3.11 runtime for download scripts

### Documentation
- **Build selection guidance** added to README.md:
  - Which build type to choose (Feature Update vs Cumulative)
  - Edition selection guide (base editions, virtual editions)
  - Troubleshooting for common build selection issues
  - Fixes for missing Windows Security/Settings apps

## [1.1.0] - 2026-01-08 - Automated UUP Download

### Added
- **Automated UUP downloader** (`scripts/download_uup.py`)
  - Interactive menu for browsing and selecting Windows 11 builds
  - Direct integration with uupdump.net API
  - Edition filtering (download specific editions or all)
  - Parallel downloads using aria2c
  - Automatic file organization to `uup_files/` directory
  - Command-line options for automation
- **New Makefile target:** `make download` launches the interactive UUP downloader

### Changed
- Updated README.md to highlight automated download feature
- Updated Makefile help to include download command
- Quick Start now recommends automated download method

## [1.0.0] - 2026-01-08 - Production Ready Release

### Added
- **Pre-build validation system** (`scripts/validate_prereqs.sh`)
  - Checks all dependencies are installed
  - Validates UUP files are present
  - Verifies configuration files exist
  - Reports disk space availability
  - Provides actionable error messages
- Documentation: troubleshooting guide, ISO verification section, autounattend.xml guide (`docs/autounattend.md`)
- **New Makefile targets:** `make validate`, enhanced `make help`
- README: troubleshooting for common issues, ISO verification procedures, quality checklist

### Changed
- **Windows servicing script** (`scripts/windows_service.cmd`): now processes all WIM indexes, not just index 1
- **Build script** (`scripts/build.sh`): integrated pre-build validation, better error messages
- All shell scripts are now properly executable

### Fixed
- Shell script syntax validated across all files
- Removed hardcoded assumptions about single WIM index
- Improved error handling in build pipeline
- Better detection of missing configuration files

### Documentation
- Added `CHANGELOG.md` for tracking version history
- Expanded troubleshooting section with 8 common scenarios
- Added ISO verification procedures and quality checklist
