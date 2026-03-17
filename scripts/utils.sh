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

# =============================================================================
# Tool check function
# Returns 0 if found, 1 if not found. Outputs appropriate log message.
# =============================================================================
check_tool() {
    local tool="$1"
    if ! command -v "$tool" &> /dev/null; then
        return 1
    else
        log_success "$tool found"
        return 0
    fi
}
