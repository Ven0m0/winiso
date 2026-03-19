# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Bulk pull request auto-merge workflow**
  - Added `.github/workflows/automerge-open-prs.yml` to enable auto-merge for all open pull requests on demand
  - Added `scripts/automerge_open_prs.sh` to iterate open pull requests and configure auto-merge with the selected merge method

## [1.1.0] - 2026-01-08 - Automated UUP Download

### Added
- **Automated UUP downloader** (`scripts/download_uup.py`)
  - Interactive menu for browsing and selecting Windows 11 builds
  - Direct integration with uupdump.net API
  - Edition filtering (download specific editions or all)
  - Fast parallel downloads using aria2c
  - Automatic file organization to `uup_files/` directory
  - Command-line options for automation
  - Comprehensive documentation (`scripts/README_DOWNLOAD.md`)

- **New Makefile target**
  - `make download` - Launch interactive UUP downloader

### Changed
- Updated README.md to highlight automated download feature
- Updated Makefile help to include download command
- Quick Start now recommends automated download method

### Documentation
- Added complete downloader documentation (`scripts/README_DOWNLOAD.md`)
- Updated README.md with download options
- Enhanced Quick Start guide with automated workflow

## [1.0.0] - 2026-01-08 - Production Ready Release

### Added
- **Pre-build validation system** (`scripts/validate_prereqs.sh`)
  - Checks all dependencies are installed
  - Validates UUP files are present
  - Verifies configuration files exist
  - Reports disk space availability
  - Provides actionable error messages

- **Comprehensive documentation improvements**
  - Detailed troubleshooting guide with common issues and solutions
  - ISO verification section with quality checklist
  - Validation commands for diagnosing build issues
  - Autounattend.xml configuration guide (`config/README_AUTOUNATTEND.md`)

- **New Makefile targets**
  - `make validate` - Validate prerequisites before building
  - Enhanced `make help` with validation step

- **Enhanced README.md**
  - Step-by-step troubleshooting for common issues
  - ISO verification and testing procedures
  - Quality checklist for production deployment
  - Validation commands reference

### Changed
- **Windows servicing script improvements** (`scripts/windows_service.cmd`)
  - Now processes ALL indexes in WIM file (not just index 1)
  - Loops through all editions and applies servicing to each
  - Exports all indexes with proper compression
  - Better progress reporting for multi-index WIMs

- **Build script enhancements** (`scripts/build.sh`)
  - Integrated pre-build validation checks
  - Fails fast if prerequisites are not met
  - Better error messages for missing dependencies

- **All shell scripts are now properly executable**
  - Fixed permissions on all `.sh` files
  - Added executable bit to validation script

### Fixed
- Shell script syntax validated across all files
- Removed hardcoded assumptions about single WIM index
- Improved error handling in build pipeline
- Better detection of missing configuration files

### Documentation
- Added `CHANGELOG.md` for tracking version history
- Created `config/README_AUTOUNATTEND.md` for autounattend.xml guidance
- Expanded troubleshooting section with 8 common scenarios
- Added ISO verification procedures and quality checklist
- Included validation commands for debugging

### Quality Improvements
- All bash scripts pass syntax validation
- Comprehensive prerequisite checking before builds
- Better user feedback with color-coded messages
- Validation of UUP files, config files, and dependencies
- Production-ready error handling throughout

## Usage Notes

### For First-Time Users
1. Run `make deps` to install dependencies
2. Download UUP files to `uup_files/`
3. Run `make validate` to verify setup
4. Run `make build` to create ISO

### For Existing Users
- The build process now includes automatic validation
- Windows servicing script now handles multiple editions correctly
- Review new troubleshooting guide if you encounter issues
- Check `config/README_AUTOUNATTEND.md` for autounattend.xml customization

## Breaking Changes
None - all changes are backward compatible.

## Migration Guide
No migration needed. Existing configurations will work with the new validation system.

## Known Limitations
- Requires Linux environment (Arch, Debian/Ubuntu, or Fedora recommended)
- UUP files are required; they can be downloaded automatically via `make download` (recommended) or manually from uupdump.net
- Windows servicing stage (optional) requires Windows machine with DISM
- Minimum 20GB disk space required for build process

## Future Enhancements
- Docker container for portable builds
- CI/CD pipeline for automated testing
- Support for Windows Server editions
- Pre-configured templates for different use cases
