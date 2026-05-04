# Implementation Plan
_Generated: 2026-05-04T06:34:53Z · 6 tasks · Est. 50 LOC_

## Summary
This codebase contains 1 TODO marker in source code (`mise.toml:136`) and comprehensive roadmap documentation in TODO.md (50 items). The TODO marker addresses Windows package manager gap for `cabextract` and `genisoimage`. Technical debt items from PLAN.md and TODO.md are synthesized below.

## Task Index (topological order)
| # | ID | Title | Sev | Cat | Size | Blocks |
|---|-----|-------|-----|-----|------|--------|
| 1 | T001 | Windows dependency installation | medium | feature | S | — |
| 2 | T002 | ShellCheck SC2034 suppression | low | debt | S | — |
| 3 | T003 | Python type hints - download_uup.py | medium | refactor | M | — |
| 4 | T004 | Error handling standardization | high | bug | M | — |
| 5 | T005 | Unified logging levels | medium | refactor | M | T004 |
| 6 | T006 | Test coverage 40%→80% | high | debt | L | — |

## Tasks

### T001 · Install cabextract/genisoimage on Windows
**File:** `mise.toml:136`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:**
```toml
# TODO / FIXME: install "cabextract genisoimage" on windows. Neither choco nor scoop have them
```
**Intent:** Provide Windows installation method for required build tools
**Acceptance criteria:**
- [ ] Identify alternative installation method (manual download, winget, or custom script)
- [ ] Document installation in README.md Windows section
- [ ] Update tasks.windows in mise.toml with working command
**Implementation:**
Option 1: Use chocolatey-packages/manual-download wrapper script
Option 2: Add to build.sh to download from known URLs if missing
```
**Estimated LOC delta:** ~10

### T002 · ShellCheck SC2034 suppression
**File:** `scripts/utils.sh` (referenced in PLAN.md)
**Severity:** low · **Category:** debt · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:**
SC2034: Variable appears unused in script (shellcheck warning)
**Intent:** Suppress shellcheck warnings for variables used in sourced scripts
**Acceptance criteria:**
- [ ] Add # shellcheck disable=SC2034 to utils.sh
- [ ] Verify shellcheck passes with 0 warnings
**Implementation:**
Add at top of utils.sh: `# shellcheck disable=SC2034`
**Estimated LOC delta:** ~1

### T003 · Python type hints - download_uup.py
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** refactor · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:**
Technical debt: Python type hints missing
**Intent:** Add complete type annotations to download_uup.py
**Acceptance criteria:**
- [ ] Add type hints to all function signatures
- [ ] Add return types where applicable
- [ ] Run mypy --strict and resolve errors
- [ ] Maintain backwards CLI compatibility
**Implementation:**
Use `typing` module for complex types, add `# type: ignore` where needed for third-party libs
**Estimated LOC delta:** ~50

### T004 · Error handling standardization
**File:** Shell scripts (build.sh, debloat_wim.sh, custom_convert.sh)
**Severity:** high · **Category:** bug · **Size:** M
**Blocks:** T005  **Blocked by:** —
**Context:**
Technical debt: Error handling needs standardization
**Intent:** Ensure all shell scripts use consistent error handling
**Acceptance criteria:**
- [ ] All scripts use `set -euo pipefail`
- [ ] All functions return proper exit codes
- [ ] All error paths log meaningful messages
**Implementation:**
Audit scripts and add missing `set -euo pipefail`, add error handling wrappers
**Estimated LOC delta:** ~30

### T005 · Unified logging levels
**File:** `scripts/utils.sh`
**Severity:** medium · **Category:** refactor · **Size:** M
**Blocks:** —  **Blocked by:** T004
**Context:**
Technical debt: Logging levels need unification (DEBUG/INFO/WARN/ERROR)
**Intent:** Standardize logging across all shell scripts
**Acceptance criteria:**
- [ ] Implement log_debug, log_info, log_warn, log_error functions
- [ ] Add LOG_LEVEL env var for filtering
- [ ] Update all scripts to use consistent logging
**Implementation:**
In utils.sh: Add LOG_LEVEL support, implement DEBUG level filtering
**Estimated LOC delta:** ~40

### T006 · Test coverage 40%→80%
**File:** `tests/` directory
**Severity:** high · **Category:** debt · **Size:** L
**Blocks:** —  **Blocked by:** —
**Context:**
Technical debt: Test coverage needs improvement from 40% to 80%
**Intent:** Increase test coverage for main modules
**Acceptance criteria:**
- [ ] Add unit tests for download_uup.py API functions
- [ ] Add unit tests for utils.sh functions (mocked)
- [ ] Add integration tests for full download flow
- [ ] Run pytest with --cov and verify 80%+ coverage
**Implementation:**
Use pytest fixtures, unittest.mock for external calls, add parametrized tests
**Estimated LOC delta:** ~200

---

## Additional Roadmap Items (from TODO.md)

The following items are documented in TODO.md but lack specific TODO markers in code. They are high-level features not yet implemented:

| ID | Category | Item |
|----|----------|------|
| API-001 | api | UUP JSON API v2 client |
| API-002 | api | Delta downloads |
| API-003 | api | Resume interrupted downloads |
| BUILD-001 | build | Custom edition selection |
| BUILD-002 | build | Multi-edition ISO |
| DEBLOAT-001 | debloat | Smart dependency checker |
| PLAT-001 | platform | Docker build |
| PLAT-003 | platform | CI/CD integration |

---

## Metadata

- **Total markers found:** 1 TODO in source code
- **Technical debt items:** 6 (from PLAN.md debt section)
- **Roadmap features:** 50 (from TODO.md)
- **Estimated total LOC for this plan:** ~330