---
paths:
  - "Makefile"
  - "scripts/build.py"
  - "scripts/setup_env.py"
  - "scripts/sign_iso.py"
  - "scripts/validate_prereqs.py"
  - "scripts/debloat_wim.py"
  - "scripts/pyutils.py"
  - "scripts/convert_ve_plugin"
  - "scripts/custom_convert.sh"
  - "scripts/convert_config.sh"
  - "scripts/utils.sh"
---

# Linux build pipeline rules

- Pipeline scripts (`build.py`, `setup_env.py`, `sign_iso.py`, `validate_prereqs.py`, `debloat_wim.py`) are Python 3, stdlib-first; `import pyutils` for logging (`log_info`/`log_success`/`log_warn`/`log_error`) instead of adding new logging styles.
- Derive paths from `Path(__file__).resolve().parent` (`SCRIPT_DIR`) or its parent (`PROJECT_ROOT`); do not introduce machine-specific absolute paths inside scripts.
- Do not add `sudo`/elevation to `build.py` or any script in the Linux build pipeline.
- Treat `scripts/custom_convert.sh` and `scripts/convert_config.sh` (which it sources) as upstream-derived and patch-only unless the task explicitly requires a converter change — these are the only scripts that stay bash.
- `scripts/utils.sh` stays bash too, solely because `custom_convert.sh` sources it. Do not add new Python consumers of it — use `pyutils.py` instead.
- When editing `Makefile`, keep `.PHONY`, the `chmod +x scripts/<script>.py` + `./scripts/<script>.py` invocation pattern, and `help` output aligned with the real targets.
- If a change touches `debloat_wim.py` or `config/debloat_list.txt`, preserve the protected AppX patterns listed in `AGENTS.md`.
- Validate changed Python scripts with `python -m py_compile`; validate `custom_convert.sh`/`convert_config.sh` with `bash -n`. Run `make validate` only when local `uup_files/` inputs are present or the task specifically targets prerequisite validation.
