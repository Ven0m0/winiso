#!/bin/bash
# =============================================================================
# validate_prereqs.sh - Validate prerequisites before building ISO
# =============================================================================
# This script validates that all required dependencies, configuration files,
# and directories are present before starting the build process.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"



ERRORS=0
WARNINGS=0

# =============================================================================
# Check Required Tools
# =============================================================================
log_info "Checking required tools..."

check_tool() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 not found. Run 'make deps' to install dependencies."
        ((ERRORS++))
        return 1
    else
        log_success "$1 found"
        return 0
    fi
}

check_tool "aria2c"
check_tool "cabextract"
check_tool "wimlib-imagex"
check_tool "chntpw"

# Check for genisoimage or mkisofs
if command -v genisoimage &> /dev/null; then
    log_success "genisoimage found"
elif command -v mkisofs &> /dev/null; then
    log_success "mkisofs found"
else
    log_error "Neither genisoimage nor mkisofs found. Run 'make deps' to install."
    ((ERRORS++))
fi

echo ""

# =============================================================================
# Check Directory Structure
# =============================================================================
log_info "Checking directory structure..."

if [[ -d "$PROJECT_ROOT/uup_files" ]]; then
    log_success "uup_files directory exists"
else
    log_error "uup_files directory not found at: $PROJECT_ROOT/uup_files"
    ((ERRORS++))
fi

if [[ -d "$PROJECT_ROOT/output" ]]; then
    log_success "output directory exists"
else
    log_warn "output directory not found, will be created"
    mkdir -p "$PROJECT_ROOT/output"
    ((WARNINGS++))
fi

if [[ -d "$PROJECT_ROOT/config" ]]; then
    log_success "config directory exists"
else
    log_error "config directory not found at: $PROJECT_ROOT/config"
    ((ERRORS++))
fi

echo ""

# =============================================================================
# Check UUP Files
# =============================================================================
log_info "Checking for UUP files..."

count_cab=$(find "$PROJECT_ROOT/uup_files" -maxdepth 1 -name "*.cab" 2>/dev/null | wc -l)
count_esd=$(find "$PROJECT_ROOT/uup_files" -maxdepth 1 -iname "*.esd" 2>/dev/null | wc -l)

if [[ $count_cab -eq 0 ]] && [[ $count_esd -eq 0 ]]; then
    log_error "No UUP files (.cab or .esd) found in $PROJECT_ROOT/uup_files"
    echo ""
    echo "To get UUP files:"
    echo "  1. Visit https://uupdump.net"
    echo "  2. Select your desired Windows 11 build"
    echo "  3. Download the UUP package"
    echo "  4. Extract all files to: $PROJECT_ROOT/uup_files"
    echo ""
    ((ERRORS++))
else
    log_success "Found $count_cab CAB files and $count_esd ESD files"
fi

echo ""

# =============================================================================
# Check Configuration Files
# =============================================================================
log_info "Checking configuration files..."

if [[ -f "$PROJECT_ROOT/config/debloat_list.txt" ]]; then
    log_success "debloat_list.txt found"

    # Count non-empty, non-comment lines
    pattern_count=$(grep -v "^#" "$PROJECT_ROOT/config/debloat_list.txt" | grep -v "^[[:space:]]*$" | wc -l)
    log_info "  → $pattern_count debloat patterns configured"
else
    log_warn "debloat_list.txt not found - no apps will be removed"
    ((WARNINGS++))
fi

if [[ -f "$PROJECT_ROOT/config/autounattend.xml" ]]; then
    log_success "autounattend.xml found"

    # Basic XML validation
    if grep -q "<?xml" "$PROJECT_ROOT/config/autounattend.xml"; then
        log_success "  → autounattend.xml appears to be valid XML"
    else
        log_warn "  → autounattend.xml may not be valid XML"
        ((WARNINGS++))
    fi
else
    log_warn "autounattend.xml not found - installation will require manual setup"
    log_info "  → Generate one at: https://schneegans.de/windows/unattend-generator/"
    ((WARNINGS++))
fi

if [[ -d "$PROJECT_ROOT/config/oem" ]]; then
    log_success "OEM scripts directory found"

    if [[ -f "$PROJECT_ROOT/config/oem/SetupComplete.cmd" ]]; then
        log_success "  → SetupComplete.cmd found"
    else
        log_warn "  → SetupComplete.cmd not found - no first-boot tweaks will be applied"
        ((WARNINGS++))
    fi
else
    log_warn "OEM scripts directory not found - no first-boot tweaks will be applied"
    ((WARNINGS++))
fi

echo ""

# =============================================================================
# Check Script Files
# =============================================================================
log_info "Checking build scripts..."

scripts=(
    "build.sh"
    "custom_convert.sh"
    "debloat_wim.sh"
    "setup_env.sh"
)

for script in "${scripts[@]}"; do
    if [[ -f "$PROJECT_ROOT/scripts/$script" ]]; then
        if [[ -x "$PROJECT_ROOT/scripts/$script" ]]; then
            log_success "$script exists and is executable"
        else
            log_warn "$script exists but is not executable"
            chmod +x "$PROJECT_ROOT/scripts/$script"
            log_success "  → Made $script executable"
            ((WARNINGS++))
        fi
    else
        log_error "$script not found at: $PROJECT_ROOT/scripts/$script"
        ((ERRORS++))
    fi
done

echo ""

# =============================================================================
# Environment Variables
# =============================================================================
log_info "Environment configuration..."

log_info "TARGET_EDITION: ${TARGET_EDITION:-ProfessionalWorkstation (default)}"
log_info "FALLBACK_EDITION: ${FALLBACK_EDITION:-Professional (default)}"
log_info "PAUSE_FOR_WINDOWS_STAGE: ${PAUSE_FOR_WINDOWS_STAGE:-0 (disabled)}"

echo ""

# =============================================================================
# Disk Space Check
# =============================================================================
log_info "Checking available disk space..."

available_space=$(df --output=avail -BG "$PROJECT_ROOT" | tail -n 1 | tr -d 'G[:space:]')
if [[ $available_space -lt 20 ]]; then
    log_warn "Low disk space: ${available_space}GB available (20GB+ recommended)"
    ((WARNINGS++))
else
    log_success "Sufficient disk space: ${available_space}GB available"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "=============================================="
if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    log_success "All prerequisite checks passed!"
    log_success "You can proceed with: make build"
elif [[ $ERRORS -eq 0 ]]; then
    log_warn "Prerequisite checks passed with $WARNINGS warning(s)"
    log_info "Build can proceed, but review warnings above"
else
    log_error "Prerequisite validation failed!"
    log_error "Errors: $ERRORS, Warnings: $WARNINGS"
    echo ""
    echo "Please fix the errors above before running 'make build'"
    exit 1
fi
echo "=============================================="

exit 0
