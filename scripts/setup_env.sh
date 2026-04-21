#!/bin/bash
# =============================================================================
# setup_env.sh - Install dependencies for Debloated Windows 11 ISO Builder
# =============================================================================
# Supports: Arch Linux (pacman), Debian/Ubuntu (apt), Fedora (dnf)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/utils.sh"

log_info "Checking and installing dependencies..."

# Detect package manager
if command -v pacman &> /dev/null; then
    log_info "Detected Arch Linux (pacman)"
    sudo pacman -S --needed aria2 cabextract wimlib chntpw cdrtools
elif command -v apt &> /dev/null; then
    log_info "Detected Debian/Ubuntu (apt)"
    sudo apt update
    sudo apt install -y aria2 cabextract wimtools chntpw genisoimage
elif command -v dnf &> /dev/null; then
    log_info "Detected Fedora (dnf)"
    sudo dnf install -y aria2 cabextract wimlib-utils chntpw genisoimage
else
    log_error "Unsupported package manager. Please install manually:"
    echo "  - aria2 (download acceleration)"
    echo "  - cabextract (Windows cabinet extraction)"
    echo "  - wimlib / wimtools (WIM manipulation)"
    echo "  - chntpw (Windows registry editing)"
    echo "  - genisoimage / cdrtools (ISO creation)"
    exit 1
fi

# Verify critical tools are available
log_info "Verifying tool availability..."

MISSING_TOOLS=()

# Check primary tools using centralized list
for tool in "${REQUIRED_TOOLS[@]}"; do
    check_tool "$tool" || MISSING_TOOLS+=("$tool")
done

# Check ISO creation tools
check_iso_tool || MISSING_TOOLS+=("genisoimage/mkisofs")

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
    log_error "Missing tools: ${MISSING_TOOLS[*]}"
    log_error "Please install them manually and re-run."
    exit 1
fi

echo ""
log_success "All dependencies are installed and verified!"
log_info "You can now run: make build"
