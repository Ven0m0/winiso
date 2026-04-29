# Project TODO & Feature Roadmap

<metadata>
  <version>2.0-enhanced</version>
  <last-updated>2026-04-29T12:16:13Z</last-updated>
  <total-items>50</total-items>
  <categories>10</categories>
  <priority>strategic</priority>
</metadata>

<migration-log>
  <removed-items>
    <item>Pre-1.0.0 references (obsolete)</item>
    <item>Duplicate troubleshooting entries (moved to README)</item>
    <item>Outdated version requirements</item>
    <item>Completed feature requests (implemented in 1.x)</item>
  </removed-items>
  <consolidated-items>
    <item>Related features grouped by category</item>
    <item>Priorities assigned (impact vs effort)</item>
    <item>Dependencies mapped between items</item>
  </consolidated-items>
</migration-log>

## Quick Stats

<stats>
  <category name="API & Download" items="5" priority="high"/>
  <category name="Build System" items="8" priority="high"/>
  <category name="Debloating" items="8" priority="medium"/>
  <category name="Post-Install" items="4" priority="medium"/>
  <category name="Monitoring" items="4" priority="low"/>
  <category name="Platform" items="5" priority="high"/>
  <category name="Testing" items="5" priority="high"/>
  <category name="Architecture" items="5" priority="future"/>
  <category name="AI/ML" items="3" priority="experimental"/>
  <category name="Ecosystem" items="3" priority="medium"/>
</stats>

## 🎯 API & Download Enhancements

<feature-category name="api-download" priority="high">
  <item id="API-001" status="todo" effort="M" depends="none">
    <name>Implement UUP JSON API v2 client</name>
    <desc>Update download_uup.py to match latest api.uupdump.net schema (JSON API version updates quarterly)</desc>
    <acceptance>All API endpoints support v2 schema, rate limiting, retry logic</acceptance>
  </item>
  <item id="API-002" status="todo" effort="L" depends="API-001">
    <name>Add build delta/differential download</name>
    <desc>Only download changed packages between builds to save bandwidth</desc>
    <acceptance>50%+ bandwidth reduction on incremental updates</acceptance>
  </item>
  <item id="API-003" status="todo" effort="S" depends="none">
    <name>Resume interrupted downloads</name>
    <desc>aria2c supports this but needs proper state persistence across sessions</desc>
    <acceptance>Download resumes from last completed chunk after interruption</acceptance>
  </item>
  <item id="API-004" status="todo" effort="M" depends="API-003">
    <name>Mirror/redundant source support</name>
    <desc>Allow alternative download sources if uupdump.net is unavailable</desc>
    <acceptance>Configurable mirror list, automatic failover</acceptance>
  </item>
  <item id="API-005" status="todo" effort="S" depends="API-001">
    <name>Build history cache</name>
    <desc>Local cache of builds to avoid repeated API calls, with TTL refresh</desc>
    <acceptance>Build list cached 1 hour, respects Cache-Control headers</acceptance>
  </item>
</feature-category>

## 🔧 Build System & Configuration

<feature-category name="build-system" priority="high">
  <item id="BUILD-001" status="todo" effort="L" depends="none">
    <name>Custom edition selection</name>
    <desc>Allow building ANY edition from UUP metadata, not just Pro/Workstation (via CLI/env var)</desc>
    <acceptance>TARGET_EDITION accepts any valid edition ID, lists available if not found</acceptance>
  </item>
  <item id="BUILD-002" status="todo" effort="L" depends="BUILD-001">
    <name>Multi-edition ISO generation</name>
    <desc>Create single ISO with multiple Windows editions selectable at boot</desc>
    <acceptance>install.wim contains multiple indexes, boot menu shows edition selection</acceptance>
  </item>
  <item id="BUILD-003" status="todo" effort="M" depends="BUILD-001">
    <name>Language pack integration</name>
    <desc>Support adding multiple language packs during build</desc>
    <acceptance>--lang parameter accepts multiple languages, injects LPs</acceptance>
  </item>
  <item id="BUILD-004" status="todo" effort="M" depends="none">
    <name>Driver injection framework</name>
    <desc>Automated driver pack integration for common hardware (chipset, network, storage)</desc>
    <acceptance>Drivers directory scanned, matching INF files injected into WIM</acceptance>
  </item>
  <item id="BUILD-005" status="todo" effort="S" depends="none">
    <name>Build profile system</name>
    <desc>Preset configurations: "minimal", "standard", "gaming", "enterprise", "developer"</desc>
    <acceptance>make build-profile=minimal creates minimal install.wim</acceptance>
  </item>
  <item id="BUILD-006" status="todo" effort="S" depends="BUILD-005">
    <name>Component-based debloating</name>
    <desc>Toggle groups: "gaming", "productivity", "social", "telemetry", "accessibility" etc</desc>
    <acceptance>DEBLOAT_GROUPS="gaming,productivity" env var controls removal</acceptance>
  </item>
  <item id="BUILD-007" status="todo" effort="S" depends="none">
    <name>Version pinning</name>
    <desc>Lock specific Windows build versions for reproducible builds</desc>
    <acceptance>VERSION_PIN="22631.2428" env var restricts to exact build</acceptance>
  </item>
  <item id="BUILD-008" status="todo" effort="S" depends="none">
    <name>Signing & verification</name>
    <desc>Sign ISO with GPG, generate SHA256 checksums automatically</desc>
    <acceptance>Output includes .iso, .iso.sha256, .iso.sig files</acceptance>
  </item>
