"""Build selection config: named profiles (config/profiles.json) and the pinned build (.uup-pin.json)."""

from pathlib import Path
from typing import Any

import orjson
from pyutils import log_error, log_success, log_warn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_FILE = PROJECT_ROOT / "config" / "profiles.json"
PIN_FILE = PROJECT_ROOT / ".uup-pin.json"


def get_profiles() -> dict[str, dict[str, Any]]:
    """Load build profiles from config/profiles.json (the single source of truth)."""
    try:
        data = orjson.loads(PROFILES_FILE.read_bytes())
    except (orjson.JSONDecodeError, OSError) as e:
        log_warn(f"Failed to load {PROFILES_FILE}: {e}")
        return {}
    profiles = data.get("profiles") if isinstance(data, dict) else None
    return profiles if isinstance(profiles, dict) else {}


def get_pinned_build() -> dict[str, Any] | None:
    """Load pinned build configuration from .uup-pin.json in the project root."""
    pin_path = PIN_FILE

    if not pin_path.exists():
        return None

    try:
        data = orjson.loads(pin_path.read_bytes())
        if isinstance(data, dict) and "build_id" in data:
            return data
        log_warn("Invalid pin file: missing 'build_id'")
        return None
    except (orjson.JSONDecodeError, OSError) as e:
        log_warn(f"Failed to read pin file: {e}")
        return None


def save_pinned_build(
    build_id: str,
    title: str | None = None,
    edition: str | None = None,
) -> bool:
    """Save a build as the pinned version for reproducibility."""
    pin_path = PIN_FILE

    data: dict[str, Any] = {"build_id": build_id}
    if title:
        data["title"] = title
    if edition:
        data["edition"] = edition

    try:
        pin_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        log_success(f"Pinned build {build_id} to {pin_path}")
        return True
    except OSError as e:
        log_error(f"Failed to write pin file: {e}")
        return False


def get_profile(name: str) -> dict[str, Any] | None:
    """Get a specific build profile by name."""
    profiles = get_profiles()
    return profiles.get(name)
