# Debloated Windows 11 ISO Builder

A Linux-based automation toolset for creating debloated Windows 11 ISO files from UUP (Unified Update Platform) dump files. Removes bloatware, injects unattended setup configuration, and applies performance tweaks—all while preserving essential system components.

## Features

- **Targeted Edition:** Builds Windows 11 Pro for Workstations (fallback to Pro)
- **70+ Apps Removed:** Xbox, Cortana, Clipchamp, Solitaire, news/weather apps, and more
- **Unattended Setup:** Injects `autounattend.xml` for OOBE bypass and privacy settings
- **First-Boot Tweaks:** Applies telemetry reduction, advertising disable, performance optimizations
- **Optional Windows Stage:** DISM component cleanup, 8.3 short name stripping, registry hardening
- **Preserves Dependencies:** Store, WebView2, VCLibs, Defender, and runtime frameworks remain intact

## Quick Start

### 1. Install Dependencies

```bash
make deps
```

Supports Arch Linux (pacman), Debian/Ubuntu (apt), and Fedora (dnf).

### 2. Download UUP Files

1. Visit [uupdump.net](https://uupdump.net)
2. Select your desired Windows 11 build
3. Download the UUP package
4. Extract/move all files to `uup_files/`

### 3. Configure (Optional)

- **Unattended Setup:** Replace `config/autounattend.xml` with one generated from [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/)
- **Debloat List:** Edit `config/debloat_list.txt` to add/remove app patterns

### 4. Build

```bash
make build
```

The debloated ISO will appear in `output/`.

## Build Options

| Command | Description |
|---------|-------------|
| `make build` | Build ISO with Pro for Workstations (default) |
| `make build-pro` | Build ISO with Pro edition only |
| `make build-pause` | Pause for Windows servicing stage |
| `make clean` | Remove all build artifacts |
| `make help` | Show all available targets |

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
├── scripts/
│   ├── build.sh              # Main build orchestrator
│   ├── custom_convert.sh     # Modified UUP converter
│   ├── debloat_wim.sh        # WIM debloating logic
│   ├── setup_env.sh          # Dependency installer
│   └── windows_service.cmd   # Windows servicing script
├── uup_files/                # Place UUP files here (input)
├── output/                   # Final ISO appears here (output)
├── Makefile                  # Build interface
└── README.md                 # This file
```

## Configuration

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

**No UUP files found:**
Ensure `.cab` and `.esd` files are in `uup_files/`, not in a subdirectory.

**Edition not found:**
Check available editions with: `wimlib-imagex info uup_files/*.esd`

**ISO not created:**
Check for errors in the conversion output. Ensure all dependencies are installed.

**Build artifacts remain:**
Run `make clean` to remove ISODIR and generated ISOs.

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
