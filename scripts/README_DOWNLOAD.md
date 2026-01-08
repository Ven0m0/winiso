# UUP File Downloader

Automated downloader for Windows 11 UUP files from uupdump.net.

## Quick Start

```bash
# Interactive mode (recommended)
make download

# Or run directly
./scripts/download_uup.py
```

## Features

- **Interactive Selection**: Browse and select from latest Windows 11 builds
- **Edition Filtering**: Choose specific editions (Pro, Enterprise, etc.) or download all
- **Automatic Downloads**: Uses aria2c for fast, resumable downloads
- **API Integration**: Fetches builds directly from uupdump.net API
- **Progress Tracking**: Real-time download progress and status

## Usage

### Interactive Mode (Default)

The script will:
1. Fetch the latest Windows 11 builds from uupdump.net
2. Display them in a numbered list
3. Let you select which build to download
4. Ask which edition you want (or download all)
5. Download files to `uup_files/` directory

```bash
make download
```

### Command Line Options

```bash
# List available builds without downloading
./scripts/download_uup.py --list

# Download specific build by ID
./scripts/download_uup.py --build-id UUID-HERE

# Custom output directory
./scripts/download_uup.py --output /path/to/directory

# Show more builds in list
./scripts/download_uup.py --max-results 20

# Show help
./scripts/download_uup.py --help
```

## Examples

### Example 1: Interactive Download

```bash
$ make download

UUP File Downloader for Windows 11
==================================================
[INFO] Fetching latest Windows 11 builds from uupdump.net...

Available Windows 11 Builds:

[1] Windows 11 23H2 (22631.2861) amd64
    Build: 22631.2861 | Arch: amd64 | Created: 1234567890

[2] Windows 11 23H2 (22631.2792) amd64
    Build: 22631.2792 | Arch: amd64 | Created: 1234567880

Select build number [1-10] or 'q' to quit: 1

Selected: Windows 11 23H2 (22631.2861) amd64
Build ID: 12345678-90ab-cdef-1234-567890abcdef

Available Editions:

[1] Professional
[2] Enterprise
[3] Home
[A] All editions (default)

Select edition [A]: 1

Proceed with download? [Y/n]: y

[INFO] Starting download with aria2c...
```

### Example 2: List Builds Only

```bash
$ ./scripts/download_uup.py --list

Available Windows 11 Builds:

[1] Windows 11 23H2 (22631.2861) amd64
    Build: 22631.2861 | Arch: amd64 | Created: 1234567890
...
```

### Example 3: Direct Build Download

```bash
# If you already know the build ID from uupdump.net
./scripts/download_uup.py --build-id 12345678-90ab-cdef-1234-567890abcdef
```

## How It Works

1. **Fetches Build List**: Queries uupdump.net API for latest Windows 11 builds
2. **User Selection**: Displays builds in a user-friendly format
3. **Edition Filter**: Optionally filters for specific editions
4. **Download Files**: Creates aria2c input file with all download URLs
5. **Parallel Download**: Uses aria2c with 8 connections for fast downloads
6. **Saves to uup_files/**: Files are saved directly to the expected location

## File Organization

After download, your `uup_files/` directory will contain:
- `*.cab` - Cabinet files with Windows components
- `*.esd` - Encrypted/compressed Windows image files
- `*.xml` - Metadata and update information
- Other UUP package files

These files are exactly what you need for the ISO building process.

## Requirements

The script requires:
- **Python 3.6+** (standard library only, no pip packages needed)
- **aria2c** - For fast, parallel downloads (installed by `make deps`)
- **Internet connection** - To fetch builds and download files

## Troubleshooting

### Error: "Missing required tools: aria2c"

**Solution:**
```bash
make deps  # Install dependencies first
```

### Error: "Failed to fetch builds from uupdump.net"

**Causes:**
- Network connectivity issues
- uupdump.net API is down
- Firewall blocking requests

**Solution:**
- Check internet connection
- Try again later
- Use manual download from uupdump.net website

### Download Interrupted

The script uses aria2c with `--continue=true`, so you can:
1. Re-run the same command
2. Downloads will resume from where they stopped
3. Already completed files are skipped

### Wrong Files Downloaded

If you downloaded the wrong build:
```bash
# Clear uup_files directory
rm -rf uup_files/*
# Keep .gitkeep
touch uup_files/.gitkeep

# Run download again
make download
```

### "No files found after filtering"

This happens if you selected an edition that doesn't exist in the build.

**Solution:**
- Select "All editions" option
- Or choose a different edition

## API Information

This script uses the official uupdump.net API:
- **Endpoint**: `https://api.uupdump.net/`
- **No API key required**
- **Rate limits**: Be respectful, don't spam requests
- **Documentation**: https://uupdump.net/

## Security Considerations

- Downloads are fetched directly from Microsoft CDN via uupdump.net
- Files are the same as provided by Windows Update
- No modifications are made during download
- Always verify ISO integrity after building

## Comparison: Script vs Manual

| Method | Pros | Cons |
|--------|------|------|
| **Script (make download)** | Fast, automated, no browser needed | Requires Python, aria2c |
| **Manual (uupdump.net)** | Visual interface, see all details | Slower, more steps, manual file placement |

Both methods are valid - use whichever you prefer!

## Advanced Usage

### Custom API Queries

You can modify the script to search for specific builds:

```python
# In get_latest_builds() function, change search parameter:
params = {
    'search': 'windows 11 pro',  # Search for Pro specifically
    'sortByDate': '1'
}
```

### Download Specific Architectures

Filter by architecture in the build selection:
- amd64 (x64) - Most common
- arm64 - For ARM devices
- x86 - 32-bit (rare for Windows 11)

### Batch Downloads

To download multiple builds:

```bash
# Create a shell script
for build_id in UUID1 UUID2 UUID3; do
    ./scripts/download_uup.py --build-id $build_id --output "uup_files_${build_id}"
done
```

## Contributing

Found a bug or want to improve the downloader?
1. Test your changes with multiple builds
2. Ensure error handling works
3. Update this documentation
4. Submit a pull request

## Credits

- **uupdump.net** - For providing the excellent UUP dump service and API
- **aria2** - For fast, reliable downloads
- This project uses uupdump.net API with respect and appreciation
