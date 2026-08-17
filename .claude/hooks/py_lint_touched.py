#!/usr/bin/env python3
"""PostToolUse hook: ruff-fix + py_compile the pipeline scripts after a Python edit.

Only fires when the edited file is under scripts/ or tests/ and ends in .py
(checked against the raw CLAUDE_TOOL_INPUT text). Never blocks: failures are
reported to stderr so the agent sees them, but the edit itself already landed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PY_PATH = re.compile(r"(scripts|tests)/[^\"']*\.py")


def main() -> int:
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not PY_PATH.search(tool_input):
        return 0

    root = Path(__file__).resolve().parents[2]
    subprocess.run(
        ["ruff", "check", "--fix", "scripts/", "tests/"],
        cwd=root,
        check=False,
    )

    failed = []
    for py_file in sorted(root.glob("scripts/*.py")) + sorted(
        root.glob("scripts/files/*.py")
    ):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(py_file)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failed.append(py_file.name)
            print(result.stderr, file=sys.stderr)

    if failed:
        print(f"WARNING: py_compile failed for: {', '.join(failed)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
