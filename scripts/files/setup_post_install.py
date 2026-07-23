#!/usr/bin/env python3
"""setup_post_install.py - First-logon configuration for images built by this pipeline.

Converted from Setup-PostInstall.ps1. Disables hibernate, strips 8.3 filenames
on fixed volumes, then reboots (unless --no-reboot) and deletes itself.

Usage:
    python setup_post_install.py [--no-reboot]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def fixed_drive_letters() -> list[str]:
    result = subprocess.run(
        ["wmic", "logicaldisk", "where", "drivetype=3", "get", "deviceid"],
        capture_output=True,
        text=True,
    )
    letters: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and line != "DeviceID" and line.endswith(":"):
            letters.append(line)
    return letters


def main() -> int:
    parser = argparse.ArgumentParser(description="First-logon configuration.")
    parser.add_argument("--no-reboot", action="store_true")
    args = parser.parse_args()

    print()
    print("=== First Logon Configuration ===")
    print()

    print("[+] Disabling Hibernate...")
    _ = subprocess.run(["powercfg", "/hibernate", "off"])
    print("[OK] Hibernate disabled")

    print("[+] Stripping 8.3 filenames (this may take a while)...")
    for drive in fixed_drive_letters():
        print(f"    Processing {drive}...")
        _ = subprocess.run(["fsutil", "8dot3name", "strip", "/d", drive, "/s"], capture_output=True)
    print("[OK] 8.3 filenames stripped")

    print()
    print("=== Configuration Complete ===")
    print()

    if not args.no_reboot:
        print("System will reboot in 10 seconds...")
        time.sleep(10)
        _ = subprocess.run(["shutdown", "/r", "/t", "0", "/f"])

    Path(__file__).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
