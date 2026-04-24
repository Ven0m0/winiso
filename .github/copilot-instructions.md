# Copilot Instructions — Debloated Windows 11 ISO Builder

Start here, then read `AGENTS.md` for the canonical repo-wide guide.
Precedence: direct task instructions first, then matching files in `.github/instructions/`, then this bootstrap, then `AGENTS.md`.

## Quick bootstrap
- User entry point: `Makefile`
- Main build flow: `make deps -> make download -> make validate -> make build`
- Build orchestrator: `scripts/build.sh`
- Downloader: `scripts/download_uup.py`

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
python3 -m pytest tests/
make validate
```

`make validate` is expected to fail until a local `uup_files` directory and real UUP inputs are present.
