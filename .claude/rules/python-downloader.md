---
paths:
  - "scripts/download_uup.py"
  - "tests/**/*.py"
---

# Python downloader rules

- Keep the existing CLI contract of `scripts/download_uup.py`; do not rename or remove current flags.
- `httpx` (HTTP client) and `orjson` (JSON) are project dependencies for this file — use them, not `urllib`/`json`. Everything else prefers stdlib unless a dependency is already part of the repository workflow.
- Preserve the current download route through `uupdump.net`; do not add direct Microsoft download calls.
- Keep path validation and traversal protections intact, and extend tests when behavior changes.
- Use `uv run --group dev pytest tests/` for validation when downloader logic or tests change — the module now imports `httpx`/`orjson` at load time, so an isolated `uvx --with pytest` env without them will fail to import it.
