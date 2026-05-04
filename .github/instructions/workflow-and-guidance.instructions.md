---
description: "Rules for Copilot guidance, workflow files, and shared developer automation config."
applyTo: ".github/workflows/*.{yml,yaml},AGENTS.md,CLAUDE.md,.github/copilot-instructions.md,.github/instructions/**/*.md,.github/skills/**/*.md,CHANGELOG.md,mise.toml,.pre-commit-config.yaml,PSScriptAnalyzerSettings.psd1"
---

# Workflow and guidance rules

- `AGENTS.md` is the canonical long-form guide; keep `.github/copilot-instructions.md` short and defer detailed policy there.
- `CLAUDE.md` must remain a symlink to `AGENTS.md`.
- Keep workflows scoped to the repository's real toolchain: shell scripts, XML, Python tests, PowerShell servicing helpers, Makefile tasks, and ISO build prerequisites.
- Use minimal triggers, least-privilege `permissions`, and explicitly versioned action references (for example, major tags like `actions/checkout@v4` rather than unversioned references such as `@main`).
- Only install tools the repository actually uses; remove generic setup for ecosystems not present in the repo.
- Update `CHANGELOG.md` for contributor-facing workflow or guidance changes.
