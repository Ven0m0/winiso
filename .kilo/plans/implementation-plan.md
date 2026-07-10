# Implementation Plan

_Generated: 2026-07-10 · Updated: 2026-07-10_

## Summary

55 tasks across 9 categories, organized into 4 priority tiers. Technical debt items (T003-T006) are Priority 1, API/build features are Priority 2, debloat/post-install/testing are Priority 3, architecture/AI are Priority 4.

## Task Index (topological order)

| # | ID | Title | Category | Size | Blocks | Status |
|---|-----|-------|----------|------|--------|--------|
| 1 | T003 | Python type hints - download_uup.py | refactor | M | — | pending |
| 2 | T004 | Error handling standardization | bug | M | T005,T012 | done |
| 3 | T005 | Unified logging levels (DEBUG + LOG_LEVEL) | refactor | M | — | partial |
| 4 | T006 | Test coverage ~60%→80% | debt | L | T042 | in-progress |
| 5 | T007 | UUP JSON API v2 client | api | M | T008,T009,T010,T011 | pending |
| 6 | T008 | Delta downloads | api | L | — | pending |
| 7 | T009 | Resume interrupted downloads | api | M | — | pending |
| 8 | T010 | Mirror sources | api | M | — | pending |
| 9 | T011 | Build history cache | api | S | — | pending |
| 10 | T012 | Custom edition selection | build | M | T013,T014,T015 | pending |
| 11 | T013 | Multi-edition ISO | build | L | — | pending |
| 12 | T014 | Language packs support | build | M | — | pending |
| 13 | T015 | Driver injection | build | M | — | pending |
| 14 | T016 | Build profiles | build | S | T017 | pending |
| 15 | T017 | Component groups | build | S | — | pending |
| 16 | T018 | Version pinning | build | S | — | pending |
| 17 | T019 | ISO signing (GPG + SHA256) | build | S | — | pending |
| 18 | T020 | Debloat dependency checker | debloat | M | T022,T047,T054 | pending |
| 19 | T021 | Telemetry scoring | debloat | S | T047 | pending |
| 20 | T022 | Privacy dashboard | debloat | M | — | pending |
| 21 | T023 | Service hardening | debloat | M | — | pending |
| 22 | T024 | Firewall optimization | debloat | S | — | pending |
| 23 | T025 | BitLocker options | debloat | S | — | pending |
| 24 | T026 | Sandbox toggle | debloat | S | — | pending |
| 25 | T027 | WSL config | debloat | S | — | pending |
| 26 | T028 | First-run framework | postinstall | M | T029,T030,T031 | pending |
| 27 | T029 | Package managers integration | postinstall | M | T052 | pending |
| 28 | T030 | GPO injection | postinstall | S | — | pending |
| 29 | T031 | Drift detection | postinstall | S | — | pending |
| 30 | T032 | Build telemetry | monitoring | S | — | pending |
| 31 | T033 | Update alerts | monitoring | S | — | pending |
| 32 | T034 | Health checks | monitoring | S | — | pending |
| 33 | T035 | Rollback mechanism | monitoring | M | — | pending |
| 34 | T036 | Test automation QEMU | platform | M | T037,T038 | pending |
| 35 | T037 | ISO boot tests | testing | L | — | pending |
| 36 | T038 | Regression suite | testing | L | — | pending |
| 37 | T039 | Compatibility matrix | testing | S | — | pending |
| 38 | T040 | Performance benchmarks | testing | S | — | pending |
| 39 | T041 | Security fuzzing | testing | M | — | pending |
| 40 | T042 | Plugin system | architecture | L | — | pending |
| 41 | T043 | WIM layering | architecture | L | T044 | pending |
| 42 | T044 | Diff updates | architecture | M | — | pending |
| 43 | T045 | A/B partitions | architecture | L | — | pending |
| 44 | T046 | Secure boot | architecture | M | — | pending |
| 45 | T047 | Smart recommendations (ML) | ai | L | — | pending |
| 46 | T048 | Failure prediction (ML) | ai | S | — | pending |
| 47 | T049 | Issue triage (ML) | ai | S | — | pending |
| 48 | T050 | Debloat pattern validator | debloat | M | — | pending |
| 49 | T051 | Build configuration presets | build | S | — | pending |
| 50 | T052 | winget integration | postinstall | M | — | pending |
| 51 | T053 | Build artifact archive | platform | M | — | pending |
| 52 | T054 | Optimize-Windows patterns integration | debloat | M | — | pending |
| 53 | T055 | Pre-build autounattend.xml validation | build | S | — | pending |
| 54 | T056 | aria2c stderr capture | api | S | — | pending |
| 55 | T057 | zISOTweaker features integration | build | M | — | pending |

## Tasks

### Priority 1: Foundation (0-30d)

**T003 · Python type hints**  
File: `scripts/download_uup.py`  
Intent: Add complete type annotations. Acceptance: All functions typed, mypy --strict passing, CLI compatibility maintained.