</feature-category>

## 🛠️ Advanced Debloating & Optimization

<feature-category name="debloating" priority="medium">
  <item id="DEBLOAT-001" status="todo" effort="M" depends="none">
    <name>Smart dependency checker</name>
    <desc>Detect when "safe to remove" apps are actually dependencies of kept apps</desc>
    <acceptance>Build fails with warning if dependency conflict detected</acceptance>
  </item>
  <item id="DEBLOAT-002" status="todo" effort="S" depends="none">
    <name>Telemetry scoring system</name>
    <desc>Rate debloating effectiveness ("This build blocks 95% of telemetry vectors")</desc>
    <acceptance>Post-build report shows telemetry reduction percentage</acceptance>
  </item>
  <item id="DEBLOAT-003" status="todo" effort="M" depends="DEBLOAT-002">
    <name>Privacy dashboard</name>
    <desc>Script to verify post-install privacy settings match intended configuration</desc>
    <acceptance>PowerShell script audits 20+ privacy settings, generates report</acceptance>
  </item>
  <item id="DEBLOAT-004" status="todo" effort="M" depends="none">
    <name>Service hardening</name>
    <desc>Disable unnecessary Windows services beyond current registry tweaks</desc>
    <acceptance>10+ additional services disabled, documented in README</acceptance>
  </item>
  <item id="DEBLOAT-005" status="todo" effort="S" depends="DEBLOAT-004">
    <name>Firewall rule optimization</name>
    <desc>Pre-configured inbound/outbound rules during build</desc>
    <acceptance>netsh commands in SetupComplete.cmd tighten firewall</acceptance>
  </item>
  <item id="DEBLOAT-006" status="todo" effort="S" depends="none">
    <name>BitLocker optimization</name>
    <desc>Configurable encryption settings for security-conscious deployments</desc>
    <acceptance>BitLocker enable/disable option, TPM-only vs TPM+PIN</acceptance>
  </item>
  <item id="DEBLOAT-007" status="todo" effort="S" depends="BUILD-005">
    <name>Windows Sandbox integration</name>
    <desc>Optional: enable/disable Windows Sandbox feature</desc>
    <acceptance>SANDBOX=1 env var preserves/removes Windows Sandbox</acceptance>
  </item>
  <item id="DEBLOAT-008" status="todo" effort="S" depends="BUILD-005">
    <name>WSL configuration</name>
    <desc>Optional: pre-configure Windows Subsystem for Linux during build</desc>
    <acceptance>WSL_ENABLED=1 installs WSL core, optional distro parameter</acceptance>
  </item>
</feature-category>

## 🌐 Post-Install Automation

<feature-category name="post-install" priority="medium">
  <item id="POST-001" status="todo" effort="M" depends="none">
    <name>First-run script framework</name>
    <desc>PowerShell/Bash scripts that run on first boot (beyond SetupComplete.cmd)</desc>
    <acceptance>FirstLogon.ps1 extended, runs user-defined scripts from config/</acceptance>
  </item>
  <item id="POST-002" status="todo" effort="S" depends="POST-001">
    <name>Chocolatey/Winget integration</name>
    <desc>Optional: package manager with pre-selected apps</desc>
    <acceptance>CHOCO_PACKAGES="vscode,git" installs via choco during first-run</acceptance>
  </item>
  <item id="POST-003" status="todo" effort="M" depends="POST-001">
    <name>Enterprise policy injection</name>
    <desc>Group Policy objects (GPO) for domain-joined machines</desc>
    <acceptance>GPO backup files in config/gpos/, imported during specialize</acceptance>
  </item>
  <item id="POST-004" status="todo" effort="S" depends="POST-001">
    <name>Configuration drift detection</name>
    <desc>Script to check if deployed systems match build configuration</desc>
    <acceptance>DriftCheck.ps1 compares deployed WIM against gold image</acceptance>
  </item>
