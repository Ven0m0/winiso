# Copilot Instructions — Debloated Windows 11 ISO Builder

Use this file as the quick bootstrap, then read `AGENTS.md` for the canonical repo-wide guide.

## Quick bootstrap
- User entry point: `Makefile`
- Main build flow: `make deps -> make download -> make validate -> make build`
- Build orchestrator: `scripts/build.py`
- Downloader: `scripts/download_uup.py`
- Optional Windows servicing handoff: `scripts/windows_service.cmd` (standalone batch) or `scripts/apply_image_settings.py` (Python, dism.exe-based)

## Rules to keep in mind
- Keep the Linux build pipeline runnable as a regular user.
- Place UUP `.cab` and `.esd` files directly in the repository input directory named `uup_files`.
- Preserve these protected AppX patterns: `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`.
- Treat `scripts/custom_convert.sh` (and `scripts/convert_config.sh`, which it sources) as upstream-derived unless the task explicitly requires a change there — these are the only scripts that stay bash.
- Keep existing CLI flags in `scripts/download_uup.py` stable.
- Keep `CLAUDE.md` as a symlink to `AGENTS.md`.

## Use the focused guidance files
- `.github/instructions/shell-build.instructions.md`
- `.github/instructions/python-downloader.instructions.md`
- `.github/instructions/windows-servicing.instructions.md`
- `.github/instructions/workflow-and-guidance.instructions.md`

## Common validation
```bash
for f in scripts/*.py scripts/files/*.py; do python3 -m py_compile "$f"; done
bash -n scripts/custom_convert.sh scripts/convert_config.sh scripts/utils.sh
xmllint --noout ventoy/answer/autounattend.xml config/autounattend.xml
diff -u ventoy/answer/autounattend.xml config/autounattend.xml  # config/ is a copy of the canonical ventoy/answer/ file
python3 scripts/validate_reg_files.py                           # .reg headers, standalone + embedded in autounattend.xml
uvx --with pytest pytest tests/
```

Run `make validate` only when a local `uup_files/` directory with real UUP inputs is present; otherwise rely on the shell, XML, and pytest checks above.
