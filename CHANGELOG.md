# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `scripts/validate_reg_files.py` and `make validate-reg` — validates the
  `Windows Registry Editor Version 5.00` header on every standalone `.reg` file
  (`config/unattend-generator/apply.reg`) and on the `.reg` content embedded via
  `<Extensions><File path="...reg">` inside `ventoy/answer/autounattend.xml` and
  `config/autounattend.xml`, plus an informational (non-fatal) scan for security-sensitive
  value changes (UAC, service-disable, RPC) — same checks as `Ven0m0/Win`'s `reg-validate.yml`,
  extended to also parse the two files' embedded reg blocks since neither is a standalone
  `.reg` file on disk.
- `PSScriptAnalyzerSettings.psd1` at repo root (same ruleset as `Ven0m0/Win`) plus
  `--severity Warning --include-rules ...` args on the existing (previously argument-less)
  `py-psscriptanalyzer` pre-commit hook, a `lint-powershell` job in
  `.github/workflows/lint-and-format.yml` (`windows-latest`, `Invoke-ScriptAnalyzer -Settings`),
  and a `mise run lint-ps` task — covers `scripts/*.ps1`, `config/unattend-generator/system.ps1`,
  `uupdump/files/get_aria2.ps1`. All pass cleanly against current scripts with zero findings.
- `lint-xml` now also validates `ventoy/answer/autounattend.xml` (the canonical source, not just
  its `config/autounattend.xml` copy) and fails on `diff` if the two have drifted apart — in the
  Makefile, `.github/workflows/lint-and-format.yml`, `.github/workflows/copilot-setup-steps.yml`,
  and `mise run lint-xml`. Prevents a repeat of the `config/autounattend.xml` deletion below.
- `scripts/Mount-WimGui.ps1` — native Windows GUI (`System.Windows.Forms`, no external
  dependencies) for mounting a WIM: an `OpenFileDialog` to pick the `.wim` and a
  `FolderBrowserDialog` to pick (or create) the mount folder, then runs `dism.exe /Mount-Image`.
  Warns via message box if the chosen mount folder isn't empty before proceeding.
- `config/ntlite-presets/InstallApps.cmd` — a single-file, pure-batch winget app installer for
  NTLite's Post-Setup > Commands (timing "After Logon"). Waits up to 60s for `winget.exe` to
  exist, then installs a user-editable `PACKAGES` list with a 3-attempt retry per package,
  logging to `%TEMP%\InstallApps.log`. Not called by `build.py`/`debloat_wim.py`, same as the
  rest of the NTLite manual alternative path.
- Extended the Linux pipeline's answer file (`ventoy/answer/autounattend.xml` and its
  `config/autounattend.xml` copy) and the Windows servicing scripts
  (`scripts/windows_service.cmd`, `scripts/apply_image_settings.py`) to disable 8.3 short-name
  creation (`NtfsDisable8dot3NameCreation`) and set the High Performance power plan active in the
  offline SYSTEM hive, plus enable High Performance and disable monitor/standby/disk sleep
  timeouts in WinPE itself — both speed up unattended install time. `config/unattend-generator/apply.reg`
  (the NTLite manual-path companion, moved from `scripts/apply.reg`) got both the 8.3 and the
  power-plan tweak, matching the answer file.
- Moved `scripts/apply.reg` to `config/unattend-generator/apply.reg` alongside two new reference
  files, `after-logon.cmd` and `system.ps1` — standalone copies of the `FirstLogonScript0` and
  `SystemScript1` entries embedded in `ventoy/answer/autounattend.xml`'s generator-URL comment, so
  they're easier to read/edit than the URL-encoded inline form. None of the three are called by
  `build.py`/`debloat_wim.py`.
- Added `SkipAutoActivation` (specialize `Microsoft-Windows-Security-SPP-UX`) and
  `NetworkLocation`/`HideLocalAccountScreen` (oobeSystem `OOBE`) to
  `ventoy/answer/autounattend.xml`/`config/autounattend.xml`, ported from an NTLite preset's own
  `<Unattended>` block — needed so that block can be safely disabled (see Changed below) without
  losing those settings. No `ProductKey` was ported — see Security below.
