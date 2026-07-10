#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils.sh"

SIGN_GPG=0
GPG_KEY_ID=""
ISO_FILE=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] <iso-file>

Generate SHA256/SHA512 checksums and (optionally) a GPG detached signature
for the given ISO file. Writes <iso>.sha256, <iso>.sha512, and (if GPG is
enabled) <iso>.asc next to the input file.

Options:
  --gpg                   Also create a GPG detached signature
  --key KEY_ID            GPG key ID or email to sign with (implies --gpg)
  -h, --help              Show this help

Examples:
  $(basename "$0") output/Win11_22631.iso
  $(basename "$0") --gpg --key maintainer@example.com output/Win11_22631.iso
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gpg)
      SIGN_GPG=1
      shift
      ;;
    --key)
      SIGN_GPG=1
      GPG_KEY_ID="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
    *)
      ISO_FILE="$1"
      shift
      ;;
  esac
done

if [[ -z "$ISO_FILE" ]]; then
  log_error "No ISO file specified"
  usage
  exit 1
fi

ISO_PATH="$(readlink -f "$ISO_FILE")"
ISO_DIR="$(dirname "$ISO_PATH")"

if [[ ! -f "$ISO_PATH" ]]; then
  log_error "ISO file not found: $ISO_PATH"
  exit 1
fi

log_info "Generating checksums for: $ISO_PATH"

cd "$ISO_DIR"
sha256sum "$(basename "$ISO_PATH")" > "$(basename "$ISO_PATH").sha256"
log_success "Wrote $(basename "$ISO_PATH").sha256"

sha512sum "$(basename "$ISO_PATH")" > "$(basename "$ISO_PATH").sha512"
log_success "Wrote $(basename "$ISO_PATH").sha512"

if [[ "$SIGN_GPG" -eq 1 ]]; then
  if ! command -v gpg >/dev/null 2>&1; then
    log_error "gpg is not installed; cannot sign"
    exit 1
  fi
  log_info "Creating GPG detached signature"
  if [[ -n "$GPG_KEY_ID" ]]; then
    gpg --batch --yes --local-user "$GPG_KEY_ID" \
      --output "$(basename "$ISO_PATH").asc" \
      --armor --detach-sign "$(basename "$ISO_PATH")"
  else
    gpg --batch --yes \
      --output "$(basename "$ISO_PATH").asc" \
      --armor --detach-sign "$(basename "$ISO_PATH")"
  fi
  log_success "Wrote $(basename "$ISO_PATH").asc"
fi

log_success "Signing complete"
