---
applyTo: ".github/workflows/*.{yml,yaml},AGENTS.md,CLAUDE.md,.github/copilot-instructions.md,.github/instructions/**/*.md,.github/skills/**/*.md,CHANGELOG.md"
---

# Workflow and guidance rules

- `AGENTS.md` is the canonical long-form guide; keep `.github/copilot-instructions.md` short and defer detailed policy there.
- `CLAUDE.md` must remain a symlink to `AGENTS.md`.
- Keep workflows scoped to the repository's real toolchain: shell scripts, XML, Python tests, Makefile tasks, and ISO build prerequisites.
- Use minimal triggers, least-privilege `permissions`, and pinned action versions.
- Only install tools the repository actually uses; remove generic setup for ecosystems not present in the repo.
- Update `CHANGELOG.md` for contributor-facing workflow or guidance changes.
