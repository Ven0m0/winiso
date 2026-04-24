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
4. Validate the smallest relevant set:
   - `for f in scripts/*.sh; do bash -n "$f"; done`
   - `xmllint --noout config/autounattend.xml`
   - `python3 -m pytest tests/`
   - `make validate`
5. Update `CHANGELOG.md` when contributor-facing behavior or guidance changes.
