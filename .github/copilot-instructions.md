# Copilot Instructions — Debloated Windows 11 ISO Builder

A Linux shell/Python toolset that converts UUP dump files into debloated, unattended Windows 11 ISO images. Build pipeline is driven by `make`; all logic lives in `scripts/`.

---

## Architecture

| Layer | File(s) | Role |
|---|---|---|
| User interface | `Makefile` | All user-facing commands |
| Orchestration | `scripts/build.sh` | Drives the full pipeline |
| Conversion | `scripts/custom_convert.sh` | UUP → WIM via wimlib |
| Debloating | `scripts/debloat_wim.sh` | Removes AppX packages from WIM |
| Validation | `scripts/validate_prereqs.sh` | Pre-build dependency and file checks |
| Downloading | `scripts/download_uup.py` | Interactive UUP fetcher (uupdump.net API) |
| Setup | `scripts/setup_env.sh` | Installs system packages |
| Utilities | `scripts/utils.sh` | Shared color-coded log helpers |
| Config | `config/autounattend.xml` | Windows unattended answer file |
| Config | `config/debloat_list.txt` | Glob patterns for AppX removal |
| First-boot | `config/oem/SetupComplete.cmd` | Post-install tweaks (telemetry, perf) |

---

## Shell Script Conventions

Every script must start with:
```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/utils.sh"
```

Use only these four log helpers for user-facing output — never raw `echo`:
```bash
log_info    "Starting conversion..."   # cyan  [INFO]
log_success "ISO created."             # green [OK]
log_warn    "Low disk space."          # yellow [WARN]
log_error   "Missing dependency."      # red   [ERROR]
```

All file paths must derive from `PROJECT_ROOT` or `SCRIPT_DIR`. No hardcoded absolute paths.

After any edit: `bash -n scripts/<file>.sh`

---

## Python Conventions

- Python 3 only; stdlib preferred; `requests` is optional
- No root/sudo usage anywhere
- Do not change existing CLI argument names or flags in `download_uup.py`
- External runtime dependency: `aria2c` (parallel downloads)

---

## Makefile Conventions

When adding a target:
1. Add it to `.PHONY`
2. Add `chmod +x scripts/*.sh` before invoking shell scripts
3. Document it in the `help` target

---

## XML (autounattend.xml)

- UTF-8 encoding, no BOM
- Validate: `xmllint --noout config/autounattend.xml`

---

## Hard Rules — Never Violate These

### Protected AppX patterns
Do not add patterns to `debloat_list.txt` that match any of these:
```
*Store*              *WebView*           *VCLibs*
*UI.Xaml*            *Defender*          *DesktopAppInstaller*
```
Removing these breaks app installation and system functionality.

### No root in build pipeline
`wimlib` FUSE mounts work as a regular user. No `sudo` or `su` in `build.sh` or any script it calls.

### UUP file placement
`.cab` and `.esd` files must be directly in `uup_files/` — subdirectories are not scanned.

### upstream/ is read-only
`upstream/` contains reference copies of the UUP converter. Edit `scripts/convert_config.sh` for shared config, not files under `upstream/`.

### No direct Microsoft server calls
Route all downloads through `scripts/download_uup.py` which uses uupdump.net.

---

## Environment Variables

```bash
TARGET_EDITION=ProfessionalWorkstation   # preferred edition
FALLBACK_EDITION=Professional            # fallback if target not in WIM
PAUSE_FOR_WINDOWS_STAGE=0               # set 1 to pause for DISM servicing
```

---

## Validation

```bash
# Shell syntax
for f in scripts/*.sh; do bash -n "$f" && echo "OK: $f"; done

# XML
xmllint --noout config/autounattend.xml

# Prerequisites (no UUP files needed)
make validate

# Unit tests
python3 -m pytest tests/

# Full build (requires UUP files + ~20 GB free disk)
make build
```

---

## CI Checks

| Tool | Scope | Notes |
|---|---|---|
| ShellCheck | `scripts/*.sh` | `custom_convert.sh` excluded (upstream) |
| Flake8 + Black | `scripts/*.py` | max line length: 120 |
| xmllint | `config/autounattend.xml` | Must be valid XML |
| pytest | `tests/` | Python 3.9–3.12 on Ubuntu + macOS |

---

## Do Not

- Use `echo` for user-facing output — use `log_*` helpers from `utils.sh`
- Hardcode paths — derive from `SCRIPT_DIR` / `PROJECT_ROOT`
- Add `sudo`/`su` to the build pipeline
- Modify files under `upstream/`
- Add direct calls to Microsoft servers
- Swallow errors — let `set -euo pipefail` surface them
- Change existing CLI flags in `download_uup.py`


## vexp context tools <!-- vexp v1.3.11 -->

**MANDATORY: use `run_pipeline` — do NOT grep, glob, or read files manually.**
vexp returns pre-indexed, graph-ranked context in a single call.

### Workflow
1. `run_pipeline` with your task description — ALWAYS FIRST (replaces all other tools)
2. Make targeted changes based on the context returned
3. `run_pipeline` again only if you need more context

### Available MCP tools
- `run_pipeline` — **PRIMARY TOOL**. Runs capsule + impact + memory in 1 call.
  Auto-detects intent. Includes file content. Example: `run_pipeline({ "task": "fix auth bug" })`
- `get_context_capsule` — lightweight, for simple questions only
- `get_impact_graph` — impact analysis of a specific symbol
- `search_logic_flow` — execution paths between functions
- `get_skeleton` — compact file structure
- `index_status` — indexing status
- `get_session_context` — recall observations from sessions
- `search_memory` — cross-session search
- `save_observation` — persist insights (prefer run_pipeline's observation param)

### Agentic search
- Do NOT use built-in file search, grep, or codebase indexing — always call `run_pipeline` first
- If you spawn sub-agents or background tasks, pass them the context from `run_pipeline`
  rather than letting them search the codebase independently

### Smart Features
Intent auto-detection, hybrid ranking, session memory, auto-expanding budget.

### Multi-Repo
`run_pipeline` auto-queries all indexed repos. Use `repos: ["alias"]` to scope. Run `index_status` to see aliases.
<!-- /vexp -->