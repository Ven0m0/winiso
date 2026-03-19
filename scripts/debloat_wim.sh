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

source "$SCRIPT_DIR/common.sh"

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
    local index="$1"
    for pattern in "${PATTERNS[@]}"; do
        # WindowsApps directory
        echo "delete --recursive --force \"/Program Files/WindowsApps/$pattern\""
        # AppRepository packages
        echo "delete --recursive --force \"/ProgramData/Microsoft/Windows/AppRepository/Packages/$pattern\""
    done

    if [[ "${NANO:-0}" == "1" ]]; then
        # Manual file deletions from nano11
        echo "delete --recursive --force \"/Windows/Web\""
        echo "delete --recursive --force \"/Windows/Help\""
        echo "delete --recursive --force \"/Windows/Cursors\""
        echo "delete --recursive --force \"/Windows/Speech\""
        echo "delete --recursive --force \"/Windows/System32/Speech\""
        echo "delete --recursive --force \"/Windows/System32/InputMethod/CHS\""
        echo "delete --recursive --force \"/Windows/System32/InputMethod/CHT\""
        echo "delete --recursive --force \"/Windows/System32/InputMethod/JPN\""
        echo "delete --recursive --force \"/Windows/System32/InputMethod/KOR\""
        echo "delete --recursive --force \"/Program Files (x86)/Microsoft/Edge\""
        echo "delete --recursive --force \"/Program Files (x86)/Microsoft/EdgeUpdate\""
        echo "delete --force \"/Windows/System32/OneDriveSetup.exe\""

        # Slimming DriverStore (find and delete patterns)
        # Note: We use wimlib-imagex dir to find matches because delete doesn't support wildcards directly
        local driver_repo="/Windows/System32/DriverStore/FileRepository"
        local driver_patterns="prn|scan|mfd|wscsmd\.inf|tapdrv|rdpbus\.inf|tdibth\.inf"

        # Get matching directories in DriverStore
        { wimlib-imagex dir "$WIM_FILE" "$index" --path="$driver_repo" 2>/dev/null | grep -v "^$driver_repo$" | grep -iE "$driver_patterns" || true; } | while read -r full_path; do
            [[ -n "$full_path" ]] && echo "delete --recursive --force \"$full_path\""
        done

        # Slimming Fonts (Keep only core fonts)
        local fonts_dir="/Windows/Fonts"
        local keep_fonts="segoe|tahoma|marlett|8541oem|segui|consol|lucon|calibri|arial|times|cou|8.*"
        { wimlib-imagex dir "$WIM_FILE" "$index" --path="$fonts_dir" 2>/dev/null | grep -v "^$fonts_dir$" | grep -ivE "$keep_fonts" || true; } | while read -r font_path; do
             [[ -n "$font_path" ]] && echo "delete --force \"$font_path\""
        done

        # NOTE: WinSxS *structural* slimming has been disabled because
        # aggressively whitelisting, moving, and deleting \Windows\WinSxS
        # risks producing an unbootable image and can introduce basename
        # collisions when flattening directories. NANO mode still applies
        # other size optimizations above, but leaves WinSxS intact.
    fi
}

