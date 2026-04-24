# Copilot Instructions — Debloated Windows 11 ISO Builder

Start here, then read `/home/runner/work/winiso/winiso/AGENTS.md` for the canonical repo-wide guide.

## Quick bootstrap
- User entry point: `/home/runner/work/winiso/winiso/Makefile`
- Main build flow: `make deps -> make download -> make validate -> make build`
- Build orchestrator: `/home/runner/work/winiso/winiso/scripts/build.sh`
- Downloader: `/home/runner/work/winiso/winiso/scripts/download_uup.py`

## Rules to keep in mind
- Do not add `sudo` or `su` to the Linux build pipeline.
- Keep UUP `.cab` and `.esd` files directly in `/home/runner/work/winiso/winiso/uup_files/`.
- Never remove or match these protected AppX patterns: `*Store*`, `*WebView*`, `*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`.
- Do not edit `/home/runner/work/winiso/winiso/upstream/`.
- Do not rename or remove existing CLI flags in `scripts/download_uup.py`.
- Keep `CLAUDE.md` as a symlink to `AGENTS.md`.

## Use the focused guidance files
- `/home/runner/work/winiso/winiso/.github/instructions/shell-build.instructions.md`
- `/home/runner/work/winiso/winiso/.github/instructions/python-downloader.instructions.md`
- `/home/runner/work/winiso/winiso/.github/instructions/workflow-and-guidance.instructions.md`

## Common validation
```bash
for f in scripts/*.sh; do bash -n "$f"; done
xmllint --noout config/autounattend.xml
python3 -m pytest tests/
make validate
```