</feature-category>

## 📊 Monitoring & Telemetry

<feature-category name="monitoring" priority="low">
  <item id="MON-001" status="todo" effort="M" depends="none">
    <name>Build telemetry dashboard</name>
    <desc>Track which builds succeed/fail, time-to-build statistics</desc>
    <acceptance>SQLite DB logs builds, simple dashboard shows trends</acceptance>
  </item>
  <item id="MON-002" status="todo" effort="S" depends="MON-001">
    <name>Update notification system</name>
    <desc>Alert when new Windows builds available matching configured preferences</desc>
    <acceptance>Email/Discord webhook on new matching build</acceptance>
  </item>
  <item id="MON-003" status="todo" effort="S" depends="none">
    <name>Health check script</name>
    <desc>Verify critical components post-install (defender, updates, store)</desc>
    <acceptance>Post-install verification reports status of key services</acceptance>
  </item>
  <item id="MON-004" status="todo" effort="S" depends="none">
    <name>Rollback mechanism</name>
    <desc>Save previous WIM before modifications for quick restore</desc>
    <acceptance>Previous install.wim saved as install.wim.backup</acceptance>
  </item>
</feature-category>

## 🖥️ Platform & Tooling

<feature-category name="platform" priority="high">
  <item id="PLAT-001" status="todo" effort="L" depends="none">
    <name>macOS build support</name>
    <desc>Test and document macOS compatibility (currently Linux-focused)</desc>
    <acceptance>setup_env_macos.sh, documented Homebrew installation path</acceptance>
  </item>
  <item id="PLAT-002" status="todo" effort="M" depends="none">
    <name>Windows native build mode</name>
    <desc>Run full build pipeline natively on Windows (WSL2 or direct)</desc>
    <acceptance>build.ps1 or build.bat works in PowerShell on Windows 10/11</acceptance>
  </item>
  <item id="PLAT-003" status="todo" effort="M" depends="none">
    <name>Docker build container</name>
    <desc>Consistent build environment via containerization</desc>
    <acceptance>docker build -t winiso . produces same output as host</acceptance>
  </item>
  <item id="PLAT-004" status="todo" effort="M" depends="none">
    <name>CI/CD integration</name>
    <desc>GitHub Actions for automated nightly builds</desc>
    <acceptance>Workflow triggers on schedule, tests build, uploads artifact</acceptance>
  </item>
  <item id="PLAT-005" status="todo" effort="L" depends="PLAT-004">
    <name>Web dashboard</name>
    <desc>Simple web UI to configure builds instead of CLI flags</desc>
    <acceptance>React/Vue app generates build configuration JSON</acceptance>
  </item>
</feature-category>

## 🔬 Testing & Quality

<feature-category name="testing" priority="high">
  <item id="TEST-001" status="todo" effort="M" depends="none">
    <name>ISO boot test automation</name>
    <desc>QEMU-based automated boot verification</desc>
    <acceptance>GitHub Action boots ISO in QEMU, verifies GRUB menu appears</acceptance>
  </item>
  <item id="TEST-002" status="todo" effort="M" depends="TEST-001">
    <name>Regression test suite</name>
    <desc>Ensure debloating doesn't break Windows Update or activation</desc>
    <acceptance>Automated test: Windows Update check passes, activation succeeds</acceptance>
  </item>
  <item id="TEST-003" status="todo" effort="S" depends="none">
    <name>Compatibility matrix</name>
    <desc>Document known working/non-working app/component combinations</desc>
    <acceptance>README section: "Known Issues", compatibility table</acceptance>
  </item>
  <item id="TEST-004" status="todo" effort="S" depends="none">
    <name>Performance benchmarking</name>
    <desc>Automated before/after performance measurements</desc>
    <acceptance>Boot time, disk space, RAM usage metrics compared</acceptance>
  </item>
  <item id="TEST-005" status="todo" effort="L" depends="none">
    <name>Fuzzing security tests</name>
    <desc>Verify debloat patterns don't create security gaps</desc>
    <acceptance>AFL++ fuzzing of debloat script with malformed inputs</acceptance>
  </item>
</feature-category>

## 🏗️ Architecture & Future

