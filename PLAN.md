# Implementation Plan
_Generated: 2026-05-04T07:08:52Z · Updated: 2026-05-15_
_Last reviewed: 51 tasks → 54 tasks (3 new items added, baselines corrected)_

## Summary
Comprehensive implementation plan integrating technical debt from existing PLAN.md and 50 feature items from TODO.md. Categories: API/Download (6), Build System (9), Debloating (10), Post-Install (4), Monitoring (4), Platform (4), Testing (5), Architecture (5), AI/ML (3), Ecosystem (0), plus 4 technical debt items. Total effort: ~660h across 4 priority tiers.

**Stale items removed in prior updates:**
- T001: Windows dependency installation (outdated - winget now available)
- T002: ShellCheck SC2034 suppression (partially done - already in utils.sh)
- T036 (old): Docker build (no Dockerfile exists, not currently planned)
- T037 (old): Windows native PowerShell script (no build.ps1 exists)
- T038 (old): CI/CD integration (workflows already exist in .github/workflows/)
- T054-T056 (old): Ecosystem integrations (Packer, Ansible, Chef/Puppet - speculative)

**Updates in this review (2026-05-15):**
- T004: Shell scripts confirmed fully compliant (`set -euo pipefail` in all 5 scripts); criteria updated
- T005: Basic log levels (info/success/warn/error) already in utils.sh; remaining: DEBUG + LOG_LEVEL filtering
- T006: Corrected test coverage baseline from 40% to ~60% (actual measured state)
- Removed stale `implement Optimize-Windows` line from TODO.md; promoted to proper task T054
- Added T054: Optimize-Windows debloat patterns integration
- Added T055: Pre-build autounattend.xml validation
- Added T056: aria2c stderr capture for better download error messages

## Task Index (topological order)
| # | ID | Title | Sev | Cat | Size | Blocks |
|---|-----|-------|-----|-----|------|--------|
| 1 | T003 | Python type hints - download_uup.py | medium | refactor | M | — |
| 2 | T004 | Error handling standardization | high | bug | M | — |
| 3 | T005 | Unified logging levels | medium | refactor | M | T004 |
| 4 | T006 | Test coverage ~60%→80% | high | debt | L | — |
| 5 | T007 | UUP JSON API v2 client | high | feature | M | T003,T004 |
| 6 | T008 | Delta downloads | high | feature | L | T007 |
| 7 | T009 | Resume interrupted downloads | medium | feature | M | T007 |
| 8 | T010 | Mirror sources | medium | feature | M | T007 |
| 9 | T011 | Build history cache | medium | feature | S | T007 |
| 10 | T012 | Custom edition selection | high | feature | M | T004 |
| 11 | T013 | Multi-edition ISO | high | feature | L | T012 |
| 12 | T014 | Language packs support | medium | feature | M | T012 |
| 13 | T015 | Driver injection | medium | feature | M | T012 |
| 14 | T016 | Build profiles | medium | feature | S | — |
| 15 | T017 | Component groups | medium | feature | S | T016 |
| 16 | T018 | Version pinning | medium | feature | S | — |
| 17 | T019 | ISO signing | medium | feature | S | — |
| 18 | T020 | Debloat dependency checker | medium | feature | M | — |
| 19 | T021 | Telemetry scoring | medium | feature | S | — |
| 20 | T022 | Privacy dashboard | low | feature | M | T020 |
| 21 | T023 | Service hardening | medium | feature | M | — |
| 22 | T024 | Firewall optimization | medium | feature | S | — |
| 23 | T025 | BitLocker options | low | feature | S | — |
| 24 | T026 | Sandbox toggle | low | feature | S | — |
| 25 | T027 | WSL config | low | feature | S | — |
| 26 | T028 | First-run framework | medium | feature | M | — |
| 27 | T029 | Package managers integration | medium | feature | M | T028 |
| 28 | T030 | GPO injection | medium | feature | S | T028 |
| 29 | T031 | Drift detection | medium | feature | S | T028 |
| 30 | T032 | Build telemetry | low | feature | S | — |
| 31 | T033 | Update alerts | low | feature | S | — |
| 32 | T034 | Health checks | low | feature | S | — |
| 33 | T035 | Rollback mechanism | medium | feature | M | — |
| 34 | T036 | Test automation QEMU | medium | feature | M | — |
| 35 | T037 | ISO boot tests | high | feature | L | T036 |
| 36 | T038 | Regression suite | high | feature | L | T036 |
| 37 | T039 | Compatibility matrix | low | docs | S | — |
| 38 | T040 | Performance benchmarks | low | feature | S | — |
| 39 | T041 | Security fuzzing | medium | feature | M | — |
| 40 | T042 | Plugin system | high | refactor | L | T004,T006 |
| 41 | T043 | WIM layering | high | feature | L | — |
| 42 | T044 | Diff updates | medium | feature | M | T043 |
| 43 | T045 | A/B partitions | medium | feature | L | — |
| 44 | T046 | Secure boot | high | feature | M | — |
| 45 | T047 | Smart recommendations | low | ai | L | T020,T021 |
| 46 | T048 | Failure prediction | low | ai | S | — |
| 47 | T049 | Issue triage | low | ai | S | — |
| 48 | T050 | Debloat pattern validator | medium | feature | M | — |
| 49 | T051 | Build configuration presets | medium | feature | S | — |
| 50 | T052 | winget integration | medium | feature | M | — |
| 51 | T053 | Build artifact archive | medium | feature | M | — |
| 52 | T054 | Optimize-Windows patterns integration | medium | feature | M | — |
| 53 | T055 | Pre-build autounattend.xml validation | low | debt | S | — |
| 54 | T056 | aria2c stderr capture | low | debt | S | — |

