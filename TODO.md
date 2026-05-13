# Project TODO & Feature Roadmap
<metadata><version>4.0-cleaned</version><updated>2026-05-11T21:16:00Z</updated><items>42</items><categories>10</categories></metadata>
<removed>
- T001: Windows dependency install (outdated - winget now available)
- T002: ShellCheck SC2034 suppression (partially done - already in utils.sh)
- T036: Docker build (no Dockerfile exists)
- T037: Windows PowerShell script (no build.ps1 exists)
- T038: CI/CD integration (workflows already exist)
- T054-T056: Packer/Ansible/Chef (speculative, not aligned with project)
- Stale PR references and Win11Debloat mentions
</removed>

##  API & Download
<category name="api" items="5" priority="high">
- API-001: UUP JSON API v2 client - match api.uupdump.net schema
- API-002: Delta downloads - only changed packages between builds
- API-003: Resume interrupted downloads - aria2c state persistence
- API-004: Mirror sources - redundant download endpoints
- API-005: Build history cache - local cache with TTL refresh
</category>

##  Build System
<category name="build" items="8" priority="high">
- BUILD-001: Custom edition selection - any edition ID from metadata
- BUILD-002: Multi-edition ISO - single ISO, boot menu selection
- BUILD-003: Language packs - multi-language support
- BUILD-004: Driver injection - automated driver pack integration
- BUILD-005: Build profiles - minimal/standard/gaming/enterprise/dev
- BUILD-006: Component groups - toggle gaming/productivity/social/telemetry
- BUILD-007: Version pinning - lock specific builds
- BUILD-008: ISO signing - GPG + SHA256 checksums
</category>

##  Debloating
<category name="debloat" items="9" priority="medium">
- DEBLOAT-001: Smart dependency checker - detect dependency conflicts
- DEBLOAT-002: Telemetry scoring - rate reduction percentage
- DEBLOAT-003: Privacy dashboard - verify privacy settings
- DEBLOAT-004: Service hardening - disable unnecessary services
- DEBLOAT-005: Firewall optimization - pre-configured rules
- DEBLOAT-006: BitLocker options - encryption configuration
- DEBLOAT-007: Sandbox toggle - enable/disable Windows Sandbox
- DEBLOAT-008: WSL config - pre-configure Windows Subsystem for Linux
- DEBLOAT-009: Debloat pattern validator - validate patterns before applying
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
<debt><item sev="medium">Python type hints - download_uup.py</item><item sev="high">Error handling - standardize across shell scripts</item><item sev="medium">Logging - unify levels</item><item sev="high">Test coverage - 40%→80%</item></debt>

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
*Roadmap: 42 items | v4.0-cleaned*