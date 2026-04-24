# AGENTS.md — Debloated Windows 11 ISO Builder

Canonical repository guidance for coding agents and contributors.
Edit this file when repo-wide guidance changes.
Keep `CLAUDE.md` as a symlink to this file.
Keep `.github/copilot-instructions.md` short.
Allow matching files under `.github/instructions/` to add narrower rules for their scope.

## Mission and entry points

- Build debloated, unattended Windows 11 ISO images from UUP dump files on Linux.
- User-facing entry point: `Makefile`
- Main orchestrator: `scripts/build.sh`
- UUP downloader: `scripts/download_uup.py`
- Shared shell helpers: `scripts/utils.sh`

Normal flow:

```text
make deps -> make download -> make validate -> make build
```

## Non-negotiable invariants

### Protected AppX patterns
Treat these patterns as required keeps and preserve them in `config/debloat_list.txt` and `scripts/debloat_wim.sh`:

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
- Keep `scripts/build.sh` and the scripts it calls runnable as a regular user.
- `wimlib` FUSE mounts work as a regular user, so user-space flows are the default.

### UUP inputs stay flat
- Place `.cab` and `.esd` files directly in the repository input directory named `uup_files`.
- The build scripts do not scan nested directories.

### Upstream-derived converter logic stays isolated
- Treat `scripts/custom_convert.sh` as an upstream-derived file unless the task explicitly requires syncing or patching it.
- If shared converter behavior must change, prefer updating `scripts/convert_config.sh`.

### Downloads must go through uupdump.net
- Keep download logic inside `scripts/download_uup.py`.
- Add new download behavior only through the existing uupdump.net-based flow.

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
- `make validate` expects a local `uup_files` directory and will report missing inputs until UUP files are staged.
- Only run `make build` when UUP files and disk space are available.

## Existing CI coverage

- `.github/workflows/lint-and-format.yml`
- `.github/workflows/test-matrix.yml`
- `.github/workflows/build-and-deploy.yml`
- `.github/workflows/copilot-setup-steps.yml`

## Change-management expectations

- Update `CHANGELOG.md` for contributor-facing changes.
- Keep guidance concise, repository-specific, and internally consistent.
- Prefer improving existing files over creating overlapping duplicates.
