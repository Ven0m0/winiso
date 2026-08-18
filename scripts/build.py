#!/usr/bin/env python3
"""build.py - Orchestrator for Debloated Windows 11 ISO

This script orchestrates the UUP to ISO conversion with debloating.

Environment Variables:
    TARGET_EDITION          - Preferred edition (default: ProfessionalWorkstation)
    FALLBACK_EDITION        - Fallback edition (default: Professional)
    PROFILE                 - Named profile from config/profiles.json (sets edition)
    PAUSE_FOR_WINDOWS_STAGE - Set to 1 to pause for Windows servicing

Usage:
    python scripts/build.py                    # Normal build
    python scripts/build.py --profile minimal  # Build using a named profile
    python scripts/build.py --edition Core     # Override the target edition directly
    PAUSE_FOR_WINDOWS_STAGE=1 python scripts/build.py  # Pause for Windows servicing
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import orjson
from pyutils import log_error, log_info, log_success

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
UUP_DIR = PROJECT_ROOT / "uup_files"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROFILES_FILE = PROJECT_ROOT / "config" / "profiles.json"


def load_profile(name: str) -> dict[str, Any] | None:
    if not PROFILES_FILE.is_file():
        return None
    try:
        data = orjson.loads(PROFILES_FILE.read_bytes())
    except OSError, ValueError:
        return None
    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    return profiles.get(name) if isinstance(profiles, dict) else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a debloated Windows 11 ISO.")
    parser.add_argument(
        "--profile",
        default=os.environ.get("PROFILE"),
        help="Named build profile from config/profiles.json (sets the target edition)",
    )
    parser.add_argument(
        "--edition",
        default=None,
        help="Override TARGET_EDITION (takes precedence over --profile and the env var)",
    )
    return parser.parse_args()


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
        size /= 1024
    return f"{size:.1f}P"


def main() -> int:
    args = parse_args()

    log_info("Running prerequisite validation...")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_prereqs.py")], check=False
    )
    if result.returncode != 0:
        log_error("Prerequisite validation failed. Please fix errors and try again.")
        return 1
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cab_files = list(UUP_DIR.glob("*.cab"))
    esd_files = list(UUP_DIR.glob("*.[eE][sS][dD]"))
    if not cab_files and not esd_files:
        log_error(f"No UUP files (.cab or .esd) found in {UUP_DIR}")
        print()
        print("To get UUP files:")
        print("  1. Visit https://uupdump.net and select your Windows 11 build")
        print("  2. Download the UUP package")
        print(f"  3. Extract or move files to: {UUP_DIR}")
        print()
        return 1

    target_edition = os.environ.get("TARGET_EDITION", "ProfessionalWorkstation")
    fallback_edition = os.environ.get("FALLBACK_EDITION", "Professional")

    if args.profile:
        profile = load_profile(args.profile)
        if profile is None:
            log_error(f"Unknown profile: {args.profile}")
            return 1
        log_info(f"Using profile: {args.profile}")
        target_edition = profile.get("edition", target_edition)

    if args.edition:
        target_edition = args.edition

    log_info("Starting Build Process...")
    log_info(f"Source: {UUP_DIR}")
    log_info(f"Output: {OUTPUT_DIR}")
    log_info(f"Target Edition: {target_edition}")
    log_info(f"Fallback Edition: {fallback_edition}")
    print()

    log_info("Cleaning previous build artifacts...")
    shutil.rmtree(SCRIPT_DIR / "ISODIR", ignore_errors=True)

    env = os.environ.copy()
    env["TARGET_EDITION"] = target_edition
    env["FALLBACK_EDITION"] = fallback_edition
    env["PAUSE_FOR_WINDOWS_STAGE"] = os.environ.get("PAUSE_FOR_WINDOWS_STAGE", "0")
    env["NANO"] = os.environ.get("NANO", "0")
    env["WIMLIB_IMAGEX_IGNORE_CASE"] = "1"
    # debloat_wim.py now imports orjson; the converter's DEBLOAT HOOK must run
    # it with the same interpreter (venv) that build.py itself is running under.
    env["PYTHON"] = sys.executable

    # custom_convert.sh is upstream-derived bash and stays as-is; run via bash.
    # Usage: custom_convert.sh [compression] [uups_directory] [create_virtual_editions]
    # We force 'wim' compression because 'esd' cannot be reliably modified.
    log_info("Running UUP converter with debloating...")
    result = subprocess.run(
        ["bash", str(SCRIPT_DIR / "custom_convert.sh"), "wim", str(UUP_DIR), "0"],
        cwd=SCRIPT_DIR,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        log_error("Build failed during conversion.")
        return 1

    iso_files = list(SCRIPT_DIR.glob("*.iso"))
    if not iso_files:
        log_error("ISO file not found after conversion.")
        log_error("Check for errors above. The converter may have failed.")
        return 1

    iso_file = iso_files[0]
    log_success(f"ISO created: {iso_file.name}")

    log_info(f"Moving {iso_file.name} to {OUTPUT_DIR}...")
    dest = OUTPUT_DIR / iso_file.name
    _ = shutil.move(str(iso_file), str(dest))

    final_size = human_size(dest.stat().st_size)

    print()
    log_success("======================================")
    log_success("Build Complete!")
    log_success("======================================")
    print(f"  ISO: {dest}")
    print(f"  Size: {final_size}")
    print()

    log_info("Cleaning up build artifacts...")
    shutil.rmtree(SCRIPT_DIR / "ISODIR", ignore_errors=True)

    log_success("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
