#!/usr/bin/env python3
"""remove_short_names.py - Strip 8.3 short filenames from a staged ISO and its WIMs.

Converted from Remove-ShortNames.ps1, itself a consolidation of "8.3 strip all.cmd",
"Remove Shortnames.cmd", and "Remove Shortnames -install.cmd":
    - default (no flags)  : install.wim + boot.wim   (was "Remove Shortnames.cmd")
    - --include-winre      : also reprocess Winre.wim  (was "8.3 strip all.cmd")
    - --install-only        : install.wim only, drop leftover *.LOG (was "...-install.cmd")

Usage:
    python scripts/remove_short_names.py [--iso-root PATH] [--mount-root PATH]
        [--install-only] [--include-winre]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from win_utils import invoke_dism, require_admin, write_step, write_success


def strip_8dot3(path: Path) -> None:
    write_step(f"Stripping 8.3 short names under {path}")
    _ = subprocess.run(
        ["fsutil", "8dot3name", "strip", "/f", "/s", str(path)],
        capture_output=True,
        check=False,
    )


def clean_mounted_image(mount_dir: Path) -> None:
    _ = subprocess.run(
        ["dism.exe", f"/Image:{mount_dir}", "/Optimize-ProvisionedAppxPackages"],
        capture_output=True,
        check=False,
    )
    invoke_dism(
        [
            "/Cleanup-Image",
            f"/Image={mount_dir}",
            "/StartComponentCleanup",
            "/ResetBase",
        ]
    )


def export_wim(source: Path, destination: Path) -> None:
    invoke_dism(
        [
            "/Export-Image",
            f"/SourceImageFile:{source}",
            "/SourceIndex:1",
            f"/DestinationImageFile:{destination}",
            "/Compress:max",
            "/CheckIntegrity",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strip 8.3 short filenames from a staged ISO and its WIMs."
    )
    parser.add_argument("--iso-root", default=r"C:\ISO")
    parser.add_argument("--mount-root", default=r"C:\mnt")
    parser.add_argument("--install-only", action="store_true")
    parser.add_argument("--include-winre", action="store_true")
    args = parser.parse_args()

    require_admin()

    iso_root = Path(args.iso_root)
    mount_root = Path(args.mount_root)

    invoke_dism(["/CleanUp-Wim"])
    strip_8dot3(iso_root)

    install_wim = iso_root / "sources" / "install.wim"
    install_mount = mount_root / "install"
    install_mount.mkdir(parents=True, exist_ok=True)

    write_step("Mounting install.wim")
    invoke_dism(
        [
            "/Mount-Image",
            f"/ImageFile:{install_wim}",
            "/Index:1",
            f"/MountDir:{install_mount}",
        ]
    )
    strip_8dot3(install_mount)
    clean_mounted_image(install_mount)

    if args.install_only:
        write_step("Removing leftover *.LOG files")
        for log_file in install_mount.rglob("*LOG"):
            log_file.unlink(missing_ok=True)

    if args.include_winre:
        winre_wim = install_mount / "Windows" / "System32" / "Recovery" / "Winre.wim"
        winre_mount = mount_root / "winre"
        winre_mount.mkdir(parents=True, exist_ok=True)

        write_step("Mounting Winre.wim")
        invoke_dism(
            [
                "/Mount-Image",
                f"/ImageFile:{winre_wim}",
                "/Index:1",
                f"/MountDir:{winre_mount}",
            ]
        )
        strip_8dot3(winre_mount)
        invoke_dism(
            [
                "/Cleanup-Image",
                f"/Image={winre_mount}",
                "/StartComponentCleanup",
                "/ResetBase",
            ]
        )
        invoke_dism(["/Unmount-Image", f"/MountDir:{winre_mount}", "/Commit"])

        winre_cleaned = (
            install_mount / "Windows" / "System32" / "Recovery" / "Winre_cleaned.wim"
        )
        export_wim(winre_wim, winre_cleaned)

        time.sleep(1)
        winre_wim.unlink()
        time.sleep(2)
        winre_cleaned.rename(winre_wim)
        time.sleep(1)
        write_success("Winre.wim reprocessed")

    invoke_dism(["/Unmount-Image", f"/MountDir:{install_mount}", "/Commit"])

    install_cleaned = iso_root / "sources" / "install_cleaned.wim"
    export_wim(install_wim, install_cleaned)
    invoke_dism(["/CleanUp-Wim"])
    write_success(f"install.wim processed -> {install_cleaned}")

    if not args.install_only:
        boot_wim = iso_root / "sources" / "boot.wim"
        boot_mount = mount_root / "boot"
        boot_mount.mkdir(parents=True, exist_ok=True)

        write_step("Mounting boot.wim")
        invoke_dism(
            [
                "/Mount-Image",
                f"/ImageFile:{boot_wim}",
                "/Index:1",
                f"/MountDir:{boot_mount}",
            ]
        )
        strip_8dot3(boot_mount)
        invoke_dism(
            [
                "/Cleanup-Image",
                f"/Image={boot_mount}",
                "/StartComponentCleanup",
                "/ResetBase",
            ]
        )
        invoke_dism(["/Unmount-Image", f"/MountDir:{boot_mount}", "/Commit"])

        boot_cleaned = iso_root / "sources" / "boot_cleaned.wim"
        export_wim(boot_wim, boot_cleaned)
        invoke_dism(["/CleanUp-Wim"])
        write_success(f"boot.wim processed -> {boot_cleaned}")

    write_success("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