**T004 · Error handling standardization**  
File: Shell scripts  
Status: DONE. Confirmed in build.sh, debloat_wim.sh, setup_env.sh, validate_prereqs.sh. Remaining: Python exception context.

**T005 · Unified logging levels**  
File: `scripts/utils.sh`  
Status: PARTIAL. Basic log_info/success/warn/error done. Remaining: log_debug with LOG_LEVEL env var.

**T006 · Test coverage ~60%→80%**  
File: `tests/`  
Status: IN-PROGRESS. Need coverage for: `_process_selected_build`, `_prepare_output_directory`, `_prepare_download_list`, `_run_aria2_download` happy paths.

**T055 · Pre-build autounattend.xml validation** (quick win)  
File: `scripts/validate_prereqs.sh`, `Makefile`  
Intent: xmllint --noout before build starts. Acceptance: Fail fast with clear error, `make validate-xml` target added.

**T056 · aria2c stderr capture** (quick win)  
File: `scripts/download_uup.py`  
Intent: Capture subprocess stderr/stdout on failure. Acceptance: Log actual error text, suppress verbose output unless --verbose.

### Priority 2: API & Build (30-90d)

**T007 · UUP JSON API v2 client**  
File: `scripts/download_uup.py`  
Intent: Match api.uupdump.net schema. Acceptance: Map all endpoints, handle pagination, parse build metadata.

**T008 · Delta downloads**  
Intent: Only download changed packages between builds.

**T009 · Resume interrupted downloads**  
Intent: aria2c state persistence for download resume.

**T010 · Mirror sources**  
Intent: Redundant download endpoints with fallback.

**T011 · Build history cache**  
Intent: Cache build metadata with TTL.

**T012 · Custom edition selection**  
Intent: Any edition ID from metadata via --edition flag.

**T013 · Multi-edition ISO**  
Intent: Single ISO with boot menu selection.

**T014 · Language packs support**  
Intent: Multi-language ISO support.

**T015 · Driver injection**  
Intent: Automated driver pack integration.

**T016 · Build profiles**  
Intent: minimal/standard/gaming/enterprise/dev predefined configs.

**T017 · Component groups**  
Intent: Toggleable gaming/productivity/social/telemetry groups.

**T018 · Version pinning**  
Intent: Lock specific builds for reproducibility.

**T019 · ISO signing**  
Intent: GPG + SHA256 checksums.

**T051 · Build configuration presets**  
Intent: Ready-to-use configurations via --preset flag.

**T057 · zISOTweaker features integration**  
Intent: Merge features from https://github.com/zoicware/zISOTweaker.

### Priority 3: Debloat & Post-Install (90-180d)

**T020 · Debloat dependency checker**  
Intent: Detect dependency conflicts before removal.

**T021 · Telemetry scoring**  
Intent: Quantify privacy improvement percentage.

**T022 · Privacy dashboard**  
Intent: Verify privacy settings, generate report.

**T023 · Service hardening**  
Intent: Disable non-essential Windows services.

**T024 · Firewall optimization**  
Intent: Pre-configured firewall rules, block telemetry IPs.

**T025 · BitLocker options**  
Intent: Encryption configuration in autounattend.xml.

**T026 · Sandbox toggle**  
Intent: Enable/disable Windows Sandbox.

**T027 · WSL config**  
Intent: Pre-configure Windows Subsystem for Linux.

**T028 · First-run framework**  
Intent: Scripts on first Windows boot.

**T029 · Package managers integration**  
Intent: Chocolatey and winget pre-installation.

**T030 · GPO injection**  
Intent: Enterprise domain policies.

**T031 · Drift detection**  
Intent: Config compliance checks.

**T032-T035 · Monitoring features**  
Build telemetry, update alerts, health checks, rollback.

**T036-T041 · Testing**  
QEMU boot verification, regression suite, compatibility matrix, benchmarks, security fuzzing.

### Priority 4: Architecture & AI (180+d)

**T042 · Plugin system**  
Intent: Loadable modules with hooks (pre_debloat, post_debloat).

**T043 · WIM layering**  
Intent: Base/updates/custom layer separation.

**T044 · Diff updates**  
Intent: Incremental WIM deltas.

**T045 · A/B partitions**  
Intent: Dual-boot rollback support.

**T046 · Secure boot**  
Intent: Signed boot files.

**T047 · Smart recommendations**  
Intent: ML debloat advisor.

**T048 · Failure prediction**  
Intent: Build risk analysis.

**T049 · Issue triage**  
Intent: Automated classification.

**T050 · Debloat pattern validator**  
Intent: Validate patterns before applying, check for protected AppX conflicts.

**T052 · winget integration**  
Intent: Pre-install App Installer with winget.

**T053/T054 · Archive & Optimize-Windows**  
Archive builds, merge patterns from ShivamXD6/Optimize-Windows.

## Quality Gates

| Gate | Threshold | Status |
|------|-----------|--------|
| ShellCheck | 0 warnings | passing |
| TypeCoverage | 80% | pending |
| UnitTests | 80% | in-progress (60%) |
| BuildTime | <10min | baseline (15-30min) |

---

*Updated: 2026-07-10*