## Tasks

### T003 · Python type hints - download_uup.py
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** refactor · **Size:** M
**Blocks:** T007,T008,T009,T010,T011  **Blocked by:** —
**Context:** Technical debt: Python type hints missing
**Intent:** Add complete type annotations to download_uup.py
**Acceptance criteria:**
- [ ] Add type hints to all function signatures
- [ ] Add return types where applicable
- [ ] Run mypy --strict and resolve errors
- [ ] Maintain backwards CLI compatibility
**Implementation:** Use `typing` module for complex types, add `# type: ignore` where needed for third-party libs

### T004 · Error handling standardization
**File:** Shell scripts (build.sh, debloat_wim.sh, custom_convert.sh)
**Severity:** high · **Category:** bug · **Size:** M
**Blocks:** T005,T012,T042  **Blocked by:** —
**Context:** Technical debt: Error handling needs standardization
**Intent:** Ensure all shell scripts use consistent error handling
**Acceptance criteria:**
- [x] All pipeline scripts use `set -euo pipefail` *(confirmed: build.sh:17, debloat_wim.sh:11, setup_env.sh:6, validate_prereqs.sh:6)*
- [ ] `scripts/custom_convert.sh` — upstream-derived, no `set -euo pipefail`; track separately if/when upstreamed
- [ ] All functions return proper exit codes
- [ ] All error paths log meaningful messages
- [ ] `download_uup.py` raises typed exceptions with context on all failure paths
**Implementation:** Pipeline shell work is largely done. Remaining: `custom_convert.sh` (upstream), Python exception context

### T005 · Unified logging levels
**File:** `scripts/utils.sh`
**Severity:** medium · **Category:** refactor · **Size:** M
**Blocks:** —  **Blocked by:** T004
**Context:** Technical debt: Logging levels need unification (DEBUG/INFO/WARN/ERROR)
**Intent:** Standardize logging across all shell scripts
**Acceptance criteria:**
- [x] `log_info`, `log_success`, `log_warn`, `log_error` implemented in utils.sh *(already present)*
- [ ] Add `log_debug` function with `LOG_LEVEL=debug` guard
- [ ] Add `LOG_LEVEL` env var support for runtime filtering (default: info)
- [ ] All scripts consistently use utils.sh log functions (no raw echo for status)
**Implementation:** In utils.sh: add `LOG_LEVEL` support and `log_debug` filtered by it; audit callers

### T006 · Test coverage ~60%→80%
**File:** `tests/` directory
**Severity:** high · **Category:** debt · **Size:** L
**Blocks:** T042  **Blocked by:** —
**Context:** Technical debt: Test coverage needs improvement from ~60% to 80% (baseline corrected from 40% — test_download_uup.py already has 40+ tests covering major paths)
**Intent:** Increase test coverage for main modules
**Acceptance criteria:**
- [x] Unit tests for download_uup.py API functions (fetch_url, get_latest_builds, get_build_info, select_editions, interactive_mode)
- [ ] Add tests for `_process_selected_build()`, `_prepare_output_directory()`, `_prepare_download_list()`, `_run_aria2_download()` happy paths
- [ ] Add unit tests for utils.sh functions (mocked via bats or pytest subprocess)
- [ ] Add integration tests for full download flow (mocked network)
- [ ] Run pytest with --cov and verify 80%+ coverage
**Implementation:** Expand the existing unittest/unittest.mock suite; focus on uncovered private helpers; use pytest --cov to track progress

