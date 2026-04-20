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
    sudo apt-get update -qq
    sudo apt-get install -yqq aria2 python3-apt cabextract wimtools chntpw genisoimage
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

check_tool "aria2c" || MISSING_TOOLS+=("aria2c")
check_tool "cabextract" || MISSING_TOOLS+=("cabextract")
check_tool "wimlib-imagex" || MISSING_TOOLS+=("wimlib-imagex")
check_tool "chntpw" || MISSING_TOOLS+=("chntpw")

# Check for genisoimage or mkisofs
if command -v genisoimage &> /dev/null; then
    log_success "genisoimage found: $(command -v genisoimage)"
elif command -v mkisofs &> /dev/null; then
    log_success "mkisofs found: $(command -v mkisofs)"
else
    MISSING_TOOLS+=("genisoimage/mkisofs")
fi

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
    log_error "Missing tools: ${MISSING_TOOLS[*]}"
    log_error "Please install them manually and re-run."
    exit 1
fi

echo ""
log_success "All dependencies are installed and verified!"
log_info "You can now run: make build"
