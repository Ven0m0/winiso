#!/usr/bin/env python3
"""validate_prereqs.py - Validate prerequisites before building ISO"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from pyutils import (
    REQUIRED_TOOLS,
    check_iso_tool,
    check_required_tools,
    log_error,
    log_info,
    log_success,
    log_warn,
)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

PIPELINE_SCRIPTS = ["build.py", "custom_convert.sh", "debloat_wim.py", "setup_env.py"]


def main() -> int:
    errors = 0
    warnings = 0

    log_info("Checking required tools...")
    errors += check_required_tools(REQUIRED_TOOLS)
    if not check_iso_tool():
        log_error("Neither genisoimage nor mkisofs found. Run 'make deps' to install.")
        errors += 1

    print()
    log_info("Checking directory structure...")

    uup_dir = PROJECT_ROOT / "uup_files"
    if uup_dir.is_dir():
        log_success("uup_files directory exists")
    else:
        log_error(f"uup_files directory not found at: {uup_dir}")
        errors += 1

    output_dir = PROJECT_ROOT / "output"
    if output_dir.is_dir():
        log_success("output directory exists")
    else:
        log_warn("output directory not found, will be created")
        output_dir.mkdir(parents=True, exist_ok=True)
        warnings += 1

    config_dir = PROJECT_ROOT / "config"
    if config_dir.is_dir():
        log_success("config directory exists")
    else:
        log_error(f"config directory not found at: {config_dir}")
        errors += 1

    print()
    log_info("Checking for UUP files...")

    cab_count = len(list(uup_dir.glob("*.cab"))) if uup_dir.is_dir() else 0
    esd_count = len(list(uup_dir.glob("*.[eE][sS][dD]"))) if uup_dir.is_dir() else 0
    if cab_count == 0 and esd_count == 0:
        log_error(f"No UUP files (.cab or .esd) found in {uup_dir}")
        print()
        print("To get UUP files:")
        print("  1. Visit https://uupdump.net")
        print("  2. Select your desired Windows 11 build")
        print("  3. Download the UUP package")
        print(f"  4. Extract all files to: {uup_dir}")
        print()
        errors += 1
    else:
        log_success(f"Found {cab_count} CAB files and {esd_count} ESD files")

    print()
    log_info("Checking configuration files...")

    debloat_list = config_dir / "debloat_list.txt"
    if debloat_list.is_file():
        log_success("debloat_list.txt found")
        lines = debloat_list.read_text(encoding="utf-8", errors="replace").splitlines()
        pattern_count = sum(
            1 for line in lines if line.strip() and not line.startswith("#")
        )
        log_info(f"  → {pattern_count} debloat patterns configured")
    else:
        log_warn("debloat_list.txt not found - no apps will be removed")
        warnings += 1

    autounattend = config_dir / "autounattend.xml"
    if autounattend.is_file():
        log_success("autounattend.xml found")
        xmllint = shutil.which("xmllint")
        if xmllint:
            result = subprocess.run(
                [xmllint, "--noout", str(autounattend)],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                log_error(
                    "autounattend.xml failed XML validation - run 'xmllint --noout config/autounattend.xml' for details"
                )
                errors += 1
            else:
                log_success("  → autounattend.xml is valid XML")
        else:
            log_warn("xmllint not found - skipping XML validation")
            warnings += 1
    else:
        log_warn("autounattend.xml not found - installation will require manual setup")
        log_info(
            "  → Generate one at: https://schneegans.de/windows/unattend-generator/"
        )
        warnings += 1

    oem_dir = config_dir / "oem"
    if oem_dir.is_dir():
        log_success("OEM scripts directory found")
        if (oem_dir / "SetupComplete.cmd").is_file():
            log_success("  → SetupComplete.cmd found")
        else:
            log_warn(
                "  → SetupComplete.cmd not found - no first-boot tweaks will be applied"
            )
            warnings += 1
    else:
        log_warn(
            "OEM scripts directory not found - no first-boot tweaks will be applied"
        )
        warnings += 1

    print()
    log_info("Checking build scripts...")

    for script in PIPELINE_SCRIPTS:
        script_path = PROJECT_ROOT / "scripts" / script
        if script_path.is_file():
            log_success(f"{script} exists")
        else:
            log_error(f"{script} not found at: {script_path}")
            errors += 1

    print()
    log_info("Environment configuration...")
    log_info(
        f"TARGET_EDITION: {os.environ.get('TARGET_EDITION', 'ProfessionalWorkstation (default)')}"
    )
    log_info(
        f"FALLBACK_EDITION: {os.environ.get('FALLBACK_EDITION', 'Professional (default)')}"
    )
    log_info(
        f"PAUSE_FOR_WINDOWS_STAGE: {os.environ.get('PAUSE_FOR_WINDOWS_STAGE', '0 (disabled)')}"
    )

    print()
    log_info("Checking available disk space...")
    available_gb = shutil.disk_usage(PROJECT_ROOT).free // (1024**3)
    if available_gb < 20:
        log_warn(f"Low disk space: {available_gb}GB available (20GB+ recommended)")
        warnings += 1
    else:
        log_success(f"Sufficient disk space: {available_gb}GB available")

    print()
    print("==============================================")
    if errors == 0 and warnings == 0:
        log_success("All prerequisite checks passed!")
        log_success("You can proceed with: make build")
    elif errors == 0:
        log_warn(f"Prerequisite checks passed with {warnings} warning(s)")
        log_info("Build can proceed, but review warnings above")
    else:
        log_error("Prerequisite validation failed!")
        log_error(f"Errors: {errors}, Warnings: {warnings}")
        print()
        print("Please fix the errors above before running 'make build'")
        print("==============================================")
        return 1
    print("==============================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
