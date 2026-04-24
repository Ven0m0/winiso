---
applyTo: "scripts/download_uup.py,tests/**/*.py"
---

# Python downloader rules

- Keep the existing CLI contract of `scripts/download_uup.py`; do not rename or remove current flags.
- Prefer Python stdlib modules unless a dependency is already part of the repository workflow.
- Preserve the current download route through `uupdump.net`; do not add direct Microsoft download calls.
- Keep path validation and traversal protections intact, and extend tests when behavior changes.
- Use `python3 -m pytest tests/` for validation when downloader logic or tests change.