### T007 · UUP JSON API v2 client
**File:** `scripts/download_uup.py`
**Severity:** high · **Category:** feature · **Size:** M
**Blocks:** T008,T009,T010,T011  **Blocked by:** T003,T004
**Context:** API-001: UUP JSON API v2 client - match api.uupdump.net schema
**Intent:** Implement API v2 client to match uupdump.net schema
**Acceptance criteria:**
- [ ] Map all api.uupdump.net v2 endpoints
- [ ] Handle pagination for large result sets
- [ ] Parse all build metadata (version, arch, lang, edition)
- [ ] Add comprehensive error handling for API errors
**Implementation:** Add `class UUPAPIv2` with methods: `get_builds()`, `get_build_info()`, `get_download_url()`

### T008 · Delta downloads
**File:** `scripts/download_uup.py`
**Severity:** high · **Category:** feature · **Size:** L
**Blocks:** —  **Blocked by:** T007
**Context:** API-002: Delta downloads - only changed packages between builds
**Intent:** Implement delta download to skip unchanged packages
**Acceptance criteria:**
- [ ] Compare local and remote package lists
- [ ] Calculate diff to determine needed packages
- [ ] Only download changed/new packages
- [ ] Maintain local package manifest for future comparisons
**Implementation:** Add `compute_delta(local_manifest, remote_manifest)` returning list of URLs to download

### T009 · Resume interrupted downloads
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T007
**Context:** API-003: Resume interrupted downloads - aria2c state persistence
**Intent:** Persist aria2c download state for resume capability
**Acceptance criteria:**
- [ ] Save aria2c session on interrupt (SIGINT/SIGTERM)
- [ ] Load saved session on restart
- [ ] Validate partial file integrity
- [ ] Clean up stale sessions older than 7 days
**Implementation:** Use `aria2c --save-session` and `--input-file` for resume

### T010 · Mirror sources
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T007
**Context:** API-004: Mirror sources - redundant download endpoints
**Intent:** Implement fallback to mirror sources on primary failure
**Acceptance criteria:**
- [ ] Maintain list of known mirrors
- [ ] Implement retry with exponential backoff
- [ ] Switch to mirror on primary failure
- [ ] Track mirror reliability for future requests
**Implementation:** Add `class MirrorManager` with `get_mirror()`, `report_failure()`

### T011 · Build history cache
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** T007
**Context:** API-005: Build history cache - local cache with TTL refresh
**Intent:** Cache build metadata to reduce API calls
**Acceptance criteria:**
- [ ] Store build metadata in SQLite/JSON cache
- [ ] Implement TTL (default 1 hour)
- [ ] Force refresh via --force flag
- [ ] Cache invalidation on API version change
**Implementation:** Add `class BuildCache` with `get()`, `set()`, `invalidate()`

### T012 · Custom edition selection
**File:** `scripts/build.sh`
**Severity:** high · **Category:** feature · **Size:** M
**Blocks:** T013,T014,T015  **Blocked by:** T004
**Context:** BUILD-001: Custom edition selection - any edition ID from metadata
**Intent:** Allow selection of any Windows edition from API metadata
**Acceptance criteria:**
- [ ] Parse edition list from UUP metadata
- [ ] Add --edition flag to select specific edition
- [ ] Validate edition exists before download
- [ ] Support edition ID (e.g., "Professional")
**Implementation:** Add `select_edition(edition_id, metadata)` returning validated edition

### T013 · Multi-edition ISO
**File:** `scripts/build.sh`
**Severity:** high · **Category:** feature · **Size:** L
**Blocks:** —  **Blocked by:** T012
**Context:** BUILD-002: Multi-edition ISO - single ISO, boot menu selection
**Intent:** Create single ISO with multiple editions selectable at boot
**Acceptance criteria:**
- [ ] Bundle multiple editions in single ISO
- [ ] Configure boot menu for edition selection
- [ ] Each edition has separate WIM
- [ ] Total ISO size optimized (shared packages)
**Implementation:** Use oscdimg with multiple WIMs, configure boot.wim menu

### T014 · Language packs support
**File:** `scripts/build.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T012
**Context:** BUILD-003: Language packs - multi-language support
**Intent:** Support building ISO with multiple language packs
**Acceptance criteria:**
- [ ] Accept comma-separated language list
- [ ] Download appropriate language packs
- [ ] Configure locale in autounattend.xml
- [ ] Support comma-separated language format like `en-US,zh-CN,de-DE`
**Implementation:** Add `--languages` flag, integrate with lp.cab downloads

### T015 · Driver injection
**File:** `scripts/build.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T012
**Context:** BUILD-004: Driver injection - automated driver pack integration
**Intent:** Inject third-party drivers into WIM
**Acceptance criteria:**
- [ ] Accept driver path via --drivers flag
- [ ] Use DISM /Add-Driver to inject
- [ ] Support .inf and .cab driver sources
- [ ] Recursive directory scan for drivers
**Implementation:** Add `inject_drivers(wim_path, driver_dir)` using DISM