- Wired up `prek` (already listed in `mise.toml`'s tools but unused) as the local hook
  runner for `.pre-commit-config.yaml`: new `mise run precommit`/`precommit-install` tasks,
  documented in `AGENTS.md`. Confirmed compatible with plain `pre-commit` first
  (`prek validate-config` + `prek run --all-files --dry-run` resolve every existing hook
  cleanly) — no config changes were needed, `pre-commit run --all-files`/`pre-commit install`
  still work identically against the same file for contributors without prek.
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
- Converted `invoke_system_cleanup.py`, `remove_short_names.py`, and `repair_wim.py` back to
  PowerShell (`Invoke-SystemCleanup.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`), matching
  their pre-Python-conversion originals ("Cleanup.cmd"/"Invoke-SystemCleanup.ps1", "8.3 strip
  all.cmd"/"Remove Shortnames.cmd"/"Remove Shortnames -install.cmd", "Repair Wim.cmd"). A new
  `scripts/WinUtils.ps1` (dot-sourced) replaces `win_utils.py` for these three, providing the
  same `Write-Step`/`Write-Success`/`Write-ErrorExit`/`Assert-Admin`/`Invoke-Dism` helpers so
  nothing gets duplicated across scripts. All three remain optional, Windows-side-only, and not
  called by `build.py`/`debloat_wim.py`.
- `Repair-Wim.ps1` and `Remove-ShortNames.ps1` now prompt for their WIM files and mount folders
  via native `OpenFileDialog`/`FolderBrowserDialog` instead of accepting hardcoded-default path
  parameters. `Remove-ShortNames.ps1` is also reduced to install.wim only — the `-IncludeWinRE`
  switch, Winre.wim reprocessing, and the `-InstallOnly`-gated boot.wim block were removed;
  leftover `*.LOG` cleanup (previously `-InstallOnly`-gated) now always runs.
- Merged a freshly-regenerated `ventoy/answer/autounattend.xml` (schneegans generator, newer
  commit) into the repo, prioritizing the new file's content and structure. Re-applied every
  repo-specific customization that had no counterpart in the new file so nothing already relied
  upon was silently dropped: the High Performance power plan + 8.3/`ActivePowerScheme` offline
  hive tweaks and the "allow re-running Setup after a failed attempt" partition-count-check
  removal (windowsPE pe.cmd), `install.ps1`'s full winget package list plus its `stage2.ps1`
  follow-up (WSL + Chris Titus WinUtil on next logon) and `MakeEdgeUninstallable.ps1`, a CapsLock
  remap (`Specialize.ps1`), a few `RemovePackages`/`RemoveCapabilities`/`RemoveFeatures` entries
  (`Microsoft.ZuneVideo`, `Media.WindowsMediaPlayer`, `Microsoft.Windows.WordPad`,
  `MicrosoftWindowsPowerShellV2Root`), and `Set-WinHomeLocation -GeoId 94` (`UserOnce.ps1`).
  Verified via a full programmatic diff of every `Extensions/File` entry against the
  previously-committed version — zero unaccounted-for content differences remain, only two
  accepted cosmetic preference values from the new file (accent color, one desktop-icon
  visibility flag) and the new file's own additions (Panther cleanup, `TaskbarEndTask`,
  `PreventDeviceMetadataFromNetwork`). One inconsistency intentionally left as-is from the new
  file rather than silently fixed: WinPE's `DeviceRegion` is now GeoID 244 (United States) while
  `TimeZone` stays "W. Europe Standard Time" — flagged for the user to confirm, not changed.
- `scripts/apply_image_settings.py` now warns (rather than silently overwriting) if
  `Windows\Panther\unattend.xml` already exists in the mounted install.wim before copying
  `config/autounattend.xml` over it — catches the case where the WIM was already serviced by
  NTLite with its own `<Unattended>` answer file, whose AutoLogon/OOBE/ProductKey settings would
  otherwise be silently discarded. Documented in `AGENTS.md`'s NTLite section: the Linux pipeline
  and NTLite presets are mutually exclusive answer-file sources per build.
- Documented (and set up) the supported combo of building via NTLite while booting/deploying via
  `ventoy/answer/autounattend.xml`'s own windowsPE `pe.cmd` chain: requires turning off both
  `AnswerFileLocationPanther` and `AnswerFileLocationBoot` in the NTLite preset, since Windows
  Setup only discovers one windowsPE answer file and ours copies itself into
  `Windows\Panther\unattend.xml` to also drive later passes — see `AGENTS.md`'s NTLite section.
- Converted the Linux build pipeline (`build.sh`, `setup_env.sh`, `sign_iso.sh`, `validate_prereqs.sh`, `debloat_wim.sh`) and the Windows servicing scripts (`Apply-ImageSettings.ps1`, `config.ps1`, `ps-utils.ps1`, `Invoke-SystemCleanup.ps1`, `New-Iso.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`, `Setup-PostInstall.ps1`) to Python for cross-platform maintainability. New modules: `pyutils.py`, `build.py`, `setup_env.py`, `sign_iso.py`, `validate_prereqs.py`, `debloat_wim.py`, `win_config.py`, `win_utils.py`, `apply_image_settings.py`, `invoke_system_cleanup.py`, `new_iso.py`, `remove_short_names.py`, `repair_wim.py`, `files/setup_post_install.py`. Windows servicing now shells out to `dism.exe` directly instead of the PowerShell DISM module. `custom_convert.sh`, `convert_config.sh`, and `utils.sh` (its dependency) stay bash — `custom_convert.sh` is upstream-derived and patch-only; its debloat hook now calls `debloat_wim.py` via `python3`. Removed the now-unused `PSScriptAnalyzerSettings.psd1` and the `mise.toml` `pwsh-install`/pwsh-essentials tasks. Updated `Makefile`, `mise.toml`, `README.md`, `AGENTS.md`, and the `.claude`/`.github` rule files accordingly.
- Consolidated the five `ventoy/answer/*.xml` autounattend variants (main, `-simple`, and three `old/` ancestors) into a single corrected `ventoy/answer/autounattend.xml`: dropped the conflicting Winhance debloat layer in favor of the schneegans-style script suite + winget install list, removed dead x86/arm64 Setup stubs, fixed a duplicate `FirstLogon.ps1` file entry that silently overwrote itself, fixed a duplicate `RunSynchronous` reboot order, removed an invalid placeholder `ProductKey`, and corrected `AutoLogon` `LogonCount` for the actual post-install reboot chain. `config/autounattend.xml` is now a copy of this file so the Linux UUP-dump build pipeline injects it too.
- Converted `iso-cmd/*.cmd` WIM-servicing scripts to PowerShell. Merged the three near-duplicate 8.3-shortname-stripping scripts into one parameterized `iso-cmd/Remove-ShortNames.ps1` (`-InstallOnly`, `-IncludeWinre` switches); converted `Repair Wim.cmd` -> `Repair-Wim.ps1`, `ISO.cmd` -> `New-Iso.ps1`, and `Cleanup.cmd` -> `Invoke-SystemCleanup.ps1` (fixing undefined `%REG%`/`%LOGPATH%`/`%WIN_VER%` variables the original never defined). Removed `Commands.cmd` (unrunnable wimlib scratch notes).
- Synced `config/component_groups.json` groups with `config/debloat_list.txt` patterns that had drifted out of the JSON groups (Utilities, Dev Tools, Extensions/Codecs sections folded into the `system`/`media` groups).
- Folded the placeholder `config/TODO.md` reference link into the root `TODO.md`.
- Added xmllint validation for autounattend.xml in validate_prereqs.sh (T055).
- Added `validate-xml` Makefile target for standalone XML validation.
- Added xmllint to required tools in utils.sh.
- Captured subprocess stderr/stdout in `_run_aria2_download` for better error diagnostics (T056).
- Refactored shell scripts (utils.sh, debloat_wim.sh, setup_env.sh, validate_prereqs.sh) to use consistent 2-space indentation.
- Inlined `generate_commands()` function in debloat_wim.sh (single-use function).
- Removed redundant section comments from shell scripts.
- Streamlined debloat_wim.sh command generation by inlining the generate_commands function.
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

### Fixed
- Restored `config/autounattend.xml`, deleted in a prior commit (`df3035c`) without updating any
  of its ~15 references across `Makefile`, `.github/workflows/*.yml`,
  `.github/copilot-instructions.md`, `mise.toml`, `AGENTS.md`, `README.md`,
  `docs/autounattend.md`, and `scripts/custom_convert.sh`/`validate_prereqs.py`. Since
  `custom_convert.sh`'s autounattend-injection step treats a missing file as skip-not-fail, the
  Linux build pipeline was silently producing ISOs with no answer file at all — falling back to
  fully manual/interactive Windows Setup — with no error anywhere in the chain. Re-copied from
  the canonical `ventoy/answer/autounattend.xml` (UTF-8, no BOM, matches `AGENTS.md`'s
  invariant); see Added below for the drift check that now catches this class of bug in CI.
- `scripts/apply_image_settings.py` referenced `scripts/autounattend.xml` as the source for all
  three autounattend-copy steps (boot.wim indexes, Panther `unattend.xml`, ISO root) — that file
  never existed; the real one lives at `config/autounattend.xml`. Every one of those
  `shutil.copy()` calls raised `FileNotFoundError` the moment this script ran past the mount
  step. Fixed to resolve `script_dir.parent / "config" / "autounattend.xml"`, matching the
  pattern already used two lines below for `SetupComplete.cmd`.
- Removed the three local `.pre-commit-config.yaml` hooks (`psscriptanalyzer-lint`,
  `psscriptanalyzer-format`, `pester-tests`) that shelled out to
  `.github/scripts/Lint-PowerShell.ps1`/`Format-PowerShell.ps1`/`Test-PowerShell.ps1` —
  none of those scripts, nor the `.github/scripts/` directory, ever existed, so every
  hook failed immediately with a "not recognized as the name of a script file" error.
  Root cause: leftover config from before the Windows servicing pipeline was converted
  to Python; there's no PowerShell codebase left to lint/format/test. The existing
  `thetestlabs/py-psscriptanalyzer` hooks already cover lint+format for any `.ps1` file
  in the repo. Also excluded `uupdump/` from those hooks (vendored upstream UUP-converter
  content, same treatment as `scripts/custom_convert.sh` — not ours to reformat) and
  excluded `CLAUDE.md` from `trailing-whitespace`/`end-of-file-fixer`/
  `fix-byte-order-marker`/`mixed-line-ending`, discovered when running the full suite:
  on a Windows checkout without symlink support, `CLAUDE.md` (a real git symlink to
  `AGENTS.md`) materializes as a plain text file, so those hooks would silently corrupt
  the symlink target (appending a trailing newline) if ever committed.
- Brought the rest of the `.pre-commit-config.yaml` suite to green (`prek run --all-files`
  now exits 0): fixed the remaining ruff lint errors post-autofix (an `@overload` ambiguity
  in `download_uup.fetch_url` where both the `Literal[False]` and `Literal[True]` variants
  declared defaults — made the `True` variant keyword-only with no default; an ambiguous
  `l` loop variable; nested-if/nested-with simplifications; two intentional blind
  `except Exception` boundaries marked with `# noqa: BLE001`); marked the Python scripts'
  missing executable bits (`git add --chmod=+x`, matching the `chmod +x` step every Makefile
  target already runs); reformatted two stray non-compliant JSON files
  (`.claude/settings.json`, `renovate.json`, `.kilo/package.json`) with biome and excluded
  `ventoy/` from `biome-ci` (vendored Ventoy config, same "not ours to reformat" treatment
  as `uupdump/`); added `pyrightconfig.json` (`typeCheckingMode: standard`, scoped to
  `scripts/download_uup.py`) since basedpyright's own stricter-than-pyright default rules
  (`reportAny`, `reportExplicitAny`, `reportUnusedCallResult`, etc.) were failing the hook
  on 357 pre-existing warnings that were never a deliberately-adopted bar — matches
  AGENTS.md's existing "other scripts are not yet gated on this" and PLAN.md's "add strict
  typing/coverage gates only if actually wanted".
- Fixed a gap in the `RunSynchronousCommand` `<Order>` sequence in `ventoy/answer/autounattend.xml`'s WindowsPE pass (jumped from 20 to 22, and 24 to 26) left over from a prior edit that removed commands without renumbering the rest. Windows Setup requires these values to be contiguous starting at 1; the gap silently truncated the WindowsPE command chain after disk formatting, skipping image apply, bcdboot, driver injection, and the post-format reboot. Also fixed stray non-indented markup and trailing blank lines introduced by the same edit. Re-synced `config/autounattend.xml` to the corrected canonical copy, which carried the same class of gap.
- Made the WindowsPE `diskpart.exe` and `dism.exe /Apply-Image` steps in `ventoy/answer/autounattend.xml` / `config/autounattend.xml` retry once (after a 5s pause) instead of aborting setup on the first failure, since both can fail transiently right after boot (disk not yet settled, USB enumeration races). If the retry also fails, setup still exits with `pause`/`exit /b 1` (the on-screen diskpart/dism error is preserved either way) rather than continuing on an unformatted or partially-applied disk.

### Security
- Removed an unverified product key (`RKY6N-27F4G-W3X9B-QTFT2-PG2RH`, ported from an NTLite
  preset in a prior change) from `ventoy/answer/autounattend.xml`/`config/autounattend.xml` — it
  did not match Microsoft's published Windows 11 Pro generic/KMS client setup key
  (`W269N-WFGWX-YVC9B-4J6C9-T83GX`), so it could not be verified safe to commit. No `ProductKey`/
  `UserData` element is set at all now; edition selection instead uses `dism.exe /Apply-Image`'s
  `/Name:"Windows %OS_VERSION% Pro"` filter (windowsPE Order 20-21), matching how the schneegans
  unattend generator's own "generic key" mode picks an edition without embedding any key. See
  `AGENTS.md`'s `config/autounattend.xml` section for the do-not-reintroduce note.

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
