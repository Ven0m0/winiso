#!/usr/bin/env python3
"""debloat_wim.py - Remove bloatware from Windows install.wim

Usage: python scripts/debloat_wim.py <path_to_install.wim>

Features:
    - Processes ALL indexes in the WIM
    - Offline registry tweaking (Privacy, Performance, AI disabling, Bypasses)
    - Nano mode for aggressive debloating (NANO=1)
    - Case-insensitive matching
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pyutils import log_error, log_info, log_success, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "debloat_list.txt"

PATTERN_RE = re.compile(r"^[a-zA-Z0-9.*_-]+$")

SOFTWARE_HIVE_SCRIPT = """nk Microsoft\\Windows\\CurrentVersion\\CloudContent
cd Microsoft\\Windows\\CurrentVersion\\CloudContent
nv 4 DisableWindowsConsumerFeatures
ed DisableWindowsConsumerFeatures
1
nv 4 DisableCloudOptimizedContent
ed DisableCloudOptimizedContent
1
cd \\
nk Policies\\Microsoft\\Windows\\CloudContent
cd Policies\\Microsoft\\Windows\\CloudContent
nv 4 DisableWindowsConsumerFeatures
ed DisableWindowsConsumerFeatures
1
cd \\
nk Microsoft\\Windows\\CurrentVersion\\DataCollection
cd Microsoft\\Windows\\CurrentVersion\\DataCollection
nv 4 AllowTelemetry
ed AllowTelemetry
0
cd \\
nk Policies\\Microsoft\\Windows\\WindowsCopilot
cd Policies\\Microsoft\\Windows\\WindowsCopilot
nv 4 TurnOffWindowsCopilot
ed TurnOffWindowsCopilot
1
cd \\
nk Microsoft\\Windows\\CurrentVersion\\Explorer
cd Microsoft\\Windows\\CurrentVersion\\Explorer
nv 4 HubMode
ed HubMode
1
q
y
"""

NANO_FONT_DELETES = [
    "Program Files (x86)/Microsoft/Edge",
    "Program Files (x86)/Microsoft/EdgeCore",
    "Program Files (x86)/Microsoft/EdgeUpdate",
    "Windows/Fonts/malgun.ttf",
    "Windows/Fonts/msjh.ttc",
    "Windows/Fonts/msyh.ttc",
    "Windows/Fonts/msyhl.ttc",
    "Windows/Fonts/msyhbd.ttc",
]


def build_system_hive_script() -> str:
    lines: list[str] = []
    for cs in ("ControlSet001", "ControlSet002", "ControlSet003"):
        for service in ("DiagTrack", "dmwappushservice"):
            lines += [f"nk {cs}\\Services\\{service}", f"cd {cs}\\Services\\{service}", "nv 4 Start", "ed Start", "4", "cd \\"]
    lines += ["nk Setup\\LabConfig", "cd Setup\\LabConfig"]
    for value in ("BypassTPMCheck", "BypassSecureBootCheck", "BypassRAMCheck", "BypassStorageCheck", "BypassCPUCheck"):
        lines += [f"nv 4 {value}", f"ed {value}", "1"]
    lines += ["cd \\", "nk Setup\\MoSetup", "cd Setup\\MoSetup"]
    lines += ["nv 4 AllowUpgradesWithUnsupportedTPMOrCPU", "ed AllowUpgradesWithUnsupportedTPMOrCPU", "1"]
    lines += ["q", "y"]
    return "\n".join(lines) + "\n"


def load_patterns() -> list[str]:
    if not CONFIG_FILE.is_file():
        return []
    patterns: list[str] = []
    for raw_line in CONFIG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not PATTERN_RE.match(line):
            log_warn(f"Skipping invalid pattern: {line}")
            continue
        patterns.append(line)
    return patterns


def parse_edition_names(info_output: str) -> dict[int, str]:
    editions: dict[int, str] = {}
    current_index: int | None = None
    for line in info_output.splitlines():
        index_match = re.match(r"^Index:\s+(\d+)$", line)
        if index_match:
            current_index = int(index_match.group(1))
            continue
        name_match = re.match(r"^Name:\s+(.*)$", line)
        if name_match and current_index is not None:
            editions[current_index] = name_match.group(1).rstrip("\r")
            current_index = None
    return editions


def apply_registry_tweaks(wim_file: Path, index: int, temp_reg_dir: Path, index_cmd_lines: list[str]) -> None:
    log_info(f"Applying registry tweaks to index {index}...")

    _ = subprocess.run(
        [
            "wimlib-imagex", "extract", str(wim_file), str(index),
            "/Windows/System32/config/SOFTWARE",
            "/Windows/System32/config/SYSTEM",
            f"--dest-dir={temp_reg_dir}", "--no-acls",
        ],
        capture_output=True,
    )

    software_hive = temp_reg_dir / "SOFTWARE"
    if software_hive.is_file():
        _ = subprocess.run(["chntpw", "-e", str(software_hive)], input=SOFTWARE_HIVE_SCRIPT.encode(), capture_output=True)
        index_cmd_lines.append(f"add '{software_hive}' '/Windows/System32/config/SOFTWARE'")

    system_hive = temp_reg_dir / "SYSTEM"
    if system_hive.is_file():
        _ = subprocess.run(["chntpw", "-e", str(system_hive)], input=build_system_hive_script().encode(), capture_output=True)
        index_cmd_lines.append(f"add '{system_hive}' '/Windows/System32/config/SYSTEM'")


def build_base_delete_commands(patterns: list[str], nano: bool) -> list[str]:
    lines: list[str] = []
    for pattern in patterns:
        lines.append(f'delete --recursive --force "/Program Files/WindowsApps/{pattern}"')
        lines.append(f'delete --recursive --force "/ProgramData/Microsoft/Windows/AppRepository/Packages/{pattern}"')
    if nano:
        for path in NANO_FONT_DELETES:
            lines.append(f'delete --recursive --force "/{path}"')
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        log_error("No WIM file specified.")
        print(f"Usage: {sys.argv[0]} <path_to_install.wim>")
        return 1

    wim_file = Path(sys.argv[1])
    if not wim_file.is_file():
        log_error(f"WIM file not found: {wim_file}")
        return 1

    os.environ["WIMLIB_IMAGEX_IGNORE_CASE"] = "1"
    nano = os.environ.get("NANO", "0") == "1"

    info_result = subprocess.run(["wimlib-imagex", "info", str(wim_file)], capture_output=True, text=True)
    info_output = info_result.stdout if info_result.returncode == 0 else ""
    image_count = info_output.count("\nIndex:") + (1 if info_output.startswith("Index:") else 0)
    edition_names = parse_edition_names(info_output)

    patterns = load_patterns()
    base_delete_commands = build_base_delete_commands(patterns, nano)

    for index in range(1, image_count + 1):
        edition = edition_names.get(index, "Unknown")
        log_info(f"Processing index {index}: {edition}")

        index_cmd_lines: list[str] = []
        if patterns or nano:
            index_cmd_lines.extend(base_delete_commands)

        with tempfile.TemporaryDirectory() as temp_reg_dir:
            apply_registry_tweaks(wim_file, index, Path(temp_reg_dir), index_cmd_lines)

            if nano:
                log_info(f"Adding WinSxS slimming commands for index {index}...")
                index_cmd_lines += [
                    'delete --recursive --force "/Windows/WinSxS/Backup"',
                    'delete --recursive --force "/Windows/WinSxS/ManifestCache"',
                    'delete --recursive --force "/Windows/WinSxS/Temp"',
                ]

            if index_cmd_lines:
                update_result = subprocess.run(
                    ["wimlib-imagex", "update", str(wim_file), str(index)],
                    input="\n".join(index_cmd_lines) + "\n",
                    capture_output=True,
                    text=True,
                )
                for line in update_result.stdout.splitlines()[:20]:
                    if "does not exist" not in line:
                        print(line)

    log_info("Optimizing WIM...")
    optimize_result = subprocess.run(["wimlib-imagex", "optimize", str(wim_file), "--recompress"])
    if optimize_result.returncode != 0:
        log_warn("Optimization returned non-zero")

    size_bytes = wim_file.stat().st_size
    log_success(f"WIM processing complete. Size: {size_bytes / (1024**3):.2f}G")
    return 0


if __name__ == "__main__":
    sys.exit(main())
