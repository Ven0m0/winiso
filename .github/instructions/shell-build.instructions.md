---
applyTo: "Makefile,scripts/**/*.sh"
---

# Shell build pipeline rules

- Keep the standard shell prologue: `#!/bin/bash`, `set -euo pipefail`, `SCRIPT_DIR`, `PROJECT_ROOT`, and `source "$SCRIPT_DIR/utils.sh"`.
- Use `log_info`, `log_success`, `log_warn`, and `log_error` for user-facing output instead of adding new logging styles.
- Derive paths from `SCRIPT_DIR` or `PROJECT_ROOT`; do not introduce machine-specific absolute paths inside scripts.
- Do not add `sudo` or `su` to `scripts/build.sh` or any script in the Linux build pipeline.
- When editing `Makefile`, keep `.PHONY`, `chmod +x scripts/*.sh`, and `help` output aligned with the real targets.
- If a change touches `debloat_wim.sh` or `config/debloat_list.txt`, preserve the protected AppX patterns listed in `AGENTS.md`.
- Validate changed shell scripts with `bash -n` and run `make validate` when workflow-impacting shell behavior changes.
