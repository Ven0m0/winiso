#!/usr/bin/env python3
"""setup_env.py - Install dependencies for Debloated Windows 11 ISO Builder"""

import shutil
import subprocess
import sys

from pyutils import (
    REQUIRED_TOOLS,
    check_iso_tool,
    check_tool,
    log_error,
    log_info,
    log_success,
)

PACKAGE_MANAGERS = {
    "pacman": (
        [
            "pacman",
            "-S",
            "--needed",
            "aria2",
            "cabextract",
            "wimlib",
            "chntpw",
            "cdrtools",
        ],
        "Arch Linux (pacman)",
    ),
    "apt": (
        [
            "apt",
            "install",
            "-y",
            "aria2",
            "cabextract",
            "wimtools",
            "chntpw",
            "genisoimage",
        ],
        "Debian/Ubuntu (apt)",
    ),
    "dnf": (
        [
            "dnf",
            "install",
            "-y",
            "aria2",
            "cabextract",
            "wimlib-utils",
            "chntpw",
            "genisoimage",
        ],
        "Fedora (dnf)",
    ),
}


def main() -> int:
    log_info("Checking and installing dependencies...")

    if sys.platform == "win32":
        log_error(
            "setup_env.py installs Linux system packages and is not applicable on Windows."
        )
        log_error("Use mise (mise run install-deps) or winget for Windows tooling.")
        return 1

    import os

    if os.geteuid() != 0:
        log_error("This script must run as root to install system packages.")
        log_error("Re-run as root or via your orchestrator with elevated privileges.")
        return 1

    manager = next((m for m in ("pacman", "apt", "dnf") if shutil.which(m)), None)
    if manager is None:
        log_error("Unsupported package manager. Please install manually:")
        print("  - aria2 (download acceleration)")
        print("  - cabextract (Windows cabinet extraction)")
        print("  - wimlib / wimtools (WIM manipulation)")
        print("  - chntpw (Windows registry editing)")
        print("  - genisoimage / cdrtools (ISO creation)")
        return 1

    cmd, label = PACKAGE_MANAGERS[manager]
    log_info(f"Detected {label}")
    if manager == "apt":
        _ = subprocess.run(["apt", "update"], check=True)
    _ = subprocess.run(cmd, check=True)

    log_info("Verifying tool availability...")
    missing_tools = [tool for tool in REQUIRED_TOOLS if not check_tool(tool)]
    if not check_iso_tool():
        missing_tools.append("genisoimage/mkisofs")

    if missing_tools:
        log_error(f"Missing tools: {', '.join(missing_tools)}")
        log_error("Please install them manually and re-run.")
        return 1

    print()
    log_success("All dependencies are installed and verified!")
    log_info("You can now run: make build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
