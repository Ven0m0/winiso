# Debloated Windows 11 ISO Builder

[![Maintainability](https://qlty.sh/gh/Ven0m0/projects/winiso/maintainability.svg)](https://qlty.sh/gh/Ven0m0/projects/winiso)

A Linux-based automation toolset for creating debloated Windows 11 ISO files from UUP (Unified Update Platform) dump files. Removes bloatware, injects unattended setup configuration, and applies performance tweaks, all while preserving essential system components.

## Features

- **Automated UUP Download:** Interactive downloader for fetching Windows 11 builds from uupdump.net
- **Pre-Build Validation:** Checks dependencies, files, and configuration before starting; separate validators for XML, `.reg` content, and the debloat list
- **Targeted Edition:** Builds Windows 11 Pro for Workstations (fallback to Pro)
- **Build Profiles:** `minimal`, `standard`, `gaming`, `enterprise`, `dev` presets in `config/profiles.json` pick the edition and the AppX component groups to remove
- **90+ Debloat Patterns:** Xbox, Cortana, Clipchamp, Solitaire, news/weather apps, and more
- **Unattended Setup:** Injects `autounattend.xml` for OOBE bypass and privacy settings
- **First-Boot Tweaks:** Applies telemetry reduction, advertising disable, performance optimizations
- **Optional Windows Stage:** DISM component cleanup, 8.3 short name stripping, registry hardening, optional driver injection
- **Release Helpers:** `make sign` writes SHA256/SHA512 checksums (and an optional GPG signature); `scripts/Test-IsoBoot.ps1` boots the ISO in a Hyper-V VM
- **Preserves Dependencies:** Store, WebView2, VCLibs, Defender, and runtime frameworks remain intact

## Quick Start

### 1. Install Dependencies

**Option A: Using mise (Recommended)**

```bash
mise trust mise.toml
mise run install-deps
```

Uses [mise](https://mise.jdx.dev/) for task running. `mise run install-deps` covers pacman and apt only; on Fedora use `mise run linux` or `make deps`.

**Option B: Using Make**

```bash
make deps
```

Supports Arch Linux (pacman), Debian/Ubuntu (apt), and Fedora (dnf).

**Python and uv:** the scripts need Python 3.14+ (`requires-python` in `pyproject.toml`) and `httpx`/`orjson`. Every `make` target runs scripts through `uv run --` so those are on the path; `mise.toml` does not install Python or uv (its `[tools]` block is commented out), so install `uv` yourself. To use a system interpreter instead: `make build PY=python3` (needs `httpx` and `orjson` installed globally).

### 2. Download UUP Files

**Option A: Automatic Download (Recommended)**

```bash
make download
```

This launches an interactive menu to select and download Windows 11 builds directly from uupdump.net (the downloader talks to uupdump.net only).

Useful `scripts/download_uup.py` flags (run it with `--help` for the full list):

| Flag | Purpose |
|------|---------|
| `-l` / `--list` | List the latest builds and exit (`mise run list-builds`) |
| `-b` / `--build-id` | Download a specific build ID |
| `-e` / `--editions ID`, `--languages [ID]` | List editions or languages for a build and exit |
| `--edition NAME` | Non-interactive edition filter (`professional`, `enterprise`, `home`, `core`, `education`, or an ESD filename) |
| `--latest` (with `--arch`, `--ring`) | Fetch the latest build from Windows Update servers |
| `-p` / `--preset NAME`, `--list-presets` | Apply a profile from `config/profiles.json` (`minimal`, `standard`, `gaming`, `enterprise`, `dev`); its component groups are written to `.uup-groups` |
| `--groups`, `--list-groups`, `--write-groups PATH` | Choose AppX component groups (from `config/component_groups.json`) to remove during the build |
| `--pin-build`, `--use-pin`, `--show-pin` | Pin a build ID in `.uup-pin.json` for reproducible builds |
| `--no-cache`, `--clear-cache`, `--cache-ttl` | Control the local build-metadata cache |
| `--no-resume`, `--mirrors`, `--verbose` | aria2c resume, custom mirror list, verbose output |

**Option B: Manual Download**

1. Visit [uupdump.net](https://uupdump.net)
2. Select your desired Windows 11 build
3. Download the UUP package
4. Extract/move all files to `uup_files/`

**Important:** Ensure all `.cab` and `.esd` files are directly in `uup_files/`, not in a subdirectory.

### 3. Configure (Optional)

- **Unattended Setup:** Edit `ventoy/answer/autounattend.xml` (`config/autounattend.xml` is a symlink to it), or regenerate it from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/). See `docs/autounattend.md`
- **Debloat List:** Edit `config/debloat_list.txt` to add/remove app patterns
- **Profile:** Pick a preset with `uv run -- scripts/download_uup.py --preset NAME` (`make download` takes no arguments), then build with `PROFILE=NAME make build` or `scripts/build.py --profile NAME`. A profile sets the target edition; `--edition NAME` overrides it

### 4. Validate Prerequisites (Recommended)

```bash
make validate          # tools, disk space, UUP files, config
make validate-xml      # every *.xml: well-formed, UTF-8 without BOM, autounattend symlink resolves
make validate-reg      # .reg headers, standalone and embedded in autounattend.xml
make validate-debloat  # config/debloat_list.txt: syntax, duplicates, keep-list collisions
```

`make validate` checks that all dependencies, UUP files, and configuration are ready (it needs a populated `uup_files/`); the other three only read repo config and run without UUP files. `make build` runs `validate_prereqs.py` itself first.

### 5. Build

```bash
make build
```

The debloated ISO will appear in `output/`.

## Build Selection Guidance

### Which Build Should I Choose?

**Recommended:** Select "Pro for Workstations" edition for the best balance of features and stability.

#### Build Type Differences

| Type | Description | Use Case |
|------|-------------|----------|
| **Feature Update** | Complete Windows build ("Upgrade to...") | Recommended - full installation |
| **Cumulative Update** | Updates only ("Update for...") | Not useful for ISO creation |

If you're not sure or want an updated image, choose the **Feature Update**.

#### Edition Selection Guide

Select the **base edition** first, then add additional editions:

| Virtual Edition | Base Edition |
|----------------|-------------|
| Enterprise | Pro |
| Education | Pro |
| Pro Education | Pro |
| Pro for Workstations | Pro |
| IoT Enterprise | Pro |
| Home Single Language | Home |

### Troubleshooting Common Issues

#### "This build can't be converted to an ISO image"

This means the entry is **not** a complete Windows build:
- Standalone update (not usable)
- Server build without metadata

Those entries cannot be made into Windows images.

#### Build shows "(2)" in name

Most often the build was pushed to multiple channels, or it's a different release type mistaken for a duplicate.

#### ISO version differs from selected build

Common causes:
- "Include updates" option was unchecked on uupdump.net
- Conversion failed to include updates
- Conversion was done on Linux/macOS (does not support installing updates)

To fix: Redo the conversion with "Include updates" checked on uupdump.net.

#### Windows Security or Settings app missing

This applies to Windows 11 22H2 and later.

**Fix "Settings" app or missing "Microsoft Store":**
```cmd
wsreset -i
```

**Fix missing "Windows Security":**
1. Go to uupdump.net for your build
2. Use "Browse files" section to search for `SecHealthUI`
3. Download and install the appx package

## Build Options

### Using mise (Recommended)

```bash
mise run install-deps    # Install system dependencies
mise run download       # Download UUP files
mise run validate      # Validate prerequisites
mise run build        # Build ISO
mise run build-pro    # Build Pro edition
mise run build-pause  # Build with pause
mise run clean-unix   # Clean artifacts
mise run list-builds  # List latest builds (download_uup.py --list)
mise run test         # pytest (uv run --group dev pytest tests/)
mise run lint         # ruff check + format check + ty
mise run test-iso     # Windows only: boot output/*.iso in a Hyper-V VM
mise tasks            # Full task list (lint-xml, lint-reg, lint-debloat, lint-shell, lint-ps, ...)
```

The `build`, `build-pro` and `build-pause` mise tasks error out on native Windows; run them from WSL or Git Bash.

### Using Make

| Make Command | mise equivalent | Description |
|-------------|----------------|-------------|
| `make deps` | `mise run install-deps` | Install system dependencies |
| `make download` | `mise run download` | Download UUP files |
| `make validate` | `mise run validate` | Validate prerequisites |
| `make validate-xml` | `mise run lint-xml` | Validate all XML config files |
| `make validate-reg` | `mise run lint-reg` | Validate `.reg` headers |
| `make validate-debloat` | `mise run lint-debloat` | Validate `config/debloat_list.txt` |
| `make build` | `mise run build` | Build ISO (default) |
| `make build-pro` | `mise run build-pro` | Build Pro edition |
| `make build-nano` | none | Aggressive debloating (`NANO=1`) |
| `make build-pause` | `mise run build-pause` | Pause for servicing |
| `make sign ISO=output/Win11.iso [GPG=1 KEY=<id>]` | none | SHA256/SHA512 checksums, optional GPG signature |
| `make clean` | `mise run clean-unix` | Remove artifacts |

### Direct Scripts

```bash
./scripts/setup_env.py   # Install dependencies
./scripts/download_uup.py --list  # List builds
./scripts/build.py       # Build ISO
./scripts/build.py --profile minimal   # Build using a named profile
./scripts/build.py --edition Core      # Override the target edition directly
```

Run these through `uv run --` (or a venv with `httpx`/`orjson`); `make` does this for you.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred Windows edition |
| `FALLBACK_EDITION` | `Professional` | Fallback if target not found |
| `PROFILE` | unset | Named profile from `config/profiles.json` (sets the edition); same as `--profile` |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Set to `1` for Windows servicing |
| `NANO` | `0` | Set to `1` for aggressive debloating |

Precedence for the edition: `--edition` over `--profile`/`PROFILE` over `TARGET_EDITION`.

## Windows Servicing Stage (Optional)

For maximum optimization (DISM cleanup + 8.3 stripping), use the Windows servicing stage:

```bash
make build-pause
```

When paused:
1. Copy `scripts/ISODIR/sources/install.wim` to a Windows machine (the converter prints the exact path, `install.esd` if the image is ESD-compressed)
2. Run `scripts\windows_service.cmd C:\path\to\install.wim [MOUNT_DIR] [ISO_DIR]` as Administrator (defaults: `C:\ISO\sources\install.wim`, `C:\mnt`)
3. Copy the serviced WIM back
4. Press Enter to continue ISO generation

Other optional, Windows-only helpers in `scripts/` (none are required by the Linux build):

| Script | Purpose |
|--------|---------|
| `apply_image_settings.py` | Extract an ISO, inject the unattend file, re-run debloat (`--debloat`), inject drivers (`--driver-path DIR`, via `dism /Add-Driver /Recurse`). Stdlib-only; needs admin |
| `new_iso.py` | Build a bootable UEFI+BIOS ISO from a staged tree with `oscdimg` (`--iso-root`, `--output-iso`) |
| `Invoke-SystemCleanup.ps1`, `Remove-ShortNames.ps1`, `Repair-Wim.ps1`, `Mount-WimGui.ps1` | Live-OS cleanup, 8.3 short-name stripping, DISM RestoreHealth, and a WIM mount GUI |
| `Test-IsoBoot.ps1` | Boot the newest `output/*.iso` in a throwaway Hyper-V VM and wait for the heartbeat |
| `Invoke-OnlineServicing.ps1` | Manual WinPE deploy and recapture loop in a Hyper-V VM (needs the Windows ADK) |

See `docs/iso-creation.md` and `docs/hyperv-testing.md` for details.

## Project Structure

```
├── config/
│   ├── autounattend.xml      # Symlink to ventoy/answer/autounattend.xml (unattended setup)
│   ├── debloat_list.txt      # App removal patterns
│   ├── component_groups.json # Named AppX groups (gaming, social, telemetry, ...)
│   ├── profiles.json         # Build profiles (minimal/standard/gaming/enterprise/dev)
│   ├── components.psd1       # Extra items for the NTLite manual path (not used by scripts)
│   ├── ntlite-presets/       # NTLite presets (manual alternative)
│   ├── unattend-generator/   # Reference copies of generator scripts + apply.reg (manual path)
│   └── oem/
│       └── SetupComplete.cmd # First-boot tweaks script (CRLF)
├── docs/
│   ├── autounattend.md       # Guide for autounattend.xml customization
│   ├── iso-creation.md       # Linux pipeline vs Windows-side ISO assembly
│   └── hyperv-testing.md     # Test-IsoBoot.ps1 and Invoke-OnlineServicing.ps1
├── scripts/
│   ├── build.py              # Main build orchestrator
│   ├── custom_convert.sh     # Modified UUP converter (upstream-derived, stays bash)
│   ├── convert_config.sh     # Shared converter config (sourced by custom_convert.sh)
│   ├── utils.sh              # Bash helpers, only used by custom_convert.sh
│   ├── debloat_wim.py        # WIM debloating logic
│   ├── keep_list.py          # Owns debloat_list.txt, component groups and the AppX keep-list
│   ├── download_uup.py       # Downloader CLI (with uup_api.py, uup_download.py, uup_profiles.py, uup_delta.py)
│   ├── setup_env.py          # Dependency installer
│   ├── validate_prereqs.py   # Pre-build checks
│   ├── validate_xml.py, validate_reg_files.py, validate_debloat.py  # Config validators
│   ├── sign_iso.py           # Checksums and optional GPG signature
│   ├── pyutils.py            # Shared logging/tool-check helpers
│   ├── apply_image_settings.py # Windows-side ISO extraction/debloat (dism.exe-based)
│   ├── new_iso.py, win_config.py, win_utils.py # Windows-side ISO builder and shared helpers
│   ├── windows_service.cmd   # Windows servicing script
│   ├── *.ps1                 # Windows-side PowerShell helpers (WinUtils, HyperVUtils, Test-IsoBoot, ...)
│   └── winpe/                # WinPE payloads used by Invoke-OnlineServicing.ps1
├── ventoy/answer/            # Canonical autounattend.xml (plus Ventoy answer files)
├── tests/                    # pytest suite
├── uup_files/                # Place UUP files here (input, not committed)
├── output/                   # Final ISO appears here (output, not committed)
├── Makefile                  # Build interface
├── mise.toml                 # Task runner entries
└── README.md                 # This file
```

## Configuration

The embedded converter is synced from the upstream UUP converter and uses `scripts/convert_config.sh`
for shared converter-specific settings.

### Debloat Patterns

Edit `config/debloat_list.txt` to customize which apps are removed:

```text
# Gaming bloat
*Xbox*
*Solitaire*

# Social media
*Facebook*
*TikTok*
```

**Safe to remove:** Gaming, social media, news/weather, productivity bloat, OEM preinstalls

**Do NOT remove:** `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`

Extra AppX patterns come from the component groups selected in `.uup-groups` (written by `download_uup.py --preset/--groups`; group definitions live in `config/component_groups.json`). Protected entries are filtered out of both sources. Run `make validate-debloat` after editing.

### Autounattend.xml

The canonical file is `ventoy/answer/autounattend.xml`; `config/autounattend.xml` is a symlink to it. It contains no `ProductKey`; in the windowsPE pass its `pe.cmd` chain lists the images (`dism /Get-WimInfo`) and prompts for the image index before `dism /Apply-Image`. If you regenerate it from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/), drop any key the generator adds. Recommended settings:
- Skip Microsoft Account (use local account)
- Disable privacy prompts
- Minimal telemetry
- Keep: Defender, Store, Windows Update

## Alternative: NTLite (manual, Windows-only)

Prefer NTLite's GUI over this repo's automated Linux pipeline? Mount the WIM in NTLite and
import `config/ntlite-presets/win11.xml`, then import `config/unattend-generator/apply.reg` (via
NTLite's Registry tab or `regedit`) for the setup bypasses the preset doesn't include.
`config/unattend-generator/logon.cmd`, `system.cmd` and `system.ps1` are reference copies of the
generator scripts embedded in the answer file (not called by any script). See `AGENTS.md` for the full breakdown. None of these files are used by
`build.py`/`debloat_wim.py`. Do not combine an NTLite-serviced WIM with `apply_image_settings.py`:
it overwrites the Panther `unattend.xml` NTLite wrote.

## Alternative: Online Servicing (manual, Windows-only)

`scripts/Invoke-OnlineServicing.ps1` installs an `install.wim` into a Hyper-V VM through WinPE,
pauses for live tweaks, then recaptures it as a new WIM. Needs the Windows ADK + WinPE add-on and
Hyper-V. Its output is a distinct artifact: do not mix it with a `debloat_wim.py`-serviced WIM.
See `docs/hyperv-testing.md`.

## Requirements

- **Linux:** Arch Linux, Debian/Ubuntu, or Fedora
- **Tools:** wimlib, aria2, cabextract, chntpw, genisoimage/cdrtools; `xmllint` (libxml2) is optional for XML validation
- **Python:** 3.14+ with `uv` (runtime deps `httpx[http2]` and `orjson`)
- **Privileges:** runs as the current user; no `sudo` anywhere in the build pipeline
- **Disk Space:** ~20GB for build process
- **Optional:** Windows machine for DISM servicing stage; Windows host with Hyper-V for `Test-IsoBoot.ps1`

## How It Works

1. **Edition Selection:** Scans UUP metadata, exports only Pro for Workstations (or Pro fallback)
2. **UUP Conversion:** Converts UUP files to single-index WIM using wimlib
3. **Debloating:** Removes matching apps from WindowsApps and AppRepository directories
4. **Injection:** Copies autounattend.xml and OEM scripts into ISO structure
5. **ISO Generation:** Creates bootable ISO with genisoimage/mkisofs

## Troubleshooting

### Common Issues

#### No UUP files found
**Symptom:** Build fails with "No UUP files (.cab or .esd) found"

**Solution:**
- Ensure `.cab` and `.esd` files are directly in `uup_files/`, not in a subdirectory
- Run `make validate` to check UUP files are detected
- Verify files with: `ls -la uup_files/`

#### Edition not found
**Symptom:** Build fails with "Neither ProfessionalWorkstation nor Professional found"

**Solution:**
- Check available editions: `wimlib-imagex info uup_files/*.esd | grep "Edition ID"`
- Override target edition: `TARGET_EDITION=Enterprise make build`
- Download correct UUP package from uupdump.net

#### Dependencies missing
**Symptom:** Build fails with "tool not found" errors

**Solution:**
- Run `make deps` to install all dependencies
- Run `make validate` to verify all tools are installed
- Manually install missing tools if your distro isn't supported

#### ISO not created
**Symptom:** Build completes but no ISO file in output/

**Solution:**
- Check for errors in the conversion output
- Verify sufficient disk space (20GB+ required)
- Check permissions on output/ directory
- Review build logs for specific errors

#### Debloating didn't work
**Symptom:** ISO still contains bloatware apps

**Solution:**
- Verify `config/debloat_list.txt` exists and has patterns
- Check patterns match app names: patterns are case-insensitive wildcards
- Mount the ISO and check install.wim manually: `wimlib-imagex info output/*.iso`

#### Build artifacts remain
**Symptom:** ISODIR or old ISOs clutter the workspace

**Solution:**
- Run `make clean` to remove all build artifacts
- Manually remove: `rm -rf scripts/ISODIR output/*.iso`

#### Autounattend not working
**Symptom:** Windows installation still shows setup prompts

**Solution:**
- Verify `config/autounattend.xml` exists and is valid XML
- Check XML was injected into ISO root (not sources/)
- Regenerate autounattend.xml from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/)
- Ensure XML syntax is correct (no encoding issues)

#### Windows servicing stage fails
**Symptom:** DISM errors during windows_service.cmd

**Solution:**
- Ensure you're running as Administrator
- Check WIM file path is correct and accessible
- Verify sufficient disk space on Windows machine
- Review DISM error messages for specific issues

### Validation Commands

Run these commands to diagnose issues:

```bash
# Check prerequisites
make validate

# List UUP files
ls -lh uup_files/

# Check available Windows editions
wimlib-imagex info uup_files/*.esd | grep "Edition ID"

# Verify debloat patterns
grep -v "^#" config/debloat_list.txt | grep -v "^[[:space:]]*$" | wc -l

# Check XML, .reg content and debloat patterns
make validate-xml validate-reg validate-debloat

# Verify disk space
df -h .
```

## ISO Verification

After building your ISO, verify it's ready for deployment:

### 1. Check ISO File

```bash
# Verify ISO was created
ls -lh output/*.iso

# Check ISO size (should be 3-6GB depending on edition)
du -h output/*.iso

# Write <iso>.sha256 and <iso>.sha512 (add GPG=1 KEY=<key-id> for <iso>.asc)
make sign ISO=output/<name>.iso
```

### 2. Inspect ISO Contents

```bash
# List files in ISO
isoinfo -l -i output/*.iso | less

# Verify autounattend.xml is in ISO root
isoinfo -l -i output/*.iso | grep -i "autounattend.xml"

# Check boot files exist
isoinfo -l -i output/*.iso | grep -E "(boot|efi)"
```

### 3. Verify WIM Images

```bash
# Show WIM info
wimlib-imagex info output/*.iso

# List editions in install.wim
wimlib-imagex info output/*.iso | grep -E "(Index|Name|Edition ID)"

# Check WIM size (smaller = better debloating)
isoinfo -l -i output/*.iso | grep "install.wim"
```

### 4. Test ISO Bootability

**Automated Hyper-V Test (Windows host):**

```powershell
mise run test-iso    # or: pwsh -File scripts/Test-IsoBoot.ps1 -Profile Bypass
```

Boots the newest `output/*.iso` in a throwaway Hyper-V VM (110 GiB disk) and waits for the Hyper-V heartbeat. Needs an elevated shell and an already-built ISO; see `docs/hyperv-testing.md`.

**Virtual Machine Test (manual):**
1. Create a new VM in VirtualBox/VMware/QEMU
2. Mount the ISO as virtual CD
3. Boot from ISO and verify:
   - UEFI boot works
   - Windows Setup starts correctly
   - Autounattend is applied (if configured)
   - Installation proceeds without errors

**Physical Hardware Test:**
1. Write ISO to USB: `dd if=output/*.iso of=/dev/sdX bs=4M status=progress` (replace sdX with your USB device)
2. Boot from USB on target hardware
3. Verify installation proceeds correctly

### 5. Verify Debloating

After installing Windows from your ISO:

```powershell
# List installed AppX packages
Get-AppxPackage | Select Name, PackageFullName | Sort Name

# Check for bloatware
Get-AppxPackage | Where-Object {$_.Name -like "*Xbox*"}
Get-AppxPackage | Where-Object {$_.Name -like "*Solitaire*"}
Get-AppxPackage | Where-Object {$_.Name -like "*Clipchamp*"}

# Verify essential apps remain
Get-AppxPackage | Where-Object {$_.Name -like "*Store*"}
Get-AppxPackage | Where-Object {$_.Name -like "*WebView*"}
```

### 6. Verify Tweaks Applied

Check that SetupComplete.cmd ran successfully:

```powershell
# Check log file
Get-Content C:\Windows\Setup\Scripts\SetupComplete.log

# Verify 8.3 names are disabled
fsutil behavior query disable8dot3

# Check telemetry settings
Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry"

# Verify high performance power plan
powercfg /getactivescheme
```

### Quality Checklist

Before deploying your ISO to production:

- [ ] ISO boots successfully in UEFI mode
- [ ] ISO boots successfully in Legacy BIOS mode (if needed)
- [ ] Windows Setup starts without errors
- [ ] Autounattend.xml is applied (if configured)
- [ ] Installation completes without errors
- [ ] Bloatware apps are removed (verify with Get-AppxPackage)
- [ ] Essential apps remain (Store, WebView2, Defender)
- [ ] SetupComplete.cmd executed successfully
- [ ] Telemetry is reduced to minimum level
- [ ] System is stable and functional
- [ ] Windows Update works correctly
- [ ] Microsoft Store works (if not debloated)

## License

This project uses components from:
- [uup-converter-wimlib](https://github.com/AveYo/MediaCreationTool.bat) - Community UUP converter
- [wimlib](https://wimlib.net/) - WIM manipulation library

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `mise run test` and `mise run lint` (plus `mise run lint-xml`, `lint-reg`, `lint-debloat` for config changes), and test with a full build
4. Add a `CHANGELOG.md` entry for contributor-facing changes
5. Submit a pull request

`AGENTS.md` is the canonical repo guide (hard invariants, script rules, CI checks).

---

**Disclaimer:** This tool modifies Windows installation media. Use at your own risk. Ensure you comply with Microsoft's licensing terms.
