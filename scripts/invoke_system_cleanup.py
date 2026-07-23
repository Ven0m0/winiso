#!/usr/bin/env python3
"""invoke_system_cleanup.py - Live-OS disk cleanup helper.

Converted from "Cleanup.cmd" / Invoke-SystemCleanup.ps1. Unlike the other
Windows servicing scripts this targets the CURRENT machine, not a mounted WIM
(temp files, driver installer leftovers, WER/Defender/search caches, log/cache
bloat).

Usage:
    python scripts/invoke_system_cleanup.py [--log-path PATH]
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from win_utils import require_admin, write_success

DRIVE_ROOT_GARBAGE_EXTS = ("bat", "cmd", "txt", "log", "jpg", "jpeg", "tmp", "temp", "bak", "backup", "exe")
WINDIR_GARBAGE_EXTS = ("log", "txt", "bmp", "tmp")
DRIVER_VENDOR_DIRS = ("NVIDIA", "ATI", "AMD", "Dell", "Intel", "HP")


def remove_path_quiet(path: str) -> None:
    """Mirrors PowerShell's Remove-Item -Recurse -Force -ErrorAction SilentlyContinue,
    including trailing "\\*" wildcard semantics."""
    if path.endswith("\\*") or path.endswith("/*"):
        parent = Path(path[:-2])
        if not parent.is_dir():
            return
        for child in parent.iterdir():
            _remove_single(child)
        return
    _remove_single(Path(path))


def _remove_single(target: Path) -> None:
    try:
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists() or target.is_symlink():
            target.unlink(missing_ok=True)
    except OSError:
        pass


def remove_files_by_ext(root: Path, extensions: tuple[str, ...]) -> None:
    if not root.is_dir():
        return
    for ext in extensions:
        for f in root.glob(f"*.{ext}"):
            if f.is_file():
                f.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live-OS disk cleanup helper for Windows servicing.")
    parser.add_argument("--log-path", default=str(Path(tempfile.gettempdir()) / "iso-cmd-cleanup.log"))
    args = parser.parse_args()

    require_admin()

    windir = Path(os.environ["WINDIR"])
    temp = Path(os.environ["TEMP"])
    system_drive = os.environ.get("SystemDrive", "C:")
    program_files = os.environ.get("ProgramFiles", "")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
    all_users_profile = os.environ.get("ALLUSERSPROFILE", "")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    log_path = Path(args.log_path)
    with log_path.open("a", encoding="utf-8") as log:
        _ = log.write(f"Cleanup started: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")

    remove_path_quiet(f"{windir}\\Temp\\*")
    remove_path_quiet(f"{temp}\\*")
    remove_path_quiet(f"{windir}\\Prefetch")
    remove_path_quiet(f"{windir}\\Logs")
    remove_path_quiet(f"{local_appdata}\\cache")

    remove_path_quiet(f"{system_drive}\\Temp")
    remove_files_by_ext(Path(f"{system_drive}\\"), DRIVE_ROOT_GARBAGE_EXTS)

    for vendor in DRIVER_VENDOR_DIRS:
        remove_path_quiet(f"{system_drive}\\{vendor}")

    remove_path_quiet(f"{program_files}\\Nvidia Corporation\\Installer2")
    nvidia_netservice = Path(f"{all_users_profile}\\NVIDIA Corporation\\NetService")
    if nvidia_netservice.is_dir():
        for exe in nvidia_netservice.glob("*.exe"):
            _ = exe.unlink(missing_ok=True)

    remove_path_quiet(f"{system_drive}\\MSOCache")
    remove_path_quiet(f"{system_drive}\\i386")

    remove_path_quiet(f"{system_drive}\\RECYCLER")
    remove_path_quiet(f"{system_drive}\\$Recycle.Bin")

    _ = subprocess.run(
        ["reg.exe", "delete", "HKCU\\SOFTWARE\\Classes\\Local Settings\\Muicache", "/f"],
        capture_output=True,
    )

    remove_path_quiet(f"{all_users_profile}\\Microsoft\\Windows\\WER\\ReportArchive")
    remove_path_quiet(f"{all_users_profile}\\Microsoft\\Windows\\WER\\ReportQueue")

    remove_path_quiet(f"{all_users_profile}\\Microsoft\\Windows Defender\\Scans\\History\\Results\\Quick")
    remove_path_quiet(f"{all_users_profile}\\Microsoft\\Windows Defender\\Scans\\History\\Results\\Resource")

    remove_path_quiet(f"{all_users_profile}\\Microsoft\\Search\\Data\\Temp")

    remove_files_by_ext(windir, WINDIR_GARBAGE_EXTS)
    remove_path_quiet(f"{windir}\\Web\\Wallpaper\\Dell")

    for base in (program_files, program_files_x86):
        if base:
            remove_path_quiet(f"{base}\\NVIDIA Corporation\\Installer")
            remove_path_quiet(f"{base}\\NVIDIA Corporation\\Installer2")
    remove_path_quiet(f"{os.environ.get('ProgramData', '')}\\NVIDIA Corporation\\Downloader")
    remove_path_quiet(f"{os.environ.get('ProgramData', '')}\\NVIDIA\\Downloader")

    remove_path_quiet(f"{windir}\\Logs\\CBS")

    with log_path.open("a", encoding="utf-8") as log:
        _ = log.write(f"Cleanup finished: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")

    write_success(f"Cleanup complete. Log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
