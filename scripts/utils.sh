#!/bin/bash
# =============================================================================
# utils.sh - Shared utility functions for shell scripts
# =============================================================================

# Colors
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export CYAN='\033[0;36m'
export NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Required tools for the build process
REQUIRED_TOOLS=("aria2c" "cabextract" "wimlib-imagex" "chntpw")

# =============================================================================
# Tool check function
# Returns 0 if found, 1 if not found. Outputs appropriate log message.
# =============================================================================
check_tool() {
    local tool="$1"
    if ! command -v "$tool" &> /dev/null; then
        log_error "$tool not found"
        return 1
    else
        log_success "$tool found"
        return 0
    fi
}

# =============================================================================
# ISO creation tool check
# Returns 0 if genisoimage or mkisofs is found, 1 otherwise.
# =============================================================================
check_iso_tool() {
    if command -v genisoimage &> /dev/null; then
        log_success "genisoimage found"
        return 0
    elif command -v mkisofs &> /dev/null; then
        log_success "mkisofs found"
        return 0
    else
        return 1
    fi
}

# =============================================================================
# Check multiple required tools
# Arguments: List of tools to check
# Returns: Number of missing tools.
# =============================================================================
check_required_tools() {
    local missing_count=0
    for tool in "$@"; do
        if ! check_tool "$tool"; then
            ((missing_count++))
        fi
    done
    return "$missing_count"
}
