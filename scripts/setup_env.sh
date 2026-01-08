#!/bin/bash
# =============================================================================
# setup_env.sh - Install dependencies for Debloated Windows 11 ISO Builder
# =============================================================================
# Supports: Arch Linux (pacman), Debian/Ubuntu (apt), Fedora (dnf)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

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

check_tool() {
    if ! command -v "$1" &> /dev/null; then
        MISSING_TOOLS+=("$1")
    else
        log_success "$1 found: $(command -v "$1")"
    fi
}

check_tool "aria2c"
check_tool "cabextract"
check_tool "wimlib-imagex"
check_tool "chntpw"

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
