#!/usr/bin/env python3
"""apply_image_settings.py - Extract a Windows ISO, inject the unattend answer file
and post-install script, optionally debloat, and rebuild the ISO.

Converted from Apply-ImageSettings.ps1. Uses dism.exe for all image mount/servicing
operations (no PowerShell DISM module dependency) and PowerShell's Mount-DiskImage
(built into Windows) instead of the original's Shell.Application COM extraction hack.

Usage:
    python scripts/apply_image_settings.py --iso-path <path> [--skip-iso]
    python scripts/apply_image_settings.py --extract-path <path>
    python scripts/apply_image_settings.py --debloat --mount-dir <path> --wim-path <path>
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import win_config
from win_utils import (
    find_oscdimg,
    invoke_dism,
    require_admin,
    safe_remove_directory,
    write_error_exit,
    write_step,
    write_success,
)

HIGH_PERFORMANCE_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

# ponytail: on Modern Standby hardware this scheme is hidden/absent and Windows falls back to
# Balanced (SetupComplete.cmd's runtime "powercfg /setactive" hits the same wall); upgrade to
# "powercfg /duplicatescheme" if that ever needs handling.
OFFLINE_SYSTEM_VALUES = (
    (
        "ControlSet001\\Control\\FileSystem",
        "NtfsDisable8dot3NameCreation",
        "REG_DWORD",
        "1",
    ),
    (
        "ControlSet001\\Control\\Power\\User\\PowerSchemes",
        "ActivePowerScheme",
        "REG_SZ",
        HIGH_PERFORMANCE_GUID,
    ),
)

EDGE_PATHS = (
    "Program Files (x86)/Microsoft/Edge",
    "Program Files (x86)/Microsoft/EdgeCore",
    "Program Files (x86)/Microsoft/EdgeUpdate",
)

PACKAGES_TO_REMOVE = (
    "Microsoft-Windows-Hello-Face-Package*",
    "Microsoft-Windows-MSPaint-FoD-Package*",
    "Microsoft-Windows-Notepad-FoD-Package*",
    "Microsoft-Windows-PowerShell-ISE-FOD-Package*",
    "Microsoft-Windows-SnippingTool-FoD-Package*",
    "Microsoft-Windows-StepsRecorder-Package*",
    "Microsoft-Windows-TabletPCMath-Package*",
    "Microsoft-Windows-Wallpaper-Content-Extended-FoD-Package*",
)

FEATURES_TO_DISABLE = (
    "MicrosoftWindowsPowerShellV2Root",
    "MicrosoftWindowsPowerShellV2",
    "WorkFolders-Client",
    "SmbDirect",
    "Printing-PrintToPDFServices-Features",
    "Recall",
    "Microsoft-RemoteDesktopConnection",
    "Printing-Foundation-Features",
    "Printing-Foundation-InternetPrinting-Client",
)
FEATURES_TO_ENABLE = ("DirectPlay",)

APPX_TO_REMOVE = (
    "Clipchamp.Clipchamp*",
    "Microsoft.549981C3F5F10*",
    "Microsoft.BingNews*",
    "Microsoft.BingWeather*",
    "Microsoft.GamingApp*",
    "Microsoft.GetHelp*",
    "Microsoft.Getstarted*",
    "Microsoft.MicrosoftOfficeHub*",
    "Microsoft.MicrosoftSolitaireCollection*",
    "Microsoft.MicrosoftStickyNotes*",
    "Microsoft.Paint*",
    "Microsoft.People*",
    "Microsoft.PowerAutomateDesktop*",
    "Microsoft.ScreenSketch*",
    "Microsoft.SecHealthUI*",
    "Microsoft.StorePurchaseApp*",
    "Microsoft.Todos*",
    "Microsoft.Windows.Photos*",
    "Microsoft.WindowsAlarms*",
    "Microsoft.WindowsCalculator*",
    "Microsoft.WindowsCamera*",
    "microsoft.windowscommunicationsapps*",
    "Microsoft.WindowsFeedbackHub*",
    "Microsoft.WindowsMaps*",
    "Microsoft.WindowsNotepad*",
    "Microsoft.WindowsSoundRecorder*",
    "Microsoft.WindowsStore*",
    "Microsoft.Xbox.TCUI*",
    "Microsoft.XboxGameOverlay*",
    "Microsoft.XboxGamingOverlay*",
    "Microsoft.XboxIdentityProvider*",
    "Microsoft.XboxSpeechToTextOverlay*",
    "Microsoft.YourPhone*",
    "Microsoft.ZuneMusic*",
    "Microsoft.ZuneVideo*",
    "MicrosoftCorporationII.QuickAssist*",
    "MicrosoftWindows.Client.WebExperience*",
)

CAPABILITIES_TO_REMOVE = (
    "App.StepsRecorder*",
    "Browser.InternetExplorer*",
    "Hello.Face*",
    "MathRecognizer*",
    "Microsoft.Wallpapers.Extended*",
    "Microsoft.Windows.MSPaint*",
    "Microsoft.Windows.Notepad*",
    "Microsoft.Windows.PowerShell.ISE*",
    "Microsoft.Windows.SnippingTool*",
    "Microsoft.Windows.Wifi.Client*",
    "OneCoreUAP.OneSync*",
)


def dism_get_names(mount_dir: Path, args: list[str], identity_key: str) -> list[str]:
    """Parses "<identity_key> : Name" / "State : Installed" blocks from dism.exe output."""
    result = subprocess.run(
        ["dism.exe", f"/Image:{mount_dir}", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    names: list[str] = []
    current: str | None = None
    for line in result.stdout.splitlines():
        identity_match = re.match(
            rf"^{re.escape(identity_key)}\s*:\s*(.+)$", line.strip()
        )
        if identity_match:
            current = identity_match.group(1).strip()
            continue
        state_match = re.match(r"^State\s*:\s*(.+)$", line.strip())
        if state_match and current is not None:
            if state_match.group(1).strip().lower() == "installed":
                names.append(current)
            current = None
    return names


def matches_any(name: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        if re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), name, re.IGNORECASE):
            return pattern
    return None


def remove_edge(mount_dir: Path) -> None:
    print("Removing Microsoft Edge...")
    for rel in EDGE_PATHS:
        shutil.rmtree(mount_dir / rel, ignore_errors=True)


def remove_packages(mount_dir: Path) -> None:
    print("Removing Windows Packages...")
    for name in dism_get_names(mount_dir, ["/Get-Packages"], "Package Identity"):
        if matches_any(name, PACKAGES_TO_REMOVE):
            _ = subprocess.run(
                [
                    "dism.exe",
                    f"/Image:{mount_dir}",
                    "/Remove-Package",
                    f"/PackageName:{name}",
                    "/NoRestart",
                ],
                capture_output=True,
                check=False,
            )


def set_features(mount_dir: Path) -> None:
    print("Configuring Optional Features...")
    for feature in FEATURES_TO_DISABLE:
        _ = subprocess.run(
            [
                "dism.exe",
                f"/Image:{mount_dir}",
                "/Disable-Feature",
                f"/FeatureName:{feature}",
                "/NoRestart",
            ],
            capture_output=True,
            check=False,
        )
    for feature in FEATURES_TO_ENABLE:
        _ = subprocess.run(
            [
                "dism.exe",
                f"/Image:{mount_dir}",
                "/Enable-Feature",
                f"/FeatureName:{feature}",
                "/All",
                "/NoRestart",
            ],
            capture_output=True,
            check=False,
        )


def remove_appx_packages(mount_dir: Path) -> None:
    print("Removing AppX Packages...")
    for name in dism_get_names(
        mount_dir, ["/Get-ProvisionedAppxPackages"], "DisplayName"
    ):
        if matches_any(name, APPX_TO_REMOVE):
            _ = subprocess.run(
                [
                    "dism.exe",
                    f"/Image:{mount_dir}",
                    "/Remove-ProvisionedAppxPackage",
                    f"/PackageName:{name}",
                ],
                capture_output=True,
                check=False,
            )


def remove_capabilities(mount_dir: Path) -> None:
    print("Removing Capabilities...")
    for name in dism_get_names(mount_dir, ["/Get-Capabilities"], "Capability Identity"):
        if matches_any(name, CAPABILITIES_TO_REMOVE):
            _ = subprocess.run(
                [
                    "dism.exe",
                    f"/Image:{mount_dir}",
                    "/Remove-Capability",
                    f"/CapabilityName:{name}",
                ],
                capture_output=True,
                check=False,
            )


def mount_iso(iso_path: Path) -> str:
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Mount-DiskImage -ImagePath '{iso_path}' -PassThru | Get-Volume).DriveLetter",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    drive_letter = result.stdout.strip()
    if not drive_letter:
        write_error_exit(f"Failed to mount ISO: {iso_path}")
    return f"{drive_letter}:\\"


def dismount_iso(iso_path: Path) -> None:
    _ = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"Dismount-DiskImage -ImagePath '{iso_path}'",
        ],
        capture_output=True,
        check=False,
    )


def run_debloat(mount_dir: Path, wim_path: Path) -> int:
    if not wim_path.is_file():
        write_error_exit(f"WIM file not found: {wim_path}")
    mount_dir.mkdir(parents=True, exist_ok=True)

    print("Mounting Windows Image...")
    invoke_dism(
        ["/Mount-Image", f"/ImageFile:{wim_path}", "/Index:1", f"/MountDir:{mount_dir}"]
    )

    try:
        remove_edge(mount_dir)
        remove_packages(mount_dir)
        set_features(mount_dir)
        remove_appx_packages(mount_dir)
        remove_capabilities(mount_dir)
        print("Customization complete.")
    finally:
        print("Dismounting and saving image...")
        invoke_dism(["/Unmount-Image", f"/MountDir:{mount_dir}", "/Commit"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply image settings to a Windows ISO or extracted folder."
    )
    parser.add_argument("--iso-path")
    parser.add_argument("--extract-path")
    parser.add_argument("--output-path")
    parser.add_argument("--mount-dir")
    parser.add_argument("--wim-path")
    parser.add_argument("--skip-iso", action="store_true")
    parser.add_argument("--debloat", action="store_true")
    args = parser.parse_args()

    require_admin()

    script_dir = Path(__file__).resolve().parent
    autounattend_src = script_dir.parent / "config" / "autounattend.xml"

    if not args.iso_path and not args.extract_path and not args.debloat:
        print("ERROR: Must specify either --iso-path, --extract-path, or --debloat")
        print()
        parser.print_help()
        return 1

    if args.iso_path and args.extract_path:
        print("ERROR: Cannot specify both --iso-path and --extract-path")
        return 1

    mount_dir = (
        Path(args.mount_dir) if args.mount_dir else Path(win_config.DEFAULT_MOUNT_DIR)
    )

    if args.debloat:
        if not args.wim_path:
            write_error_exit("Debloat mode requires --wim-path")
        return run_debloat(mount_dir, Path(args.wim_path))

    oscdimg_path = win_config.OSCDIMG_PATH or find_oscdimg()

    if args.extract_path:
        extract_dir = Path(args.extract_path)
        if not extract_dir.is_dir():
            write_error_exit(f"ExtractPath not found: {extract_dir}")
        write_step(f"Using extracted folder: {extract_dir}")
        output_path = Path(args.output_path) if args.output_path else None
    else:
        iso_path = Path(args.iso_path)
        if not iso_path.is_file():
            write_error_exit(f"ISO not found: {iso_path}")

        output_path = (
            Path(args.output_path)
            if args.output_path
            else iso_path.with_name(iso_path.stem + "_modified.iso")
        )

        extract_dir = Path(win_config.TEMP_EXTRACT_DIR)
        shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        write_step("Mounting and copying ISO contents...")
        source_drive = mount_iso(iso_path)
        try:
            shutil.copytree(source_drive, extract_dir, dirs_exist_ok=True)
        finally:
            dismount_iso(iso_path)
        write_success(f"ISO extracted to: {extract_dir}")

    if not (extract_dir / "sources" / "boot.wim").is_file():
        write_error_exit("boot.wim not found")
    if not (extract_dir / "sources" / "install.wim").is_file():
        write_error_exit("install.wim not found")

    mount_dir.mkdir(parents=True, exist_ok=True)

    for idx in win_config.BOOT_WIM_INDEXES:
        write_step(f"Processing boot.wim index {idx}...")
        boot_mount = mount_dir / f"boot{idx}"
        safe_remove_directory(boot_mount)
        boot_mount.mkdir(parents=True, exist_ok=True)

        invoke_dism(
            [
                "/Mount-Image",
                f"/ImageFile:{extract_dir / 'sources' / 'boot.wim'}",
                f"/Index:{idx}",
                f"/MountDir:{boot_mount}",
                "/Optimize",
            ]
        )
        _ = shutil.copy(autounattend_src, boot_mount / "autounattend.xml")
        write_success(f"Copied autounattend.xml to boot.wim index {idx}")

        invoke_dism(["/Unmount-Image", f"/MountDir:{boot_mount}", "/Commit"])
        write_success(f"Unmounted boot.wim index {idx}")

    write_step(f"Processing install.wim index {win_config.INSTALL_WIM_INDEX}...")
    install_mount = mount_dir / "install"
    safe_remove_directory(install_mount)
    install_mount.mkdir(parents=True, exist_ok=True)

    invoke_dism(
        [
            "/Mount-Image",
            f"/ImageFile:{extract_dir / 'sources' / 'install.wim'}",
            f"/Index:{win_config.INSTALL_WIM_INDEX}",
            f"/MountDir:{install_mount}",
            "/Optimize",
        ]
    )
    write_success(f"Mounted install.wim index {win_config.INSTALL_WIM_INDEX}")

    write_step("Copying autounattend.xml...")
    panther_dir = install_mount / "Windows" / "Panther"
    panther_dir.mkdir(parents=True, exist_ok=True)
    existing_unattend = panther_dir / "unattend.xml"
    if existing_unattend.is_file():
        print(
            f"[WARN] Overwriting existing {existing_unattend} — if this WIM was already "
            "serviced by NTLite (or another answer-file source), its AutoLogon/OOBE/"
            "ProductKey settings are about to be discarded."
        )
    _ = shutil.copy(autounattend_src, existing_unattend)
    _ = shutil.copy(autounattend_src, extract_dir / "autounattend.xml")

    write_step("Applying offline SYSTEM hive tweaks...")
    reg_hive_path = install_mount / "Windows" / "System32" / "Config" / "SYSTEM"
    temp_hive = "HKLM\\WIM_REG"
    _ = subprocess.run(
        ["reg", "load", temp_hive, str(reg_hive_path)], capture_output=True, check=False
    )
    for key_path, value_name, value_type, value_data in OFFLINE_SYSTEM_VALUES:
        _ = subprocess.run(
            [
                "reg",
                "add",
                f"{temp_hive}\\{key_path}",
                "/v",
                value_name,
                "/t",
                value_type,
                "/d",
                value_data,
                "/f",
            ],
            capture_output=True,
            check=False,
        )
    _ = subprocess.run(["reg", "unload", temp_hive], capture_output=True, check=False)
    write_success("8.3 filename creation disabled and High Performance power plan set")

    write_step("Injecting post-install scripts...")
    scripts_dir = install_mount / "Windows" / "Setup" / "Scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    setup_complete_src = script_dir.parent / "config" / "oem" / "SetupComplete.cmd"
    if setup_complete_src.is_file():
        _ = shutil.copy(setup_complete_src, scripts_dir / "SetupComplete.cmd")
    write_success("Post-install scripts injected")

    invoke_dism(["/Unmount-Image", f"/MountDir:{install_mount}", "/Commit"])
    write_success("Unmounted install.wim")

    if args.skip_iso:
        write_step("Skipping ISO creation (--skip-iso specified)")
        write_success(f"Modified files remain in: {extract_dir}")
    else:
        if output_path is None:
            if args.extract_path:
                base_name = Path.cwd().name or "modified"
                output_path = Path.cwd() / f"{base_name}_modified.iso"
            else:
                output_path = Path(args.iso_path).with_name(
                    Path(args.iso_path).stem + "_modified.iso"
                )

        write_step("Creating ISO...")
        boot_etfs = extract_dir / "boot" / "etfsboot.com"
        boot_efi = extract_dir / "efi" / "microsoft" / "boot" / "efisys.bin"

        if not boot_etfs.is_file():
            write_error_exit("etfsboot.com not found")
        if not boot_efi.is_file():
            write_error_exit("efisys.bin not found")

        boot_data = f"bootdata:2#p0,e,b{boot_etfs}#pEF,e,b{boot_efi}"
        result = subprocess.run(
            [
                oscdimg_path,
                "-m",
                "-o",
                "-u2",
                "-udfver102",
                f"-l{win_config.VOLUME_LABEL}",
                boot_data,
                str(extract_dir),
                str(output_path),
            ],
            check=False,
        )
        if result.returncode != 0:
            write_error_exit("ISO creation failed")
        write_success(f"ISO created: {output_path}")

    write_step("Cleaning up...")
    if args.extract_path:
        write_success(f"Kept extracted folder: {extract_dir}")
    else:
        safe_remove_directory(win_config.TEMP_EXTRACT_DIR)
        write_success("Removed temp extraction folder")
    safe_remove_directory(mount_dir)
    write_success("Removed mount directory")

    print()
    print("=== SUCCESS ===")
    if args.skip_iso:
        print(f"Modified folder: {extract_dir}")
    else:
        print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
