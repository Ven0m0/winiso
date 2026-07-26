"""Shared helpers for the Windows servicing scripts (DISM/oscdimg wrappers)."""

import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def write_step(message: str) -> None:
    print(f"[+] {message}")


def write_success(message: str) -> None:
    print(f"[OK] {message}")


def write_error_exit(message: str) -> None:
    print(f"[ERROR] {message}")
    sys.exit(1)


def require_admin() -> None:
    if sys.platform != "win32":
        write_error_exit("This script only runs on Windows.")
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        write_error_exit("This script must be run as Administrator.")


def invoke_dism(args: list[str]) -> None:
    result = subprocess.run(["dism.exe", *args], check=False)
    if result.returncode != 0:
        write_error_exit(
            f"dism {' '.join(args)} failed with exit code {result.returncode}"
        )


def find_oscdimg() -> str:
    userprofile = os.environ.get("USERPROFILE", "")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
    candidates = [
        Path(userprofile) / "AppData/Local/Microsoft/WinGet/Links/oscdimg.exe",
        Path(
            r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
        ),
        Path(
            r"C:\Program Files (x86)\Windows Kits\11\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
        ),
        Path(program_files_x86)
        / "Windows Kits/10/Deployment Tools/amd64/Oscdimg/oscdimg.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    write_error_exit(
        "oscdimg.exe not found. Install Windows ADK Deployment Tools or winget it."
    )
    raise AssertionError("unreachable")


def safe_remove_directory(path: str | Path) -> None:
    target = Path(path)
    if not target.exists():
        return
    try:
        shutil.rmtree(target)
    except OSError:
        print("      Retrying cleanup...")
        time.sleep(2)
        shutil.rmtree(target, ignore_errors=True)