### T016 · Build profiles
**File:** `scripts/build.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** T017  **Blocked by:** —
**Context:** BUILD-005: Build profiles - minimal/standard/gaming/enterprise/dev
**Intent:** Predefined configuration profiles
**Acceptance criteria:**
- [ ] Implement minimal/standard/gaming/enterprise/dev profiles
- [ ] Each profile defines debloat list, settings
- [ ] Add --profile flag
- [ ] Profile defines autounattend.xml modifications
**Implementation:** Add `PROFILES` dict in config/profiles.yaml

### T017 · Component groups
**File:** `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** T016
**Context:** BUILD-006: Component groups - toggle gaming/productivity/social/telemetry
**Intent:** Toggleable debloat component groups
**Acceptance criteria:**
- [ ] Define groups: gaming, productivity, social, telemetry
- [ ] Add --include-group/--exclude-group flags
- [ ] Groups map to debloat patterns
- [ ] Validate group names
**Implementation:** Add `COMPONENT_GROUPS` dict in config/groups.yaml

### T018 · Version pinning
**File:** `scripts/download_uup.py`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** BUILD-007: Version pinning - lock specific builds
**Intent:** Pin to specific build version for reproducibility
**Acceptance criteria:**
- [ ] Accept build number (e.g., 26100.1)
- [ ] Verify build exists before download
- [ ] Cache pinned version in config
- [ ] Warn when pinned build is obsolete
**Implementation:** Add `--pin-build` flag, store in .uup/config.json

### T019 · ISO signing
**File:** `scripts/build.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** BUILD-008: ISO signing - GPG + SHA256 checksums
**Intent:** Sign ISO with GPG and generate checksums
**Acceptance criteria:**
- [ ] Generate SHA256 checksum file
- [ ] GPG sign the ISO and checksum
- [ ] Publish public key with release
- [ ] Verify signature on download
**Implementation:** Add `sign_iso(iso_path, gpg_key)` using gpg and sha256sum

### T020 · Debloat dependency checker
**File:** `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** T022,T047  **Blocked by:** —
**Context:** DEBLOAT-001: Smart dependency checker - detect dependency conflicts
**Intent:** Detect when removing one app breaks another
**Acceptance criteria:**
- [ ] Parse AppX dependencies from Windows
- [ ] Warn before removing dependent apps
- [ ] Offer safe removal alternatives
- [ ] Log dependency graph
**Implementation:** Add `check_dependencies(appx_list)` using DISM /GetCapabilities

### T021 · Telemetry scoring
**File:** `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** T047  **Blocked by:** —
**Context:** DEBLOAT-002: Telemetry scoring - rate reduction percentage
**Intent:** Quantify privacy improvement from debloating
**Acceptance criteria:**
- [ ] Score before/after telemetry endpoints
- [ ] Report percentage reduction
- [ ] Categorize: network, registry, scheduled tasks
- [ ] Output machine-parseable JSON
**Implementation:** Add `score_telemetry(wim_path)` returning metrics dict

### T022 · Privacy dashboard
**File:** `scripts/debloat_wim.sh`
**Severity:** low · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T020
**Context:** DEBLOAT-003: Privacy dashboard - verify privacy settings
**Intent:** Generate report of privacy-related settings
**Acceptance criteria:**
- [ ] Scan registry for privacy settings
- [ ] Check firewall rules
- [ ] Verify services status
- [ ] Generate HTML/JSON report
**Implementation:** Add `audit_privacy(wim_path)` returning audit dict

### T023 · Service hardening
**File:** `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-004: Service hardening - disable unnecessary services
**Intent:** Disable non-essential Windows services
**Acceptance criteria:**
- [ ] Define service allowlist/blocklist
- [ ] Use reg add to disable services
- [ ] Support service groups (network, media, etc.)
- [ ] Backup original service config
**Implementation:** Add `harden_services(wim_path, config)` using reg load/hives

