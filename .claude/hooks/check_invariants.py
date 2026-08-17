#!/usr/bin/env python3
"""PostToolUse hook: flag AGENTS.md Hard Invariant violations after Edit/Write.

Reads the raw tool input from CLAUDE_TOOL_INPUT and, if it names one of the
guarded files, re-checks that file on disk (the edit has already landed by
PostToolUse time).
"""

from __future__ import annotations

import os
import re
import sys

KEEP_LIST = re.compile(r"Store|WebView|VCLibs|UI\.Xaml|Defender|DesktopAppInstaller")
BOM = b"\xef\xbb\xbf"

XML_FILES = ("config/autounattend.xml", "ventoy/answer/autounattend.xml")
SETUP_COMPLETE = "config/oem/SetupComplete.cmd"
DEBLOAT_LIST = "config/debloat_list.txt"


def main() -> int:
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    if DEBLOAT_LIST in tool_input and os.path.isfile(DEBLOAT_LIST):
        with open(DEBLOAT_LIST, encoding="utf-8") as f:
            bad = [
                f"  line {i}: {line.strip()}"
                for i, line in enumerate(f, 1)
                if line.strip()
                and not line.lstrip().startswith("#")
                and KEEP_LIST.search(line)
            ]
        if bad:
            print(
                f"WARNING: {DEBLOAT_LIST} has patterns overlapping the AppX keep-list (AGENTS.md Hard Invariants):",
                file=sys.stderr,
            )
            print("\n".join(bad), file=sys.stderr)

    for xml in XML_FILES:
        if xml in tool_input and os.path.isfile(xml):
            with open(xml, "rb") as f:
                if f.read(3) == BOM:
                    print(
                        f"BLOCKED: {xml} has a UTF-8 BOM (AGENTS.md requires UTF-8 without BOM)",
                        file=sys.stderr,
                    )
                    return 2

    if SETUP_COMPLETE in tool_input and os.path.isfile(SETUP_COMPLETE):
        with open(SETUP_COMPLETE, "rb") as f:
            data = f.read()
        if b"\n" in data and b"\r\n" not in data:
            print(
                f"WARNING: {SETUP_COMPLETE} may be missing CRLF line endings (AGENTS.md requires CRLF)",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
