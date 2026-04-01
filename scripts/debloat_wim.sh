#!/bin/bash
# debloat_wim.sh - Remove bloatware from Windows install.wim
# Usage: ./debloat_wim.sh <path_to_install.wim>
#
# Features:
#   - Processes ALL indexes in the WIM
#   - Offline registry tweaking (Privacy, Performance, AI disabling, Bypasses)
#   - Nano mode for aggressive debloating (NANO=1)
#   - Case-insensitive matching

set -euo pipefail

WIM_FILE="$1"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/debloat_list.txt"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/utils.sh"

if [[ -z "${WIM_FILE:-}" ]]; then
  log_error "No WIM file specified."
  echo "Usage: $0 <path_to_install.wim>"
  exit 1
fi

if [[ ! -f "$WIM_FILE" ]]; then
  log_error "WIM file not found: $WIM_FILE"
  exit 1
fi

# Ensure case-insensitive matching
export WIMLIB_IMAGEX_IGNORE_CASE=1

# Get number of indexes
WIM_INFO_OUTPUT=$(wimlib-imagex info "$WIM_FILE" 2>/dev/null || echo "")
IMAGE_COUNT=$(echo "$WIM_INFO_OUTPUT" | grep -c "^Index:" || echo "0")

declare -a EDITION_NAMES
CURRENT_INDEX=""
while IFS= read -r line; do
  if [[ "$line" =~ ^Index:[[:space:]]+([0-9]+)$ ]]; then
    CURRENT_INDEX="${BASH_REMATCH[1]}"
  elif [[ "$line" =~ ^Name:[[:space:]]+(.*)$ ]] && [[ -n "${CURRENT_INDEX:-}" ]]; then
    name="${BASH_REMATCH[1]}"
    EDITION_NAMES[CURRENT_INDEX]="${name%$'\r'}"
    CURRENT_INDEX=""
  fi
done <<< "$WIM_INFO_OUTPUT"

