# Upstream Consolidation Summary

This directory contains consolidated files from the former `upstream/` directories:
- `upstream/converter/`
- `upstream/28000.1340_pro_convert_virtual/`

## Consolidation Date
2026-03-27

## Files Moved

### From `upstream/converter/`
| Original | New Location | Notes |
|----------|--------------|-------|
| `convert.sh` | `convert_upstream_reference.sh` | Original upstream converter (708 lines) |
| `readme.md` | `README_CONVERTER_UPSTREAM.md` | Upstream documentation |
| `LICENSE` | `LICENSE_UPSTREAM` | MIT License from upstream |
| `deps.sh` | `deps_upstream.sh` | Minimal Arch deps installer |
| `convert_ve_plugin.sh` | *skipped* | Duplicate of `../convert_ve_plugin` |

### From `upstream/28000.1340_pro_convert_virtual/`
| Original | New Location | Notes |
|----------|--------------|-------|
| `readme.unix.md` | `README_UNIX_28000.md` | Unix requirements doc |
| `ConvertConfig.ini` | `ConvertConfig_28000.ini` | Windows-style converter config |
| `CustomAppsList.txt` | `CustomAppsList_28000.txt` | Store apps whitelist/blacklist |
| `uup_download_linux.sh` | `uup_download_linux_legacy.sh` | Bash downloader (legacy) |
| `uup_download_windows.cmd` | `uup_download_windows_legacy.cmd` | Windows batch downloader |
| `files/get_aria2.ps1` | `get_aria2.ps1` | PowerShell aria2c downloader |
| `files/converter_multi` | `files_28000/converter_multi` | aria2 manifest for converter |
| `files/converter_windows` | `files_28000/converter_windows` | Windows converter binary manifest |
| `files/convert_config_linux` | *skipped* | Duplicate of `../convert_config.sh` |
| `files/convert_config_macos` | *skipped* | Duplicate of `../convert_config.sh` |

## Deduplication Performed

The following duplicates were identified and NOT copied:

1. **Virtual Editions Plugin**: `upstream/converter/convert_ve_plugin.sh` is identical to `../convert_ve_plugin`
2. **Config Files**: `convert_config_linux` and `convert_config_macos` are identical to `../convert_config.sh`

## Active Scripts (in parent `scripts/` directory)

These consolidated upstream files are for **reference only**. The actively used scripts are:

| Purpose | Active Script |
|---------|---------------|
| Main converter | `custom_convert.sh` (modified fork with debloat integration) |
| Virtual editions | `convert_ve_plugin` |
| Config | `convert_config.sh` |
| UUP Downloader | `download_uup.py` (Python, feature-rich) |
| Build orchestrator | `build.sh` |

## Relationship to Active Code

- `custom_convert.sh` is a modified fork of `convert_upstream_reference.sh`
  - Adds: edition targeting, debloat hook, autounattend.xml injection, OEM injection
- `download_uup.py` supersedes `uup_download_linux_legacy.sh` and `uup_download_windows_legacy.cmd`
- The config files are functionally identical; `convert_config.sh` is the canonical version
