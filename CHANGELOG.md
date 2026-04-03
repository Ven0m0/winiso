# Changelog

All notable changes to this project will be documented in this file.

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
