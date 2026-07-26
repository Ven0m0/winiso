# Debloated Windows 11 ISO Builder

[![Maintainability](https://qlty.sh/gh/Ven0m0/projects/winiso/maintainability.svg)](https://qlty.sh/gh/Ven0m0/projects/winiso)

A Linux-based automation toolset for creating debloated Windows 11 ISO files from UUP (Unified Update Platform) dump files. Removes bloatware, injects unattended setup configuration, and applies performance tweaks—all while preserving essential system components.

## Features

- **Automated UUP Download:** Interactive downloader for fetching Windows 11 builds from uupdump.net
- **Pre-Build Validation:** Checks dependencies, files, and configuration before starting
- **Targeted Edition:** Builds Windows 11 Pro for Workstations (fallback to Pro)
- **70+ Apps Removed:** Xbox, Cortana, Clipchamp, Solitaire, news/weather apps, and more
- **Unattended Setup:** Injects `autounattend.xml` for OOBE bypass and privacy settings
- **First-Boot Tweaks:** Applies telemetry reduction, advertising disable, performance optimizations
- **Optional Windows Stage:** DISM component cleanup, 8.3 short name stripping, registry hardening
- **Preserves Dependencies:** Store, WebView2, VCLibs, Defender, and runtime frameworks remain intact

## Quick Start

### 1. Install Dependencies

**Option A: Using mise (Recommended)**

```bash
mise trust mise.toml
mise run install-deps
```

Uses [mise](https://mise.jdx.dev/) for cross-platform tool management.

**Option B: Using Make**

```bash
make deps
```

Supports Arch Linux (pacman), Debian/Ubuntu (apt), and Fedora (dnf).

### 2. Download UUP Files

**Option A: Automatic Download (Recommended)**

```bash
make download
```

This launches an interactive menu to select and download Windows 11 builds directly from uupdump.net.

**Option B: Manual Download**

1. Visit [uupdump.net](https://uupdump.net)
2. Select your desired Windows 11 build
3. Download the UUP package
4. Extract/move all files to `uup_files/`

**Important:** Ensure all `.cab` and `.esd` files are directly in `uup_files/`, not in a subdirectory.

### 3. Configure (Optional)

- **Unattended Setup:** Replace `config/autounattend.xml` with one generated from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/)
- **Debloat List:** Edit `config/debloat_list.txt` to add/remove app patterns

### 4. Validate Prerequisites (Recommended)

```bash
make validate
```

This checks that all dependencies, UUP files, and configuration are ready.

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
```

### Using Make

| Make Command | mise equivalent | Description |
|-------------|----------------|-------------|
| `make deps` | `mise run install-deps` | Install system dependencies |
| `make download` | `mise run download` | Download UUP files |
| `make validate` | `mise run validate` | Validate prerequisites |
| `make build` | `mise run build` | Build ISO (default) |
| `make build-pro` | `mise run build-pro` | Build Pro edition |
| `make build-pause` | `mise run build-pause` | Pause for servicing |
| `make clean` | `mise run clean-unix` | Remove artifacts |

### Direct Scripts

```bash
./scripts/setup_env.py   # Install dependencies
./scripts/download_uup.py --list  # List builds
./scripts/build.py       # Build ISO
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred Windows edition |
| `FALLBACK_EDITION` | `Professional` | Fallback if target not found |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Set to `1` for Windows servicing |

## Windows Servicing Stage (Optional)

For maximum optimization (DISM cleanup + 8.3 stripping), use the Windows servicing stage:

```bash
make build-pause
```

When paused:
1. Copy `scripts/ISODIR/sources/install.wim` to a Windows machine
2. Run `scripts\windows_service.cmd C:\path\to\install.wim` as Administrator
3. Copy the serviced WIM back
4. Press Enter to continue ISO generation

## Project Structure

```
├── config/
│   ├── autounattend.xml      # Unattended setup configuration
│   ├── debloat_list.txt      # App removal patterns
│   └── oem/
│       └── SetupComplete.cmd # First-boot tweaks script
├── docs/
│   └── autounattend.md       # Guide for autounattend.xml customization
├── scripts/
│   ├── build.py              # Main build orchestrator
│   ├── custom_convert.sh     # Modified UUP converter (upstream-derived, stays bash)
│   ├── convert_config.sh     # Shared converter config (sourced by custom_convert.sh)
│   ├── debloat_wim.py        # WIM debloating logic
│   ├── setup_env.py          # Dependency installer
│   ├── apply_image_settings.py # Windows-side ISO extraction/debloat (dism.exe-based)
│   └── windows_service.cmd   # Windows servicing script
├── uup_files/                # Place UUP files here (input)
├── output/                   # Final ISO appears here (output)
├── Makefile                  # Build interface
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

### Autounattend.xml

Generate from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/) with recommended settings:
- Skip Microsoft Account (use local account)
- Disable privacy prompts
- Minimal telemetry
- Keep: Defender, Store, Windows Update

## Alternative: NTLite (manual, Windows-only)

Prefer NTLite's GUI over this repo's automated Linux pipeline? Mount the WIM in NTLite and
import `config/ntlite-presets/Win11-25H2.xml`, then import `scripts/apply.reg` (via NTLite's
Registry tab or `regedit`) for the setup bypasses the preset doesn't include. See
`AGENTS.md` for the full breakdown. Neither file is used by `build.py`/`debloat_wim.py`.

## Requirements

- **Linux:** Arch Linux, Debian/Ubuntu, or Fedora
- **Tools:** wimlib, aria2, cabextract, chntpw, genisoimage/cdrtools
- **Disk Space:** ~20GB for build process
- **Optional:** Windows machine for DISM servicing stage

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

# Check autounattend.xml validity
xmllint --noout config/autounattend.xml 2>/dev/null && echo "Valid XML" || echo "Invalid XML"

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

**Virtual Machine Test (Recommended):**
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
3. Test your changes with a full build
4. Submit a pull request

---

**Disclaimer:** This tool modifies Windows installation media. Use at your own risk. Ensure you comply with Microsoft's licensing terms.
