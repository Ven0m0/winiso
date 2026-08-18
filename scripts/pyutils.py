#!/usr/bin/env python3
"""Shared logging and tool-check helpers for the build pipeline scripts."""

import shutil
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"

REQUIRED_TOOLS = ["aria2c", "cabextract", "wimlib-imagex", "chntpw", "xmllint"]


def log_info(msg: str) -> None:
    print(f"{CYAN}[INFO]{NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{GREEN}[OK]{NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


def check_tool(tool: str) -> bool:
    found = shutil.which(tool) is not None
    if found:
        log_success(f"{tool} found")
    return found


def check_iso_tool() -> bool:
    for tool in ("genisoimage", "mkisofs"):
        if shutil.which(tool):
            log_success(f"{tool} found")
            return True
    return False


def check_required_tools(tools: list[str]) -> int:
    """Returns the count of tools that are missing."""
    return sum(not check_tool(t) for t in tools)


def demo() -> None:
    assert check_required_tools(["__definitely_not_a_real_tool__"]) == 1
    assert check_required_tools([]) == 0
    assert check_iso_tool() in (True, False)
    print("pyutils self-check OK")


if __name__ == "__main__":
    demo()
