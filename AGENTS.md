# AGENTS.md — Debloated Windows 11 ISO Builder

Canonical repository guidance for coding agents and contributors.
Edit this file when repo-wide guidance changes. `CLAUDE.md` must stay a symlink to this file, and `.github/copilot-instructions.md` must stay short and point back here.

## Mission and entry points

- Build debloated, unattended Windows 11 ISO images from UUP dump files on Linux.
- User-facing entry point: `/home/runner/work/winiso/winiso/Makefile`
- Main orchestrator: `/home/runner/work/winiso/winiso/scripts/build.sh`
- UUP downloader: `/home/runner/work/winiso/winiso/scripts/download_uup.py`
- Shared shell helpers: `/home/runner/work/winiso/winiso/scripts/utils.sh`

Normal flow:

```text
make deps -> make download -> make validate -> make build
```

## Non-negotiable invariants

### Protected AppX patterns
Never add removal patterns that match any of these:

```text
*Store*
*WebView*
*VCLibs*
*UI.Xaml*
*Defender*
*DesktopAppInstaller*
```

These packages keep Store installs, WebView, runtimes, and core Windows functionality working.

### Build pipeline must stay non-root
- Do not add `sudo` or `su` to `/home/runner/work/winiso/winiso/scripts/build.sh` or the scripts it calls.
- `wimlib` FUSE mounts work as a regular user.

### UUP inputs stay flat
- `.cab` and `.esd` files must live directly under `/home/runner/work/winiso/winiso/uup_files/`.
- The build scripts do not scan nested directories.

### Upstream sources are read-only
- Do not edit files under `/home/runner/work/winiso/winiso/upstream/`.
- If shared converter behavior must change, update `/home/runner/work/winiso/winiso/scripts/convert_config.sh` instead.

### Downloads must go through uupdump.net
- Keep download logic inside `/home/runner/work/winiso/winiso/scripts/download_uup.py`.
- Do not add direct Microsoft download flows elsewhere in the repository.

## Repository map

```text
config/
  autounattend.xml
  debloat_list.txt
  oem/SetupComplete.cmd

docs/
  autounattend.md

scripts/
  build.sh
  custom_convert.sh
  convert_config.sh
  debloat_wim.sh
  download_uup.py
  setup_env.sh
  utils.sh
  validate_prereqs.sh
  windows_service.cmd

tests/
  test_download_uup.py
  test_security.py

.github/
  copilot-instructions.md
  instructions/
  skills/
  workflows/
```

## File-specific guidance

### Shell scripts in `scripts/*.sh`
Every maintained shell script should start with:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/utils.sh"
```

Rules:
- Use `log_info`, `log_success`, `log_warn`, and `log_error` for user-facing output.
- Derive paths from `SCRIPT_DIR` or `PROJECT_ROOT`; do not hardcode machine-specific absolute paths inside scripts.
- Let failures surface through `set -euo pipefail`; do not hide errors.
- `custom_convert.sh` is upstream-derived and excluded from normal cleanup unless the task explicitly requires it.

### `Makefile`
When adding or changing a target:
- Keep `.PHONY` in sync.
- Run `chmod +x scripts/*.sh` before invoking shell scripts.
- Document the target in `help` output.
- Keep commands aligned with the real scripts and environment variables used by `scripts/build.sh`.

### `scripts/download_uup.py` and `tests/`
- Python 3 only; stdlib-first.
- Keep the existing CLI interface stable; do not rename or remove existing flags.
- `aria2c` remains the external runtime dependency for parallel downloads.
- Preserve path traversal safeguards and keep tests covering them.

### `config/`
- `config/autounattend.xml` must stay UTF-8 without BOM.
- `config/oem/SetupComplete.cmd` must keep CRLF line endings.
- `config/debloat_list.txt` should remain grouped by comment headers with one glob per line.

### Guidance and workflow files
- `AGENTS.md` is the canonical long-form guide.
- `.github/copilot-instructions.md` should only be a short startup bootstrap.
- `.github/instructions/*.instructions.md` should hold narrow, reusable rules.
- `.github/skills/*/SKILL.md` should capture recurring repo workflows.
- Workflows should use minimal triggers, least-privilege permissions, and only the tools this repo actually uses.

## Validation matrix

Run the smallest relevant subset for the files you touched:

```bash
# Shell syntax
for f in scripts/*.sh; do bash -n "$f"; done

# XML
xmllint --noout config/autounattend.xml

# Python tests
python3 -m pytest tests/

# Pre-build validation
make validate
```

Additional expectations:
- If you edit shell scripts, syntax-check the changed scripts immediately.
- If you edit workflow or guidance files, verify referenced paths and commands exist.
- Only run `make build` when UUP files and disk space are available.

## Existing CI coverage

- `/home/runner/work/winiso/winiso/.github/workflows/lint-and-format.yml`
- `/home/runner/work/winiso/winiso/.github/workflows/test-matrix.yml`
- `/home/runner/work/winiso/winiso/.github/workflows/build-and-deploy.yml`
- `/home/runner/work/winiso/winiso/.github/workflows/copilot-setup-steps.yml`

## Change-management expectations

- Update `/home/runner/work/winiso/winiso/CHANGELOG.md` for contributor-facing changes.
- Keep guidance concise, repository-specific, and internally consistent.
- Prefer improving existing files over creating overlapping duplicates.
