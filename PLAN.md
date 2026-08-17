# Implementation Plan
_Updated: 2026-08-17_

Linux-based builder for a debloated Windows 11 ISO. Pipeline is Python
(`build.py`, `download_uup.py`, `debloat_wim.py`, `validate_prereqs.py`,
`sign_iso.py`) — the older shell pipeline it replaced is gone. This plan
tracks only real remaining work. Completed work lives in `CHANGELOG.md`,
not here — do not duplicate finished items back into this file.

## Now
(nothing queued — see Next below)

## Next (small, unstarted)
- QEMU boot smoke test for produced ISOs.
- DEBLOAT-001: smart debloat dependency checker (detect AppX removal
  conflicts before applying). Blocks DEBLOAT-010 (selective pattern merge
  from `ShivamXD6/Optimize-Windows`, see `TODO.md`).

## Someday / maybe (not planned — YAGNI until requested)
Multi-edition ISO, web dashboard, telemetry scoring, privacy dashboard,
service/firewall hardening, BitLocker/Sandbox/WSL config toggles, GPO
injection, drift detection, build telemetry, update alerts, health checks,
rollback/backup, regression suite, compatibility matrix, performance
benchmarks, security fuzzing, plugin system, WIM layering/diff, A/B
partitions, secure boot signing, AI/ML recommend/predict/triage.

## Housekeeping
- `.mise/tasks/` now holds only `install`; the rest of the tasks already live
  in `mise.toml`. Low-priority: fold `install` in too or leave as-is.
- No `pyproject.toml`/mypy/pytest config exists. Ruff is configured via
  `mise.toml`. `pyrightconfig.json` sets `typeCheckingMode: standard` and scopes
  `basedpyright` to `scripts/download_uup.py`, matching the pre-commit hook and
  AGENTS.md's "other scripts are not yet gated on this" — basedpyright's own
  stricter-than-pyright default rules (`reportAny`, `reportExplicitAny`, etc.)
  were never deliberately opted into. Add strict typing/coverage gates only if
  actually wanted.
