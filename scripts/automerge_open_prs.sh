#!/bin/bash
# =============================================================================
# automerge_open_prs.sh - Enable auto-merge for all open pull requests
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

MERGE_METHOD="${MERGE_METHOD:-squash}"
INCLUDE_DRAFTS="${INCLUDE_DRAFTS:-false}"
GH_REPO="${GH_REPO:-${GITHUB_REPOSITORY:-}}"
export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

case "$MERGE_METHOD" in
    merge|squash|rebase) ;;
    *)
        log_error "MERGE_METHOD must be one of: merge, squash, rebase"
        exit 1
        ;;
esac

case "$INCLUDE_DRAFTS" in
    true|false) ;;
    *)
        log_error "INCLUDE_DRAFTS must be 'true' or 'false'"
        exit 1
        ;;
esac

if [[ -z "$GH_REPO" ]]; then
    log_error "GH_REPO or GITHUB_REPOSITORY must be set."
    exit 1
fi

if [[ -z "$GH_TOKEN" ]]; then
    log_error "GH_TOKEN or GITHUB_TOKEN must be set."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is required to auto-merge pull requests."
    exit 1
fi

log_info "Scanning open pull requests for $GH_REPO..."

if [[ "$INCLUDE_DRAFTS" == "true" ]]; then
    jq_filter='.[] | .number'
else
    jq_filter='.[] | select(.draft | not) | .number'
fi

mapfile -t pr_numbers < <(gh api --paginate "repos/$GH_REPO/pulls?state=open&per_page=100" --jq "$jq_filter")

if [[ "${#pr_numbers[@]}" -eq 0 ]]; then
    log_info "No eligible open pull requests found."
    exit 0
fi

log_info "Found ${#pr_numbers[@]} eligible pull request(s)."

failed_prs=()
merge_flag="--$MERGE_METHOD"

for pr_number in "${pr_numbers[@]}"; do
    [[ -n "$pr_number" ]] || continue

    log_info "Enabling auto-merge for PR #$pr_number using '$MERGE_METHOD'..."
    if gh pr merge --repo "$GH_REPO" "$pr_number" --auto "$merge_flag"; then
        log_success "Auto-merge enabled for PR #$pr_number"
    else
        log_warn "Unable to enable auto-merge for PR #$pr_number"
        failed_prs+=("$pr_number")
    fi
done

if [[ "${#failed_prs[@]}" -gt 0 ]]; then
    log_error "Auto-merge could not be enabled for: ${failed_prs[*]}"
    exit 1
fi

log_success "Auto-merge has been enabled for all eligible open pull requests."