# Parse config file
PATTERNS=()
if [[ -f "$CONFIG_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(echo "$line" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^# ]] && continue
    PATTERNS+=("$line")
  done <"$CONFIG_FILE"
fi

# Function to apply registry tweaks using chntpw
apply_registry_tweaks() {
  local index=$1
  local temp_reg_dir
  temp_reg_dir=$(mktemp -d)

  log_info "Applying registry tweaks to index $index..."

  # 1. SOFTWARE HIVE
  wimlib-imagex extract "$WIM_FILE" "$index" "/Windows/System32/config/SOFTWARE" --dest-dir="$temp_reg_dir" --no-acls >/dev/null 2>&1 || true

  if [[ -f "$temp_reg_dir/SOFTWARE" ]]; then
    # Disable Consumer Experience, Telemetry, and AI
    # Using nk to ensure keys exist before navigation
    chntpw -e "$temp_reg_dir/SOFTWARE" <<EOF >/dev/null 2>&1
nk Microsoft\Windows\CurrentVersion\CloudContent
cd Microsoft\Windows\CurrentVersion\CloudContent
nv 4 DisableWindowsConsumerFeatures
ed DisableWindowsConsumerFeatures
1
nv 4 DisableCloudOptimizedContent
ed DisableCloudOptimizedContent
1
cd \
nk Policies\Microsoft\Windows\CloudContent
cd Policies\Microsoft\Windows\CloudContent
nv 4 DisableWindowsConsumerFeatures
ed DisableWindowsConsumerFeatures
1
cd \
nk Microsoft\Windows\CurrentVersion\DataCollection
cd Microsoft\Windows\CurrentVersion\DataCollection
nv 4 AllowTelemetry
ed AllowTelemetry
0
cd \
nk Policies\Microsoft\Windows\WindowsCopilot
cd Policies\Microsoft\Windows\WindowsCopilot
nv 4 TurnOffWindowsCopilot
ed TurnOffWindowsCopilot
1
cd \
nk Microsoft\Windows\CurrentVersion\Explorer
cd Microsoft\Windows\CurrentVersion\Explorer
nv 4 HubMode
ed HubMode
1
q
y
EOF
    wimlib-imagex update "$WIM_FILE" "$index" --command "add '$temp_reg_dir/SOFTWARE' '/Windows/System32/config/SOFTWARE'" >/dev/null 2>&1
  fi

  # 2. SYSTEM HIVE
  wimlib-imagex extract "$WIM_FILE" "$index" "/Windows/System32/config/SYSTEM" --dest-dir="$temp_reg_dir" --no-acls >/dev/null 2>&1 || true
  if [[ -f "$temp_reg_dir/SYSTEM" ]]; then
    # Disable DiagTrack and dmwappushservice across common control sets
    CONTROL_SETS=("ControlSet001" "ControlSet002" "ControlSet003")
    for cs in "${CONTROL_SETS[@]}"; do
      chntpw -e "$temp_reg_dir/SYSTEM" <<EOF >/dev/null 2>&1
nk $cs\Services\DiagTrack
cd $cs\Services\DiagTrack
nv 4 Start
ed Start
4
cd \
nk $cs\Services\dmwappushservice
cd $cs\Services\dmwappushservice
nv 4 Start
ed Start
4
cd \
EOF
    done

    # Apply hardware bypasses (root-level Setup\LabConfig)
    chntpw -e "$temp_reg_dir/SYSTEM" <<EOF >/dev/null 2>&1
nk Setup\LabConfig
cd Setup\LabConfig
nv 4 BypassTPMCheck
ed BypassTPMCheck
1
nv 4 BypassSecureBootCheck
ed BypassSecureBootCheck
1
nv 4 BypassRAMCheck
ed BypassRAMCheck
1
nv 4 BypassStorageCheck
ed BypassStorageCheck
1
nv 4 BypassCPUCheck
ed BypassCPUCheck
1
cd \
nk Setup\MoSetup
cd Setup\MoSetup
nv 4 AllowUpgradesWithUnsupportedTPMOrCPU
ed AllowUpgradesWithUnsupportedTPMOrCPU
1
q
y
EOF
    wimlib-imagex update "$WIM_FILE" "$index" --command "add '$temp_reg_dir/SYSTEM' '/Windows/System32/config/SYSTEM'" >/dev/null 2>&1
  fi

  rm -rf "$temp_reg_dir"
}

# Generate deletion commands
generate_commands() {
  for pattern in "${PATTERNS[@]}"; do
    echo "delete --recursive --force \"/Program Files/WindowsApps/$pattern\""
    echo "delete --recursive --force \"/ProgramData/Microsoft/Windows/AppRepository/Packages/$pattern\""
  done

  if [[ "${NANO:-0}" == "1" ]]; then
    # Aggressive Nano deletions
    echo "delete --recursive --force \"/Program Files (x86)/Microsoft/Edge\""
    echo "delete --recursive --force \"/Program Files (x86)/Microsoft/EdgeCore\""
    echo "delete --recursive --force \"/Program Files (x86)/Microsoft/EdgeUpdate\""
    # DriverStore deletion removed as it is too risky/destructive for a general builder
    echo "delete --recursive --force \"/Windows/Fonts/malgun.ttf\""
    echo "delete --recursive --force \"/Windows/Fonts/msjh.ttc\""
    echo "delete --recursive --force \"/Windows/Fonts/msyh.ttc\""
    echo "delete --recursive --force \"/Windows/Fonts/msyhl.ttc\""
    echo "delete --recursive --force \"/Windows/Fonts/msyhbd.ttc\""
  fi
}

CMD_FILE=$(mktemp)
generate_commands >"$CMD_FILE"

# Process each index
for index in $(seq 1 "$IMAGE_COUNT"); do
  EDITION="${EDITION_NAMES[$index]:-Unknown}"
  log_info "Processing index $index: $EDITION"

  # AppX Debloating
  if [[ ${#PATTERNS[@]} -gt 0 ]] || [[ "${NANO:-0}" == "1" ]]; then
    wimlib-imagex update "$WIM_FILE" "$index" <"$CMD_FILE" 2>&1 | grep -v "does not exist" | head -n 20 || true
  fi

  # Registry Tweaking
  apply_registry_tweaks "$index"

  # WinSxS Slimming (Nano mode only)
  if [[ "${NANO:-0}" == "1" ]]; then
    log_info "Performing WinSxS slimming for index $index..."
    wimlib-imagex update "$WIM_FILE" "$index" <<EOF >/dev/null 2>&1 || true
delete --recursive --force "/Windows/WinSxS/Backup"
delete --recursive --force "/Windows/WinSxS/ManifestCache"
delete --recursive --force "/Windows/WinSxS/Temp"
EOF
  fi
done

rm -f "$CMD_FILE"

log_info "Optimizing WIM..."
wimlib-imagex optimize "$WIM_FILE" --recompress || log_warn "Optimization returned non-zero"

log_success "WIM processing complete. Size: $(du -h "$WIM_FILE" | cut -f1)"