apply_registry_tweaks() {
    local index="$1"
    local temp_reg_dir
    temp_reg_dir=$(mktemp -d)

    log_info "Applying registry tweaks to index $index..."

    # 1. SYSTEM TWEAKS
    if wimlib-imagex extract "$WIM_FILE" "$index" "/Windows/System32/config/SYSTEM" --dest-dir="$temp_reg_dir" --no-acls >/dev/null 2>&1; then
        log_info "  → Modifying SYSTEM hive..."
        {
            # Bypass Hardware Checks
            echo "cd Setup"
            echo "nk LabConfig"
            echo "cd LabConfig"
            echo "nv 4 BypassTPMCheck"
            echo "ed BypassTPMCheck"
            echo "1"
            echo "nv 4 BypassSecureBootCheck"
            echo "ed BypassSecureBootCheck"
            echo "1"
            echo "nv 4 BypassRAMCheck"
            echo "ed BypassRAMCheck"
            echo "1"
            echo "nv 4 BypassCPUCheck"
            echo "ed BypassCPUCheck"
            echo "1"
            echo "nv 4 BypassStorageCheck"
            echo "ed BypassStorageCheck"
            echo "1"
            echo "cd .."
            echo "nk MoSetup"
            echo "cd MoSetup"
            echo "nv 4 AllowUpgradesWithUnsupportedTPMOrCPU"
            echo "ed AllowUpgradesWithUnsupportedTPMOrCPU"
            echo "1"

            # Disable BitLocker
            echo "cd \ControlSet001\Control"
            echo "nk BitLocker"
            echo "cd BitLocker"
            echo "nv 4 PreventDeviceEncryption"
            echo "ed PreventDeviceEncryption"
            echo "1"

            # Disable Services (Start=4)
            local services=(
                "wuauserv" "UsoSvc" "WaaSMedicSvc" "WinDefend" "WdNisSvc" "Sense"
                "dmwappushservice" "Spooler" "Fax" "RemoteRegistry" "diagsvc"
                "WerSvc" "PcaSvc" "MapsBroker" "WalletService"
            )
            for svc in "${services[@]}"; do
                echo "cd \ControlSet001\Services\\$svc"
                echo "ed Start"
                echo "4"
            done

            echo "q"
            echo "y"
        } | chntpw -e "$temp_reg_dir/SYSTEM"

        if [[ $? -ne 0 ]]; then
            log_error "Failed to apply registry tweaks to SYSTEM hive for index $index (chntpw). See error output above."
            rm -rf "$temp_reg_dir"
            return 1
        fi

        if ! wimlib-imagex update "$WIM_FILE" "$index" --command "add $temp_reg_dir/SYSTEM /Windows/System32/config/SYSTEM"; then
            log_error "Failed to write modified SYSTEM hive back to WIM for index $index (wimlib-imagex update). See error output above."
            rm -rf "$temp_reg_dir"
            return 1
        fi
    fi

    # 2. SOFTWARE TWEAKS
    if wimlib-imagex extract "$WIM_FILE" "$index" "/Windows/System32/config/SOFTWARE" --dest-dir="$temp_reg_dir" --no-acls >/dev/null 2>&1; then
        log_info "  → Modifying SOFTWARE hive..."
        {
            # Disable Reserved Storage
            echo "cd Microsoft\Windows\CurrentVersion\ReserveManager"
            echo "ed ShippedWithReserves"
            echo "0"

            # Disable Consumer Features
            echo "cd \Policies\Microsoft\Windows"
            echo "nk CloudContent"
            echo "cd CloudContent"
            echo "nv 4 DisableWindowsConsumerFeatures"
            echo "ed DisableWindowsConsumerFeatures"
            echo "1"

            # OOBE BypassNRO
            echo "cd \Microsoft\Windows\CurrentVersion\OOBE"
            echo "nv 4 BypassNRO"
            echo "ed BypassNRO"
            echo "1"

            # Disable Sponsored Apps
            echo "cd \Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
            echo "nv 4 OemPreInstalledAppsEnabled"
            echo "ed OemPreInstalledAppsEnabled"
            echo "0"
            echo "nv 4 PreInstalledAppsEnabled"
            echo "ed PreInstalledAppsEnabled"
            echo "0"
            echo "nv 4 SilentInstalledAppsEnabled"
            echo "ed SilentInstalledAppsEnabled"
            echo "0"

            # Disable Copilot & Chat
            echo "cd \Policies\Microsoft\Windows"
            echo "nk WindowsCopilot"
            echo "cd WindowsCopilot"
            echo "nv 4 TurnOffWindowsCopilot"
            echo "ed TurnOffWindowsCopilot"
            echo "1"
            echo "cd .."
            echo "nk \"Windows Chat\""
            echo "cd \"Windows Chat\""
            echo "nv 4 ChatIcon"
            echo "ed ChatIcon"
            echo "3"

            echo "q"
            echo "y"
        } | chntpw -e "$temp_reg_dir/SOFTWARE"

        if [[ $? -ne 0 ]]; then
            log_error "Failed to apply registry tweaks to SOFTWARE hive for index $index (chntpw). See error output above."
            rm -rf "$temp_reg_dir"
            return 1
        fi

        if ! wimlib-imagex update "$WIM_FILE" "$index" --command "add $temp_reg_dir/SOFTWARE /Windows/System32/config/SOFTWARE"; then
            log_error "Failed to write modified SOFTWARE hive back to WIM for index $index (wimlib-imagex update). See error output above."
            rm -rf "$temp_reg_dir"
            return 1
        fi
    fi

    rm -rf "$temp_reg_dir"
}

# Process each index in the WIM
for index in $(seq 1 "$IMAGE_COUNT"); do
    log_info "Processing index $index of $IMAGE_COUNT..."

    # Get edition name for logging
    EDITION=$(wimlib-imagex info "$WIM_FILE" "$index" 2>/dev/null | grep "^Name:" | sed 's/^Name:[[:space:]]*//' || echo "Unknown")
    log_info "Edition: $EDITION"

    # Create temp command file
    CMD_FILE=$(mktemp)
    generate_commands "$index" > "$CMD_FILE"

    # Execute debloat commands
    # Note: wimlib returns non-zero if some files don't exist, which is expected
    if wimlib-imagex update "$WIM_FILE" "$index" < "$CMD_FILE" 2>&1 | grep -v "does not exist" | head -20; then
        log_success "Debloat commands executed for index $index"
    else
        log_warn "Some patterns may not have matched (this is normal for missing apps)"
    fi

    if [[ "${NANO:-0}" == "1" ]]; then
        apply_registry_tweaks "$index"
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
