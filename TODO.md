# Project TODO
_Updated: 2026-08-17_

Feature roadmap lives in `PLAN.md` (Next / Someday-maybe) — do not
duplicate items here. This file keeps only unevaluated external references.

## External inspiration (evaluated)

The four repos previously listed here were evaluated for merge. Verdict below;
no unevaluated references remain.

**Taken:** `ventoy/answer/autounattend.xml` is already generated from the same
schneegans unattend-generator that `deffz-finesse/windows-unattended-debloat`
and (via `memstechtips/UnattendedWinstall`) `ShivamXD6/Optimize-Windows` are
built on, so most of their tweaks (WPBT, LongPaths, `PreventDeviceEncryption`,
device-metadata blocking, HVCI off, SmartScreen off, `icacls` root hardening,
Recall/IE/WordPad/StepsRecorder removal) were already present. What was
genuinely new got merged: the `*549981C3F5F10*` glob (Cortana's real package
family — `*Cortana*` alone never matched it), plus OOBE-timing and first-boot
registry tweaks (`EnableFirstLogonAnimation`, `ScoobeSystemSettingEnabled`,
`DisableCoInstallers`, `SearchOrderConfig`, `GameDVR_Enabled`, `LaunchTo`,
`BingSearchEnabled`, `DeferFeatureUpdates`, Remote Assistance off, CEIP off).
See `CHANGELOG.md` [Unreleased] for the full list.

**Rejected:**
- deffz-finesse's first-logon installer suite (Firefox/VLC/VeraCrypt/KeePassXC/
  PowerToys/PS7, SHA-256 + Authenticode verified). Network-dependent, unpinned
  upstream versions, breaks offline-reproducible builds.
  `config/ntlite-presets/InstallApps.cmd` already covers the winget path for
  users who want this.
- Defender removal / `RealtimeScanDirection` downgrade (zISOTweaker,
  d3adconnection `AdminQualityofLife.reg`) — violates the AppX keep-list.
- UAC disable, SMB signing disable, insecure guest auth, Attachment Manager
  `LowRiskFileTypes`, `ExecutionPolicy=Bypass` (ShivamXD6, d3adconnection) —
  security downgrades with no build-quality benefit.
- `zISOTweaker/functions/uup-dump-get-windows-iso.ps1` —
  `scripts/download_uup.py` is further along (path-traversal guard, presets,
  ~90% test coverage).
- d3adconnection `sources/ei.cfg` — this pipeline exports a single edition via
  `custom_convert.sh`, so a channel/edition-visibility file has nothing to do.

Source repos: [zISOTweaker](https://github.com/zoicware/zISOTweaker),
[Optimize-Windows](https://github.com/ShivamXD6/Optimize-Windows),
[UnattendedWinstall](https://github.com/memstechtips/UnattendedWinstall),
[windows-unattended-debloat](https://github.com/deffz-finesse/windows-unattended-debloat),
[Win11CleanInstall](https://github.com/d3adconnection/Win11CleanInstall).