### T024 · Firewall optimization
**File:** `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-005: Firewall optimization - pre-configured rules
**Intent:** Pre-configure Windows Firewall rules
**Acceptance criteria:**
- [ ] Import pre-defined firewall rules
- [ ] Support rule profiles (strict, default)
- [ ] Block known telemetry IPs
- [ ] Export/import rule sets
**Implementation:** Add `apply_firewall_rules(wim_path, ruleset)` using netsh

### T025 · BitLocker options
**File:** `scripts/debloat_wim.sh`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-006: BitLocker options - encryption configuration
**Intent:** Configure BitLocker during Windows setup
**Acceptance criteria:**
- [ ] Add BitLocker config to autounattend.xml
- [ ] Support TPM, TPM+PIN, password modes
- [ ] Configure encryption strength
- [ ] Skip if not supported
**Implementation:** Add BitLocker settings in autounattend.xml DiskConfiguration

### T026 · Sandbox toggle
**File:** `scripts/debloat_wim.sh`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-007: Sandbox toggle - enable/disable Windows Sandbox
**Intent:** Control Windows Sandbox feature
**Acceptance criteria:**
- [ ] Add --sandbox enable/disable flag
- [ ] Use DISM to enable/disable
- [ ] Verify Windows version supports it
- [ ] Document requirements
**Implementation:** Add `configure_sandbox(wim_path, enabled)` using DISM

### T027 · WSL config
**File:** `scripts/debloat_wim.sh`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-008: WSL config - pre-configure Windows Subsystem for Linux
**Intent:** Pre-configure WSL during installation
**Acceptance criteria:**
- [ ] Install WSL feature
- [ ] Set default distro
- [ ] Configure wsl.conf
- [ ] Optionally download distros
**Implementation:** Add `configure_wsl(wim_path, config)` using reg add

### T028 · First-run framework
**File:** `scripts/setup_env.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** T029,T030,T031  **Blocked by:** —
**Context:** POST-001: First-run framework - scripts run on first boot
**Intent:** Execute scripts on first Windows boot
**Acceptance criteria:**
- [ ] Scripts placed in Windows\Setup\Scripts
- [ ] Support SetupComplete.cmd
- [ ] Support Passes in autounattend.xml
- [ ] Capture output logs
**Implementation:** Add `add_firstrun_script(script_path, wim_path)`

### T029 · Package managers integration
**File:** `scripts/setup_env.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T028
**Context:** POST-002: Package managers - choco/winget integration
**Intent:** Pre-install popular package managers
**Acceptance criteria:**
- [ ] Pre-install Chocolatey
- [ ] Pre-install winget (via App Installer)
- [ ] Pre-configure repos/sources
- [ ] Add to SetupComplete.cmd
**Implementation:** Add `install_package_managers(wim_path, config)`

### T030 · GPO injection
**File:** `scripts/setup_env.sh`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** T028
**Context:** POST-003: GPO injection - enterprise domain policies
**Intent:** Apply Group Policy settings
**Acceptance criteria:**
- [ ] Accept GPO XML/ADM/ADMX files
- [ ] Import into registry hives
- [ ] Support machine and user policies
- [ ] Validate GPO syntax
**Implementation:** Add `inject_gpo(gpo_files, wim_path)` using reg add

### T031 · Drift detection
**File:** `scripts/postinstall_drift.ps1`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** T028
**Context:** POST-004: Drift detection - config compliance checks
**Intent:** Detect configuration drift on the installed Windows system against a baseline
**Acceptance criteria:**
- [ ] Define baseline config JSON
- [ ] Collect current installed-system state and compare it to the baseline
- [ ] Report drift differences
- [ ] Optional auto-remediation
**Implementation:** Add a post-install `detect_drift(baseline, current)` flow in `scripts/postinstall_drift.ps1` that gathers current Windows configuration state and returns a drift report

### T032 · Build telemetry
**File:** `scripts/build.sh`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** MON-001: Build telemetry - success/failure tracking
**Intent:** Track build success/failure metrics
**Acceptance criteria:**
- [ ] Log build start/end timestamps
- [ ] Track success/failure per phase
- [ ] Optional: send to analytics endpoint
- [ ] Local JSON log file
**Implementation:** Add `log_telemetry(event, data)` using JSON logging

### T033 · Update alerts
**File:** `scripts/download_uup.py`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** MON-002: Update alerts - new build notifications
**Intent:** Notify when new Windows builds available
**Acceptance criteria:**
- [ ] Check for new builds periodically
- [ ] Support email/webhook notifications
- [ ] Configurable check frequency
- [ ] Suppress repeat notifications
**Implementation:** Add `check_updates(config)` returning new builds list

### T034 · Health checks
**File:** `scripts/build.sh`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** MON-003: Health checks - offline image/build verification with optional Windows post-install handoff
**Intent:** Verify build artifact health in the Linux pipeline and document optional Windows-only post-install checks separately
**Acceptance criteria:**
- [ ] Validate offline image/build artifacts from Linux (for example: required files present, image metadata readable, mount/export steps succeeded)
- [ ] Verify available host disk space and report image/output sizes relevant to the build
- [ ] Generate a health report that clearly distinguishes offline checks from Windows-only runtime checks
- [ ] If Windows post-install verification is desired, emit guidance or handoff data for `scripts/windows_service.cmd` instead of attempting SFC/DISM/Windows Update checks in `build.sh`
**Implementation:** Add `run_offline_health_checks(wim_path)` in `scripts/build.sh` returning an offline health report dict/summary; do not require SFC/DISM or Windows Update checks in the Linux build path

### T035 · Rollback mechanism
**File:** `scripts/build.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** MON-004: Rollback mechanism - WIM backup/restore
**Intent:** Backup and restore WIM states
**Acceptance criteria:**
- [ ] Create WIM backup before changes
- [ ] List available backups
- [ ] Restore from backup
- [ ] Auto-cleanup old backups
**Implementation:** Add `backup_wim()`, `restore_wim(backup_id)`, `list_backups()`

