---
name: iso-build-pipeline
description: Use when updating shell/build pipeline files, config, or guidance for the debloated Windows 11 ISO workflow while preserving repo invariants.
---

# ISO build pipeline

## Use when
- Changing `Makefile` targets or build orchestration in `scripts/`
- Updating `AGENTS.md`, `.github/copilot-instructions.md`, or repo-specific instruction files
- Adjusting workflow validation that supports the shell/XML/Python toolchain used by this repo

## Required checks
1. Read `AGENTS.md` and the focused files under `.github/instructions/`.
2. Preserve the protected AppX patterns and the no-`sudo` rule in the Linux build pipeline.
3. Keep `CLAUDE.md` as a symlink to `AGENTS.md`.
4. Treat `scripts/custom_convert.sh` as upstream-derived; only change it when the task explicitly calls for converter work.
5. Keep PowerShell and CMD changes scoped to the optional Windows servicing handoff instead of the default Linux build path.
6. Validate the smallest relevant set:
   - `for f in scripts/*.sh; do bash -n "$f"; done`
   - `xmllint --noout config/autounattend.xml`
   - `uvx --with pytest pytest tests/`
   - `make validate` only when `uup_files/` contains real repository-local UUP inputs or the task is explicitly about prerequisite validation
7. Update `CHANGELOG.md` when contributor-facing behavior or guidance changes.
