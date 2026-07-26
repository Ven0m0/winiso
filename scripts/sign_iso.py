#!/usr/bin/env python3
"""sign_iso.py - Generate checksums and an optional GPG signature for an ISO.

Usage:
    python scripts/sign_iso.py [OPTIONS] <iso-file>

Generates SHA256/SHA512 checksums and (optionally) a GPG detached signature
for the given ISO file. Writes <iso>.sha256, <iso>.sha512, and (if GPG is
enabled) <iso>.asc next to the input file.

Options:
    --gpg          Also create a GPG detached signature
    --key KEY_ID   GPG key ID or email to sign with (implies --gpg)

Examples:
    python scripts/sign_iso.py output/Win11_22631.iso
    python scripts/sign_iso.py --gpg --key maintainer@example.com output/Win11_22631.iso
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from pyutils import log_error, log_info, log_success

CHUNK_SIZE = 1024 * 1024


def write_checksum(iso_path: Path, algo: str) -> None:
    digest = hashlib.new(algo)
    with iso_path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    checksum_path = iso_path.with_name(iso_path.name + f".{algo}")
    _ = checksum_path.write_text(f"{digest.hexdigest()}  {iso_path.name}\n")
    log_success(f"Wrote {checksum_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SHA256/SHA512 checksums and an optional GPG signature for an ISO."
    )
    parser.add_argument("iso_file", help="Path to the ISO file")
    parser.add_argument(
        "--gpg", action="store_true", help="Also create a GPG detached signature"
    )
    parser.add_argument(
        "--key", dest="key_id", default=None, help="GPG key ID or email (implies --gpg)"
    )
    args = parser.parse_args()

    sign_gpg = args.gpg or args.key_id is not None

    iso_path = Path(args.iso_file).resolve()
    if not iso_path.is_file():
        log_error(f"ISO file not found: {iso_path}")
        return 1

    log_info(f"Generating checksums for: {iso_path}")
    write_checksum(iso_path, "sha256")
    write_checksum(iso_path, "sha512")

    if sign_gpg:
        if shutil.which("gpg") is None:
            log_error("gpg is not installed; cannot sign")
            return 1
        log_info("Creating GPG detached signature")
        asc_path = iso_path.with_name(iso_path.name + ".asc")
        cmd = ["gpg", "--batch", "--yes"]
        if args.key_id:
            cmd += ["--local-user", args.key_id]
        cmd += ["--output", str(asc_path), "--armor", "--detach-sign", str(iso_path)]
        _ = subprocess.run(cmd, check=True)
        log_success(f"Wrote {asc_path.name}")

    log_success("Signing complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