### T036 · Test automation QEMU
**File:** `tests/qemu_test.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** T037,T038  **Blocked by:** —
**Context:** PLAT-001: Test automation - QEMU boot verification
**Intent:** Automated ISO boot testing
**Acceptance criteria:**
- [ ] Boot ISO in QEMU
- [ ] Verify Windows setup starts
- [ ] Capture boot logs
- [ ] Cleanup after test
**Implementation:** Add `test_iso_boot(iso_path)` using qemu-system-x86_64

### T037 · ISO boot tests
**File:** `tests/boot_test.py`
**Severity:** high · **Category:** feature · **Size:** L
**Blocks:** —  **Blocked by:** T036
**Context:** TEST-001: ISO boot tests - QEMU automated verification
**Intent:** Automated boot verification
**Acceptance criteria:**
- [ ] Boot in QEMU with virtio
- [ ] Verify Windows PE loads
- [ ] Test basic setup screens
- [ ] Capture screenshot on failure
**Implementation:** Add pytest test class with QEMU fixtures

### T038 · Regression suite
**File:** `tests/regression.py`
**Severity:** high · **Category:** feature · **Size:** L
**Blocks:** —  **Blocked by:** T036
**Context:** TEST-002: Regression suite - Windows Update/activation
**Intent:** Test Windows Update and activation
**Acceptance criteria:**
- [ ] Test Windows Update connectivity
- [ ] Verify activation status
- [ ] Test after debloat changes
- [ ] Run in CI
**Implementation:** Add regression tests using Windows API calls

### T039 · Compatibility matrix
**File:** `docs/compatibility.md`
**Severity:** low · **Category:** docs · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** TEST-003: Compatibility matrix - known issues table
**Intent:** Document known hardware/software issues
**Acceptance criteria:**
- [ ] Table of known issues
- [ ] Hardware compatibility list
- [ ] Workarounds documented
- [ ] User-contributed entries
**Implementation:** Create docs/compatibility.md with Markdown table

### T040 · Performance benchmarks
**File:** `tests/benchmark.py`
**Severity:** low · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** TEST-004: Performance benchmarks - before/after metrics
**Intent:** Measure debloat performance impact
**Acceptance criteria:**
- [ ] Measure boot time
- [ ] Measure disk usage
- [ ] Measure memory usage
- [ ] Generate comparison report
**Implementation:** Add benchmark script with before/after measurements

### T041 · Security fuzzing
**File:** `tests/fuzz_debloat.py`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** TEST-005: Security fuzzing - debloat pattern validation
**Intent:** Validate debloat patterns don't break Windows
**Acceptance criteria:**
- [ ] Fuzz debloat pattern inputs
- [ ] Detect pattern errors
- [ ] Validate AppX removal safety
- [ ] Generate fuzz report
**Implementation:** Use python-afl or libfuzzer for pattern fuzzing

### T042 · Plugin system
**File:** `scripts/plugins/`
**Severity:** high · **Category:** refactor · **Size:** L
**Blocks:** —  **Blocked by:** T004,T006
**Context:** ARCH-001: Plugin system - loadable modules
**Intent:** Extensible plugin architecture
**Acceptance criteria:**
- [ ] Plugin interface defined
- [ ] Auto-discover plugins in directory
- [ ] Plugin config in YAML/JSON
- [ ] Hooks: pre_debloat, post_debloat, etc.
**Implementation:** Add `class Plugin` base, `PluginLoader` in scripts/plugin.py

### T043 · WIM layering
**File:** `scripts/wim_layer.py`
**Severity:** high · **Category:** feature · **Size:** L
**Blocks:** T044  **Blocked by:** —
**Context:** ARCH-002: WIM layering - base/updates/custom layers
**Intent:** Layered WIM approach for maintainability
**Acceptance criteria:**
- [ ] Base layer (Windows core)
- [ ] Updates layer (cumulative updates)
- [ ] Custom layer (debloat, settings)
- [ ] Merge layers on build
**Implementation:** Add `class WIMLayer` with `create()`, `merge()`, `extract()`

### T044 · Diff updates
**File:** `scripts/wim_diff.py`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T043
**Context:** ARCH-003: Diff updates - incremental WIM deltas
**Intent:** Only update changed WIM files
**Acceptance criteria:**
- [ ] Compare old vs new WIM
- [ ] Generate delta package
- [ ] Apply delta to existing WIM
- [ ] Validate integrity
**Implementation:** Add `generate_delta(old_wim, new_wim)` returning delta.cab

### T045 · A/B partitions
**File:** `scripts/ab_partition.py`
**Severity:** medium · **Category:** feature · **Size:** L
**Blocks:** —  **Blocked by:** —
**Context:** ARCH-004: A/B partitions - dual-boot rollback
**Intent:** Dual partition setup for rollback
**Acceptance criteria:**
- [ ] Create A/B partitions
- [ ] Install to inactive partition
- [ ] Rollback to last working state
- [ ] Switch partitions on failure
**Implementation:** Add `class ABPartition` with `install()`, `rollback()`, `switch()`

### T046 · Secure boot
**File:** `scripts/secure_boot.py`
**Severity:** high · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** ARCH-005: Secure boot - signed boot files
**Intent:** Support secure boot with signed binaries
**Acceptance criteria:**
- [ ] Sign boot files with test certificate
- [ ] Enroll test certificate in UEFI
- [ ] Verify secure boot status
- [ ] Document production signing
**Implementation:** Add `sign_boot_files(iso_path, cert)` using signtool

### T047 · Smart recommendations
**File:** `scripts/ai/recommend.py`
**Severity:** low · **Category:** ai · **Size:** L
**Blocks:** —  **Blocked by:** T020,T021
**Context:** AI-001: Smart recommendations - ML debloat advisor
**Intent:** ML-based debloat recommendations
**Acceptance criteria:**
- [ ] Train model on user preferences
- [ ] Recommend apps to remove
- [ ] Explain recommendation rationale
- [ ] Learn from user feedback
**Implementation:** Add `class RecommendationEngine` using sklearn/tensorflow

### T048 · Failure prediction
**File:** `scripts/ai/predict.py`
**Severity:** low · **Category:** ai · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** AI-002: Failure prediction - build risk analysis
**Intent:** Predict build failures before they occur
**Acceptance criteria:**
- [ ] Analyze past build logs
- [ ] Predict failure probability
- [ ] Suggest mitigation steps
- [ ] Confidence score
**Implementation:** Add `predict_failure(build_config)` returning risk score

### T049 · Issue triage
**File:** `scripts/ai/triage.py`
**Severity:** low · **Category:** ai · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** AI-003: Issue triage - automated classification
**Intent:** Auto-classify GitHub issues
**Acceptance criteria:**
- [ ] Parse issue description
- [ ] Classify: bug/feature/debt/docs
- [ ] Assign priority
- [ ] Suggest labels
**Implementation:** Add `class IssueClassifier` using NLP classification

### T050 · Debloat pattern validator
**File:** `scripts/validate_debloat.py`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** DEBLOAT-VALIDATOR: Validate debloat patterns before applying
**Intent:** Ensure debloat patterns are valid and safe before applying to WIM
**Acceptance criteria:**
- [ ] Validate glob patterns are well-formed
- [ ] Check for typos in pattern names (fuzzy match)
- [ ] Verify patterns don't match protected AppX
- [ ] Generate validation report
**Implementation:** Add `validate_debloat_patterns(config/debloat_list.txt)` returning validation report

### T051 · Build configuration presets
**File:** `config/profiles.yaml`
**Severity:** medium · **Category:** feature · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** BUILD-PRESETS: Predefined build configurations
**Intent:** Provide ready-to-use configuration profiles for common use cases
**Acceptance criteria:**
- [ ] Define minimal/standard/gaming/privacy/enterprise presets
- [ ] Each preset includes debloat list, settings, autounattend.xml overrides
- [ ] Add --preset flag to build.sh
- [ ] Document preset options in README
**Implementation:** Create config/profiles.yaml with preset definitions

### T052 · winget integration
**File:** `scripts/postinstall_winget.ps1`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T029
**Context:** POST-WINGET: Windows Package Manager integration
**Intent:** Pre-install and configure winget during Windows setup
**Acceptance criteria:**
- [ ] Install App Installer (winget prerequisite)
- [ ] Pre-configure winget sources
- [ ] Support winget install commands in first-run
- [ ] Document winget integration usage
**Implementation:** Add winget installation to setup_env.sh and first-run framework

### T053 · Build artifact archive
**File:** `scripts/archive_builds.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** —
**Context:** ARCHIVE: Archive old build artifacts
**Intent:** Automatically archive and manage old build artifacts to save disk space
**Acceptance criteria:**
- [ ] Archive completed builds to specified location
- [ ] Maintain metadata (build version, date, debloat settings)
- [ ] Support retention policies (keep last N, keep last N days)
- [ ] Provide list/cleanup commands
**Implementation:** Add `archive_build()` and `manage_archives()` functions

