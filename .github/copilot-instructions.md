# Copilot Instructions — Debloated Windows 11 ISO Builder

Use this file as the quick bootstrap, then read `AGENTS.md` for the canonical repo-wide guide.

## Quick bootstrap
- User entry point: `Makefile`
- Main build flow: `make deps -> make download -> make validate -> make build`
- Build orchestrator: `scripts/build.sh`
- Downloader: `scripts/download_uup.py`
- Optional Windows servicing handoff: `scripts/windows_service.cmd`

## Rules to keep in mind
- Keep the Linux build pipeline runnable as a regular user.
- Place UUP `.cab` and `.esd` files directly in the repository input directory named `uup_files`.
- Preserve these protected AppX patterns: `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`.
- Treat `scripts/custom_convert.sh` as upstream-derived unless the task explicitly requires a change there.
- Keep existing CLI flags in `scripts/download_uup.py` stable.
- Keep `CLAUDE.md` as a symlink to `AGENTS.md`.

## Use the focused guidance files
- `.github/instructions/shell-build.instructions.md`
- `.github/instructions/python-downloader.instructions.md`
- `.github/instructions/workflow-and-guidance.instructions.md`

## Common validation
```bash
for f in scripts/*.sh; do bash -n "$f"; done
xmllint --noout config/autounattend.xml
uvx --with pytest pytest tests/
```

Run `make validate` only when a local `uup_files/` directory with real UUP inputs is present; otherwise rely on the shell, XML, and pytest checks above.
