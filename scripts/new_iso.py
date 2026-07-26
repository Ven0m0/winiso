#!/usr/bin/env python3
"""new_iso.py - Build a bootable UEFI+BIOS ISO from a staged directory using oscdimg.exe.

Converted from "ISO.cmd" / New-Iso.ps1.

Usage:
    python scripts/new_iso.py [--iso-root PATH] [--output-iso PATH]
"""

import argparse
import subprocess
import sys
from pathlib import Path

from win_utils import find_oscdimg, write_error_exit, write_success


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a bootable ISO from a staged directory via oscdimg."
    )
    parser.add_argument("--iso-root", default=r"C:\ISO")
    parser.add_argument("--output-iso", default=r"C:\Win.iso")
    args = parser.parse_args()

    iso_root = Path(args.iso_root)
    if not iso_root.is_dir():
        write_error_exit(f"ISO root not found: {iso_root}")

    oscdimg_path = find_oscdimg()
    etfsboot = iso_root / "boot" / "etfsboot.com"
    efisys = iso_root / "efi" / "Microsoft" / "boot" / "efisys.bin"

    if not etfsboot.is_file():
        write_error_exit(f"etfsboot.com not found under {iso_root}")
    if not efisys.is_file():
        write_error_exit(f"efisys.bin not found under {iso_root}")

    boot_data = f"2#p0,e,b{etfsboot}#pEF,e,b{efisys}"
    result = subprocess.run(
        [
            oscdimg_path,
            "-m",
            "-o",
            "-u2",
            "-udfver102",
            f"-bootdata:{boot_data}",
            str(iso_root),
            args.output_iso,
        ],
        check=False,
    )
    if result.returncode != 0:
        write_error_exit(f"oscdimg failed with exit code {result.returncode}")

    write_success(f"ISO created: {args.output_iso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