### T054 · Optimize-Windows debloat patterns integration
**File:** `config/debloat_list.txt`, `scripts/debloat_wim.sh`
**Severity:** medium · **Category:** feature · **Size:** M
**Blocks:** —  **Blocked by:** T020
**Context:** TODO.md referenced https://github.com/ShivamXD6/Optimize-Windows as a source of additional debloat patterns and registry tweaks; promoted from informal note to tracked task
**Intent:** Review and selectively merge high-quality debloat patterns and registry hardening entries from the Optimize-Windows project into the debloat pipeline
**Acceptance criteria:**
- [ ] Audit Optimize-Windows pattern list against current `config/debloat_list.txt`
- [ ] Add net-new patterns that do not conflict with AppX keep-list invariants
- [ ] Import validated registry tweaks into `scripts/debloat_wim.sh`
- [ ] Ensure no patterns match protected AppX (`*Store* *WebView* *VCLibs* *UI.Xaml* *Defender* *DesktopAppInstaller*`)
- [ ] Document source attribution in `debloat_list.txt`
**Implementation:** Manual review of upstream patterns; add only patterns that pass T050 (debloat pattern validator); group under `# Optimize-Windows` comment in debloat_list.txt

### T055 · Pre-build autounattend.xml validation
**File:** `scripts/build.sh`, `Makefile`
**Severity:** low · **Category:** debt · **Size:** S
**Blocks:** —  **Blocked by:** —
**Context:** `autounattend.xml` is currently validated only in CI (lint-and-format.yml via xmllint). A malformed XML discovered late in a 15-30 min build wastes significant time
**Intent:** Validate `config/autounattend.xml` with xmllint at build start before any download or WIM work
**Acceptance criteria:**
- [ ] Call `xmllint --noout config/autounattend.xml` in `validate_prereqs.sh` (or build.sh pre-flight block)
- [ ] Fail fast with a clear error message if validation fails
- [ ] Add `make validate-xml` target to Makefile and document in `help`
**Implementation:** One-liner addition to `validate_prereqs.sh`; add Makefile target; no new dependencies (xmllint already in CI)

