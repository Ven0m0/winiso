# Project TODO & Feature Roadmap
<metadata><version>5.0</version><updated>2026-05-15T00:00:00Z</updated><items>45</items><categories>10</categories></metadata>
<removed>
- T001: Windows dependency install (outdated - winget now available)
- T002: ShellCheck SC2034 suppression (partially done - already in utils.sh)
- T036: Docker build (no Dockerfile exists)
- T037: Windows PowerShell script (no build.ps1 exists)
- T038: CI/CD integration (workflows already exist)
- T054-T056 (old): Packer/Ansible/Chef (speculative, not aligned with project)
- Stale PR references and Win11Debloat mentions
- "implement https://github.com/ShivamXD6/Optimize-Windows" (informal note → promoted to DEBLOAT-010/T054)
</removed>
<done>
- T004 shell criteria: all 5 scripts confirmed using set -euo pipefail (build.sh, debloat_wim.sh, setup_env.sh, validate_prereqs.sh, custom_convert.sh)
- T005 basic levels: log_info, log_success, log_warn, log_error already in utils.sh
</done>

##  API & Download
<category name="api" items="6" priority="high">
- API-001: UUP JSON API v2 client - match api.uupdump.net schema
- API-002: Delta downloads - only changed packages between builds
- API-003: Resume interrupted downloads - aria2c state persistence
- API-004: Mirror sources - redundant download endpoints
- API-005: Build history cache - local cache with TTL refresh
- API-006: aria2c stderr capture - surface actual download errors on failure
</category>

##  Build System
<category name="build" items="9" priority="high">
- BUILD-001: Custom edition selection - any edition ID from metadata
- BUILD-002: Multi-edition ISO - single ISO, boot menu selection
- BUILD-003: Language packs - multi-language support
- BUILD-004: Driver injection - automated driver pack integration
- BUILD-005: Build profiles - minimal/standard/gaming/enterprise/dev
- BUILD-006: Component groups - toggle gaming/productivity/social/telemetry
- BUILD-007: Version pinning - lock specific builds
- BUILD-008: ISO signing - GPG + SHA256 checksums
- BUILD-009: Pre-build autounattend.xml validation - fail-fast xmllint check before download starts
</category>

##  Debloating
<category name="debloat" items="10" priority="medium">
- DEBLOAT-001: Smart dependency checker - detect dependency conflicts
- DEBLOAT-002: Telemetry scoring - rate reduction percentage
- DEBLOAT-003: Privacy dashboard - verify privacy settings
- DEBLOAT-004: Service hardening - disable unnecessary services
- DEBLOAT-005: Firewall optimization - pre-configured rules
- DEBLOAT-006: BitLocker options - encryption configuration
- DEBLOAT-007: Sandbox toggle - enable/disable Windows Sandbox
- DEBLOAT-008: WSL config - pre-configure Windows Subsystem for Linux
- DEBLOAT-009: Debloat pattern validator - validate patterns before applying
- DEBLOAT-010: Optimize-Windows patterns integration - selective merge of patterns from ShivamXD6/Optimize-Windows; blocked by DEBLOAT-009
</category>

##  Post-Install
<category name="postinstall" items="4" priority="medium">
- POST-001: First-run framework - scripts run on first boot
- POST-002: Package managers - choco/winget integration
- POST-003: GPO injection - enterprise domain policies
- POST-004: Drift detection - config compliance checks
</category>

##  Monitoring
<category name="monitoring" items="4" priority="low">
- MON-001: Build telemetry - success/failure tracking
- MON-002: Update alerts - new build notifications
- MON-003: Health checks - post-install verification
- MON-004: Rollback mechanism - WIM backup/restore
</category>

##  Platform
<category name="platform" items="4" priority="high">
- PLAT-001: Test automation - QEMU boot verification
- PLAT-002: Web dashboard - UI for config
- PLAT-003: Build artifact archive - manage old builds
- PLAT-004: Build configuration presets - predefined configs
</category>

##  Testing
<category name="testing" items="5" priority="high">
- TEST-001: ISO boot tests - QEMU automated verification
- TEST-002: Regression suite - Windows Update/activation
- TEST-003: Compatibility matrix - known issues table
- TEST-004: Performance benchmarks - before/after metrics
- TEST-005: Security fuzzing - debloat pattern validation
</category>

##  Architecture
<category name="architecture" items="5" priority="future">
- ARCH-001: Plugin system - loadable modules
- ARCH-002: WIM layering - base/updates/custom layers
- ARCH-003: Diff updates - incremental WIM deltas
- ARCH-004: A/B partitions - dual-boot rollback
- ARCH-005: Secure boot - signed boot files
</category>

##  AI/ML
<category name="ai" items="3" priority="experimental">
- AI-001: Smart recommendations - ML debloat advisor
- AI-002: Failure prediction - build risk analysis
- AI-003: Issue triage - automated classification
</category>

##  Ecosystem
<category name="ecosystem" items="0" priority="medium">
<removed>
- ECO-001: Packer plugin (speculative, not aligned with project direction)
- ECO-002: Ansible module (speculative)
- ECO-003: Chef/Puppet cookbooks (speculative)
</removed>
</category>

## Technical Debt
<debt>
  <item sev="medium">Python type hints - download_uup.py (only 1 of 24+ functions annotated)</item>
  <item sev="high" progress="shell-done">Error handling - shell scripts complete (set -euo pipefail confirmed); Python exception context remaining</item>
  <item sev="medium" progress="partial">Logging - info/success/warn/error done in utils.sh; DEBUG level + LOG_LEVEL env var remaining</item>
  <item sev="high" progress="partial">Test coverage - baseline ~60% (not 40%); target 80%; missing: private helpers, shell script tests</item>
</debt>

## Implementation Notes

### Priority 1 (0-30 days): Foundation
Focus on technical debt and API improvements:
- Python type hints for download_uup.py
- Error handling standardization (set -euo pipefail everywhere)
- Unified logging levels
- Test coverage improvement to 80%

### Priority 2 (30-90 days): Core Features
API and build system enhancements:
- UUP JSON API v2 client
- Delta downloads and resume capability
- Custom edition selection
- Build profiles and component groups

### Priority 3 (90-180 days): Extensions
Debloating, post-install, and testing:
- Debloat dependency checker
- Telemetry scoring
- First-run framework
- QEMU-based ISO testing

### Priority 4 (180+ days): Future
Architecture and AI/ML:
- Plugin system
- WIM layering
- Smart recommendations
- Failure prediction

---
*Roadmap: 45 items | v5.0 | Updated: 2026-05-15*
