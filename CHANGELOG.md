# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Added a dedicated `test-matrix.yml` workflow for Python tests across Ubuntu and macOS on Python 3.9-3.12.

### Changed
- Refreshed `AGENTS.md`, `.github/copilot-instructions.md`, and repo-specific Copilot instructions/skills to use a canonical long-form guide plus focused instruction files.
- Updated `.github/workflows/copilot-setup-steps.yml` to install only the toolchain this repository actually uses.
- Switched `.github/workflows/copilot-setup-steps.yml` to use `uv` for Python tooling bootstrap while validating the mise-managed runtime.
- Normalized `mise.toml` to `[tools]` entries and wired `UV_PYTHON` to the mise-managed interpreter for consistent uv integration.

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