### T056 · aria2c stderr capture for download error messages
**File:** `scripts/download_uup.py`
**Severity:** low · **Category:** debt · **Size:** S
**Blocks:** —  **Blocked by:** T007
**Context:** `subprocess.run(cmd, check=True)` in `_run_aria2_download()` only surfaces the exit code on failure; actual aria2c error text is lost, making failed downloads hard to diagnose
**Intent:** Capture and surface aria2c stderr/stdout on failure so users see the actual error (e.g. "404 Not Found", "disk full", "connection refused")
**Acceptance criteria:**
- [ ] Capture stderr (and optionally stdout) from aria2c subprocess
- [ ] On non-zero exit, log the last N lines of aria2c output via `log_error`
- [ ] On success, suppress verbose aria2c output unless `--verbose` flag is set
- [ ] Add a test for the failure-path error message
**Implementation:** Change `subprocess.run(cmd, check=True)` to capture output; wrap in try/except `subprocess.CalledProcessError`; log `e.stderr`

---

## Priority Tiers

### Priority 1: Immediate (0-30d) | ~80h
- T003: Python type hints
- T004: Error handling standardization
- T005: Unified logging levels
- T006: Test coverage ~60%→80%

### Priority 2: High-Impact (30-90d) | ~200h
- T007-T011: API features
- T012-T015: Edition selection
- T016-T019: Build system

### Priority 3: Platform (90-180d) | ~150h
- T020-T027: Debloating enhancements
- T028-T031: Post-install
- T032-T035: Monitoring
- T036-T041: Testing

### Priority 4: Future (180+d) | ~230h
- T042-T046: Architecture
- T047-T049: AI/ML
- T050-T053: New features (debloat validator, presets, winget, archive)
- T054: Optimize-Windows patterns integration
- T055: Pre-build XML validation *(quick win, consider pulling to Priority 1)*
- T056: aria2c stderr capture *(quick win, consider pulling to Priority 1)*

---

## Quality Gates
<quality>
<gate name="ShellCheck" threshold="0" status="passing"/>
<gate name="TypeCoverage" threshold="80%" status="pending"/>
<gate name="UnitTests" threshold="80%" status="needs-work"/>
<gate name="BuildTime" threshold="10min" baseline="15-30min" status="baseline"/>
</quality>

---

*Updated: 2026-05-15*
*Stale items removed (prior): T001, T002, T036 (old), T037 (old), T038 (old), T054-T056 (old ecosystem)*
*New items added (prior): T050, T051, T052, T053*
*Updated (2026-05-15): T004 shell criteria marked done; T005 basic levels marked done; T006 baseline corrected to ~60%; added T054, T055, T056*
