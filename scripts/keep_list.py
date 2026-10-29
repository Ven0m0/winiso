"""keep_list.py - AppX removal patterns, the keep-list, and component groups.

Single owner of config/debloat_list.txt, config/component_groups.json and the
.uup-groups selection file written by download_uup.py. Stdlib-only on purpose:
apply_image_settings.py runs under a bare Windows python.exe with no venv, so it
must never reach httpx/orjson through this module (use json, not orjson).
"""

import json
import re
from pathlib import Path
from typing import Any

from pyutils import log_error, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "debloat_list.txt"
GROUPS_SELECTION_FILE = PROJECT_ROOT / ".uup-groups"
COMPONENT_GROUPS_FILE = PROJECT_ROOT / "config" / "component_groups.json"

# Never let a component group delete these, regardless of selection.
PROTECTED_KEYWORDS = (
    "store",
    "webview",
    "vclibs",
    "ui.xaml",
    "defender",
    "desktopappinstaller",
)

PATTERN_RE = re.compile(r"^[a-zA-Z0-9.*_-]+$")


def load_patterns() -> list[str]:
    if not CONFIG_FILE.is_file():
        return []
    patterns: list[str] = []
    for raw_line in CONFIG_FILE.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not PATTERN_RE.match(line):
            log_warn(f"Skipping invalid pattern: {line}")
            continue
        patterns.append(line)
    return patterns


def is_protected_pattern(pattern: str) -> bool:
    lowered = pattern.lower()
    return any(keyword in lowered for keyword in PROTECTED_KEYWORDS)


def load_component_groups(path: str | Path | None = None) -> dict[str, Any]:
    """Load config/component_groups.json as name -> {"description", "patterns"}.

    Returns an empty dict if the file is missing, malformed, or has an unexpected
    shape. Entries without at least one string pattern are dropped.
    """
    source = COMPONENT_GROUPS_FILE if path is None else path
    try:
        data: Any = json.loads(Path(source).read_bytes())
    except (OSError, ValueError) as exc:
        log_warn(f"Could not load component groups from {source}: {exc}")
        return {}
    if not isinstance(data, dict):
        log_warn(f"Component groups file {source} is not a JSON object")
        return {}
    raw_groups: Any = data.get("groups", data)
    if not isinstance(raw_groups, dict):
        log_warn(f"Component groups in {source} are not a mapping")
        return {}
    result: dict[str, Any] = {}
    for name, body in raw_groups.items():
        if not isinstance(name, str) or not isinstance(body, dict):
            continue
        patterns: Any = body.get("patterns", [])
        if not isinstance(patterns, list):
            continue
        cleaned: list[str] = [p for p in patterns if isinstance(p, str) and p]
        if not cleaned:
            continue
        description: str = (
            body.get("description", "")
            if isinstance(body.get("description"), str)
            else ""
        )
        result[name] = {"description": description, "patterns": cleaned}
    return result


def list_component_groups(path: str | Path | None = None) -> list[str]:
    """Return the names of all available component groups (sorted)."""
    return sorted(load_component_groups(path))


def get_component_group(
    name: str, path: str | Path | None = None
) -> dict[str, Any] | None:
    """Get a single component group by name, or None if not found."""
    return load_component_groups(path).get(name)


def validate_component_groups(
    names: list[str], path: str | Path | None = None
) -> list[str]:
    """Return the subset of `names` that exist, warning about unknown ones."""
    available = set(list_component_groups(path))
    valid: list[str] = []
    for name in names:
        if name in available:
            valid.append(name)
        else:
            log_warn(f"Unknown component group: {name}")
    return valid


def collect_component_patterns(
    group_names: list[str], path: str | Path | None = None
) -> list[str]:
    """Collect deduplicated glob patterns from the given groups, in order.

    Protected (keep-list) patterns are dropped with a warning.
    """
    groups = load_component_groups(path)
    seen: set[str] = set()
    combined: list[str] = []
    for group_name in group_names:
        group = groups.get(group_name)
        if group is None:
            log_warn(f"Unknown component group: {group_name}")
            continue
        for pattern in group["patterns"]:
            if pattern in seen:
                continue
            if is_protected_pattern(pattern):
                log_warn(
                    f"Skipping protected pattern from group '{group_name}': {pattern}"
                )
                continue
            seen.add(pattern)
            combined.append(pattern)
    return combined


def write_group_selection(
    group_names: list[str], output_path: str | Path = GROUPS_SELECTION_FILE
) -> bool:
    """Write the selected group names, one per line. Returns False on OSError."""
    try:
        Path(output_path).write_text(
            "".join(f"{name}\n" for name in group_names), encoding="utf-8"
        )
        return True
    except OSError as exc:
        log_error(f"Could not write component groups file {output_path}: {exc}")
        return False


def read_group_selection(path: str | Path | None = None) -> list[str]:
    """Read the group names written by write_group_selection (blank lines skipped)."""
    source = Path(GROUPS_SELECTION_FILE if path is None else path)
    if not source.is_file():
        return []
    return [
        line.strip()
        for line in source.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def load_group_patterns() -> list[str]:
    """Expand the .uup-groups selection into glob patterns, keep-list filtered."""
    group_names = read_group_selection()
    if not group_names or not COMPONENT_GROUPS_FILE.is_file():
        return []
    return collect_component_patterns(group_names)


def get_appx_patterns() -> list[str]:
    """Debloat list plus selected component groups, minus anything protected.

    The one place both build paths (Linux debloat_wim.py, Windows
    apply_image_settings.py) ask "what may be removed".
    """
    patterns = load_patterns()
    for pattern in load_group_patterns():
        if pattern not in patterns:
            patterns.append(pattern)
    return [p for p in patterns if not is_protected_pattern(p)]
