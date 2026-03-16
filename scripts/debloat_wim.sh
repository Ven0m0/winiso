#!/bin/bash
# debloat_wim.sh - Remove bloatware from Windows install.wim
# Usage: ./debloat_wim.sh <path_to_install.wim>
#
# Features:
#   - Processes ALL indexes in the WIM (not just index 1)
#   - Case-insensitive matching (like Windows filesystem)
#   - CRLF/whitespace tolerant config parsing
#   - Safe deletion (continues on missing files)

set -euo pipefail

WIM_FILE="$1"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/debloat_list.txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ -z "${WIM_FILE:-}" ]]; then
    log_error "No WIM file specified."
    echo "Usage: $0 <path_to_install.wim>"
    exit 1
fi

if [[ ! -f "$WIM_FILE" ]]; then
    log_error "WIM file not found: $WIM_FILE"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_warn "Config file not found at $CONFIG_FILE. Skipping debloat."
    exit 0
fi

# Ensure case-insensitive matching (like Windows NTFS)
export WIMLIB_IMAGEX_IGNORE_CASE=1

# Get number of indexes in the WIM
IMAGE_COUNT=$(wimlib-imagex info "$WIM_FILE" | grep -c "^Index:" || echo "0")
if [[ "$IMAGE_COUNT" -eq 0 ]]; then
    # Fallback: count via parsing
    IMAGE_COUNT=$(wimlib-imagex info "$WIM_FILE" | grep "^Image Count:" | sed 's/.*: *//')
fi

log_info "WIM file: $WIM_FILE"
log_info "Image count: $IMAGE_COUNT"
log_info "Config file: $CONFIG_FILE"

# Parse config file: strip CRLF, trim whitespace, skip comments/empty lines
PATTERNS=()
while IFS= read -r line || [[ -n "$line" ]]; do
    # Remove CRLF and trim whitespace
    line=$(echo "$line" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Skip comments and empty lines
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^# ]] && continue
    PATTERNS+=("$line")
done < "$CONFIG_FILE"

log_info "Loaded ${#PATTERNS[@]} debloat patterns"

# Generate delete commands
generate_commands() {
    for pattern in "${PATTERNS[@]}"; do
        # WindowsApps directory
        echo "delete --recursive --force \"/Program Files/WindowsApps/$pattern\""
        # AppRepository packages
        echo "delete --recursive --force \"/ProgramData/Microsoft/Windows/AppRepository/Packages/$pattern\""
    done
}

# Process each index in the WIM
for index in $(seq 1 "$IMAGE_COUNT"); do
    log_info "Processing index $index of $IMAGE_COUNT..."

    # Get edition name for logging
    EDITION=$(wimlib-imagex info "$WIM_FILE" "$index" 2>/dev/null | grep "^Name:" | sed 's/^Name:[[:space:]]*//' || echo "Unknown")
    log_info "Edition: $EDITION"

    # Create temp command file
    CMD_FILE=$(mktemp)
    generate_commands > "$CMD_FILE"

    # Execute debloat commands
    # Note: wimlib returns non-zero if some files don't exist, which is expected
    if wimlib-imagex update "$WIM_FILE" "$index" < "$CMD_FILE" 2>&1 | grep -v "does not exist" | head -20; then
        log_success "Debloat commands executed for index $index"
    else
        log_warn "Some patterns may not have matched (this is normal for missing apps)"
    fi

    rm -f "$CMD_FILE"
done

# Optimize the WIM to reclaim space
log_info "Optimizing WIM file to reclaim space..."
if wimlib-imagex optimize "$WIM_FILE" --recompress; then
    log_success "WIM optimization complete"
else
    log_warn "WIM optimization returned non-zero (may still be OK)"
fi

# Report final size
FINAL_SIZE=$(du -h "$WIM_FILE" | cut -f1)
log_success "Debloating complete. Final WIM size: $FINAL_SIZE"
