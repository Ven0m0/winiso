#!/usr/bin/env python3
"""repair_wim.py - Repair a mounted install.wim against a known-good reference image.

Converted from "Repair Wim.cmd" / Repair-Wim.ps1. Runs DISM RestoreHealth using
the reference image as the /Source, then re-optimizes it.

Usage:
    python scripts/repair_wim.py --reference-wim PATH [--target-wim PATH]
        [--mount-root PATH] [--reference-mount-root PATH]
"""

import argparse
import subprocess
import sys
from pathlib import Path

from win_utils import invoke_dism, require_admin, write_error_exit, write_step, write_success


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair install.wim against a reference image.")
    parser.add_argument("--reference-wim", required=True)
    parser.add_argument("--target-wim", default=r"C:\ISO\sources\install.wim")
    parser.add_argument("--mount-root", default=r"C:\mnt")
    parser.add_argument("--reference-mount-root", default=r"C:\Repair")
    args = parser.parse_args()

    require_admin()

    reference_wim = Path(args.reference_wim)
    target_wim = Path(args.target_wim)
    mount_root = Path(args.mount_root)
    reference_mount_root = Path(args.reference_mount_root)

    if not reference_wim.is_file():
        write_error_exit(f"Reference WIM not found: {reference_wim}")
    if not target_wim.is_file():
        write_error_exit(f"Target WIM not found: {target_wim}")

    reference_mount_root.mkdir(parents=True, exist_ok=True)
    mount_root.mkdir(parents=True, exist_ok=True)

    write_step("Mounting reference image")
    invoke_dism(["/Mount-Image", f"/ImageFile:{reference_wim}", "/Index:1", f"/MountDir:{reference_mount_root}"])

    write_step("Mounting target image")
    invoke_dism(["/Mount-Image", f"/ImageFile:{target_wim}", "/Index:1", f"/MountDir:{mount_root}"])

    write_step("Running RestoreHealth against reference source")
    invoke_dism(
        [
            f"/Image:{mount_root}",
            "/Cleanup-Image",
            "/RestoreHealth",
            f"/Source:{reference_mount_root / 'windows'}",
        ]
    )

    _ = subprocess.run(["dism.exe", f"/Image:{mount_root}", "/Optimize-ProvisionedAppxPackages"])
    invoke_dism(["/Cleanup-Image", f"/Image={mount_root}", "/StartComponentCleanup", "/ResetBase"])

    write_step("Saving target image")
    invoke_dism(["/Unmount-Image", f"/MountDir:{mount_root}", "/Commit"])

    write_step("Discarding reference mount")
    invoke_dism(["/Unmount-Image", f"/MountDir:{reference_mount_root}", "/Discard"])

    invoke_dism(["/CleanUp-Wim"])

    write_success(f"Repair complete: {target_wim}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
