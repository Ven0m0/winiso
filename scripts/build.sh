#!/bin/bash
# =============================================================================
# build.sh - Orchestrator for Debloated Windows 11 ISO
# =============================================================================
# This script orchestrates the UUP to ISO conversion with debloating.
#
# Environment Variables:
#   TARGET_EDITION       - Preferred edition (default: ProfessionalWorkstation)
#   FALLBACK_EDITION     - Fallback edition (default: Professional)
#   PAUSE_FOR_WINDOWS_STAGE - Set to 1 to pause for Windows servicing
#
# Usage:
#   ./build.sh                    # Normal build
#   PAUSE_FOR_WINDOWS_STAGE=1 ./build.sh  # Pause for Windows servicing
# =============================================================================

set -euo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
UUP_DIR="$PROJECT_ROOT/uup_files"
OUTPUT_DIR="$PROJECT_ROOT/output"

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

# Run prerequisite validation
log_info "Running prerequisite validation..."
if ! bash "$SCRIPT_DIR/validate_prereqs.sh"; then
    log_error "Prerequisite validation failed. Please fix errors and try again."
    exit 1
fi
echo ""

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Check for UUP files (look for .cab and .esd files)
count_cab=$(find "$UUP_DIR" -maxdepth 1 -name "*.cab" 2>/dev/null | wc -l)
count_esd=$(find "$UUP_DIR" -maxdepth 1 -iname "*.esd" 2>/dev/null | wc -l)

if [[ $count_cab -eq 0 ]] && [[ $count_esd -eq 0 ]]; then
    log_error "No UUP files (.cab or .esd) found in $UUP_DIR"
    echo ""
    echo "To get UUP files:"
    echo "  1. Visit https://uupdump.net and select your Windows 11 build"
    echo "  2. Download the UUP package"
    echo "  3. Extract or move files to: $UUP_DIR"
    echo ""
    exit 1
fi

log_info "Starting Build Process..."
log_info "Source: $UUP_DIR"
log_info "Output: $OUTPUT_DIR"
log_info "Target Edition: ${TARGET_EDITION:-ProfessionalWorkstation}"
log_info "Fallback Edition: ${FALLBACK_EDITION:-Professional}"
echo ""

# Clean previous build artifacts
log_info "Cleaning previous build artifacts..."
rm -rf "$SCRIPT_DIR/ISODIR"

# Change to scripts directory for converter (it uses relative paths)
cd "$SCRIPT_DIR"

# Export environment for the converter
export TARGET_EDITION="${TARGET_EDITION:-ProfessionalWorkstation}"
export FALLBACK_EDITION="${FALLBACK_EDITION:-Professional}"
export PAUSE_FOR_WINDOWS_STAGE="${PAUSE_FOR_WINDOWS_STAGE:-0}"
export WIMLIB_IMAGEX_IGNORE_CASE=1

# Run Custom Converter
# Usage: ./custom_convert.sh [compression] [uups_directory] [create_virtual_editions]
# We force 'wim' compression because 'esd' cannot be reliably modified
log_info "Running UUP converter with debloating..."
if ! bash "$SCRIPT_DIR/custom_convert.sh" wim "$UUP_DIR" 0; then
    log_error "Build failed during conversion."
    exit 1
fi

# Find the ISO file (converter creates it in current directory)
ISO_FILE=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.iso" -type f 2>/dev/null | head -n 1)

# Also check current directory if different
if [[ -z "$ISO_FILE" ]]; then
    ISO_FILE=$(find "$(pwd)" -maxdepth 1 -name "*.iso" -type f 2>/dev/null | head -n 1)
fi

if [[ -f "$ISO_FILE" ]]; then
    ISO_NAME=$(basename "$ISO_FILE")
    log_success "ISO created: $ISO_NAME"

    # Move to output directory
    log_info "Moving $ISO_NAME to $OUTPUT_DIR..."
    mv "$ISO_FILE" "$OUTPUT_DIR/"

    # Get final size
    FINAL_SIZE=$(du -h "$OUTPUT_DIR/$ISO_NAME" | cut -f1)

    echo ""
    log_success "======================================"
    log_success "Build Complete!"
    log_success "======================================"
    echo "  ISO: $OUTPUT_DIR/$ISO_NAME"
    echo "  Size: $FINAL_SIZE"
    echo ""
else
    log_error "ISO file not found after conversion."
    log_warn "Check for errors above. The converter may have failed."
    exit 1
fi

# Cleanup
log_info "Cleaning up build artifacts..."
rm -rf "$SCRIPT_DIR/ISODIR"

log_success "Done."