<feature-category name="architecture" priority="future">
  <item id="ARCH-001" status="todo" effort="L" depends="none">
    <name>Modular plugin system</name>
    <desc>Loadable debloat modules as separate scripts</desc>
    <acceptance>plugins/ directory, manifest.yaml format, dynamic loading</acceptance>
  </item>
  <item id="ARCH-002" status="todo" effort="L" depends="ARCH-001">
    <name>WIM layering system</name>
    <desc>Separate base system, updates, and customizations into layers</desc>
    <acceptance>Base.wim + Updates.wim + Custom.wim merged at build time</acceptance>
  </item>
  <item id="ARCH-003" status="todo" effort="M" depends="ARCH-002">
    <name>Differential WIM updates</name>
    <desc>Generate WIM deltas for incremental updates</desc>
    <acceptance>wimlib-imagex export with --delta produces delta WIM</acceptance>
  </item>
  <item id="ARCH-004" status="todo" effort="M" depends="none">
    <name>A/B partition with rollback</name>
    <desc>Dual-boot configuration with rollback capability</desc>
    <acceptance>Two system partitions, automatic rollback on boot failure</acceptance>
  </item>
  <item id="ARCH-005" status="todo" effort="M" depends="none">
    <name>Secure boot compatibility</name>
    <desc>Ensure ISO works with Secure Boot enabled</desc>
    <acceptance>All boot files signed, tested on UEFI with Secure Boot</acceptance>
  </item>
</feature-category>

## 🤖 AI/ML & Smart Features

<feature-category name="ai-ml" priority="experimental">
  <item id="AI-001" status="todo" effort="L" depends="none">
    <name>Smart debloat recommendations</name>
    <desc>ML model suggesting optimal debloat for use case</desc>
    <acceptance>Questionnaire-based recommendation engine</acceptance>
  </item>
  <item id="AI-002" status="todo" effort="S" depends="none">
    <name>Build failure prediction</name>
    <desc>Identify patterns in build failures</desc>
    <acceptance>Statistical analysis of past failures predicts risk</acceptance>
  </item>
  <item id="AI-003" status="todo" effort="S" depends="none">
    <name>Automated issue triage</name>
    <desc>Classify GitHub issues automatically</desc>
    <acceptance>Issue bot labels bugs, features, questions</acceptance>
  </item>
</feature-category>

## 🔗 Ecosystem Integration

<feature-category name="ecosystem" priority="medium">
  <item id="ECO-001" status="todo" effort="M" depends="none">
    <name>Packer plugin</name>
    <desc>HashiCorp Packer builder for automated Windows image builds</desc>
    <acceptance>packer validate passes, builds AMI/image on cloud</acceptance>
  </item>
  <item id="ECO-002" status="todo" effort="S" depends="none">
    <name>Ansible module</name>
    <desc>Deploy and configure using Ansible</desc>
    <acceptance>ansible-galaxy role available, idempotent</acceptance>
  </item>
  <item id="ECO-003" status="todo" effort="S" depends="none">
    <name>Puppet/Chef cookbooks</name>
    <desc>Configuration management integration</desc>
    <acceptance>Cookbook in Supermarket, tested on 3 platforms</acceptance>
  </item>
</feature-category>

## Technical Debt Register

<debt-register>
  <item sev="low" id="TD-001">
    <desc>ShellCheck SC2034 false positive suppression (1 instance in utils.sh)</desc>
    <fix>Add # shellcheck disable=SC2034 comment with justification</fix>
  </item>
  <item sev="medium" id="TD-002">
    <desc>Python type hints missing (download_uup.py, ~330 lines)</desc>
    <fix>Add typing import, annotate public functions and complex returns</fix>
  </item>
  <item sev="high" id="TD-003">
    <desc>Error handling inconsistent across scripts</desc>
    <fix>Standardize: set -euo pipefail, trap ERR, error_handler function</fix>
  </item>
  <item sev="medium" id="TD-004">
    <desc>Mixed logging styles (some scripts use echo, some log_* functions)</desc>
    <fix>Convert all to log_* functions from utils.sh</fix>
  </item>
  <item sev="high" id="TD-005">
    <desc>Unit test coverage insufficient (~40%, target 80%+)</desc>
    <fix>Priority: debloat_wim.sh, custom_convert.sh, download_uup.py</fix>
  </item>
</debt-register>

---

<metadata>
  <generated>2026-04-29T12:16:13Z</generated>
  <next-review>2026-05-06T12:16:13Z</next-review>
  <version>2.0-enhanced</version>
</metadata>