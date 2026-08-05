#!/usr/bin/env python3
"""validate_reg_files.py - Validate standalone .reg files and .reg content embedded
in autounattend.xml (via <Extensions><File path="...reg">).

Checks:
  - Required header: "Windows Registry Editor Version 5.00"
  - Informational scan for security-sensitive value changes (not fatal)
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyutils import log_error, log_info, log_success, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

EXTENSIONS_FILE_TAG = "{https://schneegans.de/windows/unattend-generator/}File"
REG_HEADER = "Windows Registry Editor Version 5.00"

SUSPICIOUS_PATTERNS = [
    (r"DisableSecurity", "Disabling security settings"),
    (r"PromptOnSecureDesktop", "UAC security modification"),
    (r"EnableLUA.*=dword:00000000", "Disabling UAC"),
    (r"ConsentPromptBehaviorAdmin.*=dword:00000000", "Disabling admin prompts"),
    (r"fAllowToGetHelp.*=dword:00000000", "Disabling remote assistance"),
    (
        r"HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\.*Start.*=dword:00000004",
        "Disabling a service",
    ),
    (r"Windows\\System\\Rpc", "RPC configuration change"),
    (r"TcpTimedWaitDelay", "Network timing configuration"),
]


def decode_reg_bytes(raw: bytes) -> str:
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def check_header(label: str, content: str, errors: list[str]) -> None:
    first_line = content.splitlines()[0].strip() if content.strip() else ""
    if first_line != REG_HEADER:
        errors.append(f"[{label}]: missing/invalid header (expected '{REG_HEADER}')")


def scan_safety(label: str, content: str, notes: list[str]) -> None:
    for pattern, message in SUSPICIOUS_PATTERNS:
        if re.search(pattern, content):
            notes.append(f"[{label}]: {message} - verify this is intentional")


def embedded_reg_blocks(xml_path: Path) -> list[tuple[str, str]]:
    if not xml_path.is_file():
        return []
    tree = ET.parse(xml_path)
    root = tree.getroot()
    blocks = []
    for file_el in root.iter(EXTENSIONS_FILE_TAG):
        path = file_el.get("path", "")
        if path.lower().endswith(".reg") and file_el.text:
            blocks.append((f"{xml_path}::{path}", file_el.text.strip() + "\n"))
    return blocks


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []

    log_info("Checking standalone .reg files...")
    reg_files = sorted(
        p
        for p in PROJECT_ROOT.rglob("*.reg")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )
    for reg_file in reg_files:
        label = str(reg_file.relative_to(PROJECT_ROOT))
        content = decode_reg_bytes(reg_file.read_bytes())
        check_header(label, content, errors)
        scan_safety(label, content, notes)
    log_info(f"  -> {len(reg_files)} standalone .reg file(s) checked")

    log_info("Checking .reg content embedded in autounattend.xml...")
    embedded_count = 0
    for xml_rel in ("ventoy/answer/autounattend.xml", "config/autounattend.xml"):
        for label, content in embedded_reg_blocks(PROJECT_ROOT / xml_rel):
            embedded_count += 1
            check_header(label, content, errors)
            scan_safety(label, content, notes)
    log_info(f"  -> {embedded_count} embedded .reg block(s) checked")

    print()
    if notes:
        log_warn("Safety review notes (informational, not fatal):")
        for note in notes:
            log_warn(f"  {note}")
        print()

    if errors:
        log_error("Registry validation failed:")
        for err in errors:
            log_error(f"  {err}")
        return 1

    log_success("All .reg files and embedded .reg blocks have valid headers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
