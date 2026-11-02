---
paths:
  - "scripts/download_uup.py"
  - "scripts/uup_api.py"
  - "scripts/uup_download.py"
  - "scripts/uup_profiles.py"
  - "tests/**/*.py"
---

# Python downloader rules

- Keep the existing CLI contract of `scripts/download_uup.py`; do not rename or remove current flags.
- `httpx` (HTTP client) and `orjson` (JSON) are project dependencies for these modules — use them, not `urllib`/`json`. Everything else prefers stdlib unless a dependency is already part of the repository workflow.
- Preserve the current download route through `uupdump.net`; do not add direct Microsoft download calls.
- Keep path validation and traversal protections intact, and extend tests when behavior changes.
- Cross-module calls go through the module (`uup_api.get_build_info_cached(...)`), not `from uup_api import ...`, so a test's `patch("uup_api.X")` reaches every caller.
- Use `uv run --group dev pytest tests/` for validation when downloader logic or tests change — the module now imports `httpx`/`orjson` at load time, so an isolated `uvx --with pytest` env without them will fail to import it.
