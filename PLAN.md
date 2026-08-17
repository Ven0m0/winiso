# Implementation Plan
_Updated: 2026-07-23_

Linux-based builder for a debloated Windows 11 ISO. Pipeline is Python
(`build.py`, `download_uup.py`, `debloat_wim.py`, `validate_prereqs.py`,
`sign_iso.py`) — the older shell pipeline it replaced is gone. This plan
tracks only real remaining work. `TODO.md` still describes the old shell
pipeline and speculative features; treat it as historical until refreshed.

## Recently completed
- **Debloat pattern validator** — `scripts/validate_debloat.py` checks
  `config/debloat_list.txt` (plus `.uup-groups`-selected component patterns)
  for invalid glob syntax, duplicates, and collisions with the protected AppX
  keep-list. Wired into `make validate-debloat` / `mise run lint-debloat`,
  kept separate from `make validate` like `validate-xml`/`validate-reg`.
- **Driver injection** — `apply_image_settings.py --driver-path <dir>` runs
  `dism /Image:<mount> /Add-Driver /Driver:<dir> /Recurse` against the mounted
  install.wim before the answer-file/registry steps.
- **`tests/test_security.py` expanded** — added 5 tests exercising the real
  `download_uup._resolve_output_dir()` (normal, subdir, `..` traversal,
  absolute-outside, and the `<root>_secret` prefix exploit) instead of only a
  standalone mock of its logic. Added `.coveragerc` (`source = scripts`,
  excludes `if __name__ == "__main__":`). `download_uup.py` measured at 90%
  coverage, already past the 80% target — no further coverage work queued.
- **Profile wiring** — `build.py` now accepts `--profile`/`PROFILE` (loads
  `config/profiles.json`, sets `TARGET_EDITION` from `profile["edition"]`)
  and `--edition` (highest-precedence override). Dropped the dead
  `edition_filter` glob-list field from `profiles.json` — nothing consumed
  it, and `custom_convert.sh` only does exact single-string edition
  matching, so a glob list didn't fit; `profile["edition"]` alone covers it.
- **Component-group debloat wiring** — `debloat_wim.py` now reads the
  `.uup-groups` file (already written by `download_uup.py --preset`/
  `--groups`, previously had no consumer), expands selected group names via
  `config/component_groups.json` into glob patterns, and merges them into
  the delete list. Patterns matching the protected keep-list (`*Store*
  *WebView* *VCLibs* *UI.Xaml* *Defender* *DesktopAppInstaller*`) are
  skipped with a warning. Covered by `tests/test_debloat_wim.py`.
- **`log_debug`/`LOG_LEVEL` parity** — `download_uup.py` had its own
  `log_info`/`log_warn`/`log_error` (doesn't import `pyutils`) but no debug
  gate; added, matching `pyutils.py`'s existing pattern.
- **aria2c stderr on failure** — `_run_aria2_download` now prints the last
  20 lines of `e.stderr` unconditionally on failure (full output still
  shown with `--verbose`), instead of showing only the exit code.
- Type hints — `download_uup.py` fully annotated (61 funcs, `@overload`/`Literal`/`cast`).
- Pre-build XML validation — `scripts/validate_prereqs.py:87-96` + `make validate-xml`.
- ISO signing — `scripts/sign_iso.py` + `make sign` (SHA256/512 + optional GPG).
- First-run framework — `config/oem/SetupComplete.cmd` (hibernate-off + 8.3 short-name
  stripping merged in as native batch; `scripts/files/setup_post_install.py` retired,
  it required a Python runtime that doesn't exist on a freshly-installed target Windows).
  `apply_image_settings.py` now injects this same canonical file into the WIM directly.
- Download-path test coverage — `tests/test_download_uup.py` (230 tests, 46 classes).

## Now
(nothing queued — see Next below)

## Next (small, unstarted)
- Language pack support.
- QEMU boot smoke test for produced ISOs.

## Someday / maybe (not planned — YAGNI until requested)
Delta downloads, mirror sources, build history cache, multi-edition ISO,
telemetry scoring, privacy dashboard, service/firewall hardening, BitLocker/
Sandbox/WSL config toggles, GPO injection, drift detection, build telemetry,
update alerts, health checks, rollback/backup, regression suite, compatibility
matrix, performance benchmarks, security fuzzing, plugin system, WIM
layering/diff, A/B partitions, secure boot signing, AI/ML recommend/predict/
triage.

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
