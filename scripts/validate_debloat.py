#!/usr/bin/env python3
"""validate_debloat.py - Validate debloat glob patterns before applying to a WIM

Checks config/debloat_list.txt (plus any component-group patterns pulled in via
.uup-groups) for invalid syntax, duplicates, and accidental collisions with the
protected AppX keep-list (Store/WebView/VCLibs/UI.Xaml/Defender/DesktopAppInstaller).

Usage: python scripts/validate_debloat.py
"""

import sys

from debloat_wim import (
    CONFIG_FILE,
    PATTERN_RE,
    is_protected_pattern,
    load_group_patterns,
    load_patterns,
)
from pyutils import log_error, log_info, log_success, log_warn


def check_raw_lines() -> int:
    """Re-scans CONFIG_FILE directly so invalid lines are reported with a line
    number; load_patterns() already skips them silently with just a warn log."""
    if not CONFIG_FILE.is_file():
        log_error(f"debloat_list.txt not found: {CONFIG_FILE}")
        return 1

    errors = 0
    for lineno, raw_line in enumerate(
        CONFIG_FILE.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not PATTERN_RE.match(line):
            log_error(f"{CONFIG_FILE.name}:{lineno}: invalid pattern syntax: {line!r}")
            errors += 1
        elif is_protected_pattern(line):
            log_error(
                f"{CONFIG_FILE.name}:{lineno}: pattern '{line}' matches the protected "
                "AppX keep-list"
            )
            errors += 1
    return errors


def warn_duplicates(patterns: list[str]) -> None:
    seen: set[str] = set()
    dupes: set[str] = set()
    for pattern in patterns:
        lowered = pattern.lower()
        if lowered in seen:
            dupes.add(pattern)
        seen.add(lowered)
    for dupe in sorted(dupes):
        log_warn(f"Duplicate pattern: {dupe}")


def main() -> int:
    log_info(f"Validating {CONFIG_FILE}...")
    errors = check_raw_lines()

    patterns = load_patterns()
    group_patterns = load_group_patterns()
    for pattern in group_patterns:
        if pattern not in patterns:
            patterns.append(pattern)

    warn_duplicates(patterns)
    log_info(
        f"{len(patterns)} pattern(s) total ({len(group_patterns)} from component groups)"
    )

    if errors:
        log_error(f"Validation failed: {errors} error(s)")
        return 1

    log_success("All debloat patterns valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
