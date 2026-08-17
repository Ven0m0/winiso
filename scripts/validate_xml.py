#!/usr/bin/env python3
"""validate_xml.py - Validate XML config files.

Checks:
  - Every *.xml file in the repo is well-formed (xmllint if available, else stdlib
    ElementTree)
  - UTF-8 encoding without a byte-order mark (BOM) - see AGENTS.md's XML encoding
    invariant
  - config/autounattend.xml is byte-identical to ventoy/answer/autounattend.xml (it is
    a symlink to it; this is a canary for a broken/unresolved symlink, e.g. a checkout
    without symlink support)
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyutils import check_tool, log_error, log_info, log_success

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

BOM = b"\xef\xbb\xbf"
CANONICAL_AUTOUNATTEND = PROJECT_ROOT / "ventoy" / "answer" / "autounattend.xml"
LINKED_AUTOUNATTEND = PROJECT_ROOT / "config" / "autounattend.xml"
EXCLUDED_PARTS = {".git", "node_modules"}


def discover_xml_files() -> list[Path]:
    return sorted(
        p for p in PROJECT_ROOT.rglob("*.xml") if not EXCLUDED_PARTS & set(p.parts)
    )


def check_well_formed(xml_file: Path, use_xmllint: bool, errors: list[str]) -> None:
    if use_xmllint:
        result = subprocess.run(
            ["xmllint", "--noout", str(xml_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"{xml_file}: {result.stderr.strip()}")
        return
    try:
        ET.parse(xml_file)
    except ET.ParseError as exc:
        errors.append(f"{xml_file}: {exc}")


def check_no_bom(xml_file: Path, errors: list[str]) -> None:
    if xml_file.read_bytes()[:3] == BOM:
        errors.append(
            f"{xml_file}: has a UTF-8 byte-order mark (BOM) - must be UTF-8 without BOM"
        )


def check_autounattend_in_sync(errors: list[str]) -> None:
    if not CANONICAL_AUTOUNATTEND.is_file() or not LINKED_AUTOUNATTEND.is_file():
        errors.append(
            "ventoy/answer/autounattend.xml and config/autounattend.xml must both exist"
        )
        return
    if CANONICAL_AUTOUNATTEND.read_bytes() != LINKED_AUTOUNATTEND.read_bytes():
        errors.append(
            "config/autounattend.xml does not resolve to ventoy/answer/autounattend.xml "
            "- symlink broken or checked out without symlink support"
        )


def main() -> int:
    files = [Path(a).resolve() for a in sys.argv[1:] if a.lower().endswith(".xml")]
    files = files or discover_xml_files()

    use_xmllint = check_tool("xmllint")
    errors: list[str] = []

    log_info(f"Validating {len(files)} XML file(s)...")
    for xml_file in files:
        check_well_formed(xml_file, use_xmllint, errors)
        check_no_bom(xml_file, errors)

    check_autounattend_in_sync(errors)

    if errors:
        log_error("XML validation failed:")
        for err in errors:
            log_error(f"  {err}")
        return 1

    log_success(f"All {len(files)} XML file(s) are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
