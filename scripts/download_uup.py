#!/usr/bin/env python3
"""
UUP File Downloader for Windows 11 ISO Builder
Automates the download of UUP files from uupdump.net
"""

import sys
import os
import json
import subprocess
import argparse
import shutil
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


# Colors for terminal output
class Colors:
    CYAN = "\033[0;36m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log_info(msg):
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {msg}")


def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def check_dependencies():
    """Check if required tools are installed"""
    required = ["aria2c"]
    missing = []

    for tool in required:
        if not shutil.which(tool):
            missing.append(tool)

    if missing:
        log_error(f"Missing required tools: {', '.join(missing)}")
        log_info("Run 'make deps' to install dependencies")
        return False
    return True


def fetch_url(url, headers=None, data=None):
    """Fetch URL with error handling"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    try:
        if data:
            data = urlencode(data).encode("utf-8")
        req = Request(url, headers=headers, data=data)
        with urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except HTTPError as e:
        log_error(f"HTTP Error {e.code}: {e.reason}")
        return None
    except URLError as e:
        log_error(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        log_error(f"Error fetching URL: {e}")
        return None


def get_latest_builds(max_results=10):
    """Fetch latest Windows 11 builds from uupdump.net API"""
    log_info("Fetching latest Windows 11 builds from uupdump.net...")

    # UUPDump API endpoint for listing builds
    api_url = "https://api.uupdump.net/listid.php"

    # Search for Windows 11 builds
    params = {"search": "windows 11", "sortByDate": "1"}

    url = f"{api_url}?{urlencode(params)}"
    response = fetch_url(url)

    if not response:
        log_error("Failed to fetch builds from uupdump.net")
        return None

    try:
        data = json.loads(response)
        if data.get("response", {}).get("error"):
            log_error(f"API Error: {data['response']['error']}")
            return None

        builds = data.get("response", {}).get("builds", {})
        if not builds:
            log_warn("No builds found in API response")
            return []

        # Convert to list and sort by date
        build_list = []
        for build_id, build_info in builds.items():
            build_info["id"] = build_id
            build_list.append(build_info)

        # Sort by created timestamp (newest first)
        build_list.sort(key=lambda x: int(x.get("created") or 0), reverse=True)

        return build_list[:max_results]

    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def display_builds(builds):
    """Display builds in a user-friendly format"""
    print(f"\n{Colors.BOLD}Available Windows 11 Builds:{Colors.RESET}\n")

    for i, build in enumerate(builds, 1):
        title = build.get("title", "Unknown")
        build_num = build.get("build", "N/A")
        arch = build.get("arch", "N/A")
        created = build.get("created", "N/A")

        print(f"{Colors.CYAN}[{i}]{Colors.RESET} {title}")
        print(f"    Build: {build_num} | Arch: {arch} | Created: {created}")
        print()


def get_build_info(build_id):
    """Get detailed information about a specific build"""
    log_info(f"Fetching build information for ID: {build_id}")

    api_url = f"https://api.uupdump.net/get.php?id={build_id}"
    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = json.loads(response)
        if data.get("response", {}).get("error"):
            log_error(f"API Error: {data['response']['error']}")
            return None

        return data.get("response")
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def get_available_editions(build_id):
    """Get available editions for a specific build from the API"""
    log_info(f"Fetching available editions for build: {build_id}")

    params = {"id": build_id}
    api_url = f"https://api.uupdump.net/listeditions.php?{urlencode(params)}"
    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = json.loads(response)
        response_data = data.get("response") or {}
        if response_data.get("error"):
            log_error(f"API Error: {response_data['error']}")
            return None

        return response_data
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def get_available_languages(build_id=None):
    """Get available languages for a specific build from the API"""
    if build_id:
        log_info(f"Fetching available languages for build: {build_id}")
        params = {"id": build_id}
        api_url = f"https://api.uupdump.net/listlangs.php?{urlencode(params)}"
    else:
        log_info("Fetching all available languages")
        api_url = "https://api.uupdump.net/listlangs.php"

    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = json.loads(response)
        if data.get("response", {}).get("error"):
            log_error(f"API Error: {data['response']['error']}")
            return None

        return data.get("response", {})
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def fetch_latest_from_wu(arch="amd64", ring="Retail"):
    """Fetch the latest build from Windows Update servers"""
    log_info(f"Fetching latest {arch} build from Windows Update ({ring} ring)...")

    params = {"arch": arch, "ring": ring}
    api_url = f"https://api.uupdump.net/fetchupd.php?{urlencode(params)}"
    response = fetch_url(api_url)

    if not response:
        log_warn("Failed to fetch from Windows Update, falling back to cached builds")
        return None

    try:
        data = json.loads(response)
        if data.get("response", {}).get("error"):
            log_error(f"API Error: {data['response']['error']}")
            return None

        return data.get("response", {})
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def get_api_version():
    """Get the current UUP dump API version"""
    api_url = "https://api.uupdump.net/"
    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = json.loads(response)
        return data.get("response", {})
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None


def select_editions(build_info):
    """Allow user to select which editions to download"""
    files = build_info.get("files", {})

    # Find edition-specific ESD files
    edition_files = {}

    for filename, file_info in files.items():
        if filename.endswith(".esd"):
            filename_lower = filename.lower()
            if "professional" in filename_lower:
                edition_files["professional"] = filename
            elif "enterprise" in filename_lower:
                edition_files["enterprise"] = filename
            elif "home" in filename_lower:
                edition_files["home"] = filename
            elif "core" in filename_lower:
                edition_files["core"] = filename
            elif "education" in filename_lower:
                edition_files["education"] = filename

    if not edition_files:
        log_warn("No edition-specific files found, will download all files")
        return None

    print(f"\n{Colors.BOLD}Available Editions:{Colors.RESET}\n")
    editions = list(edition_files.keys())
    for i, edition in enumerate(editions, 1):
        print(f"{Colors.CYAN}[{i}]{Colors.RESET} {edition}")
    print(f"{Colors.CYAN}[A]{Colors.RESET} All editions (default)")

    choice = input(f"\n{Colors.BOLD}Select edition [A]:{Colors.RESET} ").strip().upper()

    if choice == "" or choice == "A":
        return None  # Download all

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(editions):
            return [edition_files[editions[idx]]]
    except ValueError:
        # Non-numeric or invalid input; fall through to generic warning and default behavior.
        pass

    log_warn("Invalid selection, downloading all editions")
    return None


def _prepare_output_directory(output_path):
    # Create output directory and optionally clear existing files
    output_path.mkdir(parents=True, exist_ok=True)
    existing_files = list(output_path.glob("*"))
    if existing_files:
        print(
            f"\n{Colors.YELLOW}Warning:{Colors.RESET} {len(existing_files)} files exist in {output_path}"
        )
        response = input("Clear existing files? [y/N]: ").strip().lower()
        if response == "y":
            log_info("Clearing existing files...")
            for f in existing_files:
                if f.is_file() and f.name != ".gitkeep":
                    f.unlink()


def _prepare_download_list(build_id, files, edition_filter):
    # Construct the list of files to download
    download_list = []
    base_url = "https://uupdump.net/get.php"
    for filename, file_info in files.items():
        if edition_filter and filename.endswith(".esd"):
            if filename not in edition_filter:
                continue
        file_url = f"{base_url}?id={build_id}&pack={filename}&aria2=2"
        download_list.append(
            {"url": file_url, "name": filename, "size": file_info.get("size", 0)}
        )
    return download_list


def _run_aria2_download(output_path, aria2_input, download_list):
    lines = []
    for item in download_list:
        if (
            "\n" in item["url"]
            or "\r" in item["url"]
            or "\n" in item["name"]
            or "\r" in item["name"]
        ):
            log_error(f"Invalid characters in URL or filename: {item['name']}")
            return False

        safe_name = os.path.basename(item["name"].replace("\\", "/"))
        if not safe_name or safe_name in (".", ".."):
            log_error(f"Invalid filename detected: {item['name']}")
            return False

        try:
            resolved_output = output_path.resolve()
            target_path = resolved_output.joinpath(safe_name).resolve()
            target_path.relative_to(resolved_output)
        except (ValueError, RuntimeError):
            log_error(f"Path traversal attempt detected in filename: {item['name']}")
            return False

        lines.append(f"{item['url']}\n  out={safe_name}\n")

    with open(aria2_input, "w") as f:
        f.writelines(lines)

    log_info("Starting download with aria2c...")
    print(
        f"{Colors.BOLD}This may take a while depending on your connection...{Colors.RESET}\n"
    )

    aria2_cmd = [
        "aria2c",
        "--input-file",
        str(aria2_input),
        "--dir",
        str(output_path),
        "--max-connection-per-server",
        "8",
        "--split",
        "8",
        "--min-split-size",
        "1M",
        "--continue",
        "true",
        "--max-tries",
        "5",
        "--retry-wait",
        "5",
        "--allow-overwrite",
        "true",
        "--auto-file-renaming",
        "false",
        "--check-certificate",
        "false",
        "--show-console-readout",
        "true",
    ]

    try:

        subprocess.run(aria2_cmd, check=True)
        log_success("Download completed successfully")

        if aria2_input.exists():
            aria2_input.unlink()

        return True
    except subprocess.CalledProcessError as e:
        log_error(f"aria2c failed with return code {e.returncode}")
        return False
    except KeyboardInterrupt:
        log_error("\nDownload interrupted by user")
        if aria2_input.exists():
            aria2_input.unlink()
        return False
    except Exception as e:
        log_error(f"Unexpected error during download: {e}")
        return False


def download_build(build_id, output_dir, edition_filter=None, build_info=None):
    """Download UUP files for a specific build"""
    if build_info is None:
        build_info = get_build_info(build_id)

    if not build_info:
        log_error("Failed to get build information")
        return False

    files = build_info.get("files", {})
    if not files:
        log_error("No files found for this build")
        return False

    output_path = Path(output_dir)
    _prepare_output_directory(output_path)

    log_info(f"Preparing to download {len(files)} files...")
    download_list = _prepare_download_list(build_id, files, edition_filter)

    if not download_list:
        log_error("No files to download after filtering")
        return False

    log_success(f"Will download {len(download_list)} files")

    aria2_input = output_path / "aria2_input.txt"
    return _run_aria2_download(output_path, aria2_input, download_list)


def interactive_mode(output_dir):
    """Interactive mode for selecting and downloading builds"""
    print(f"\n{Colors.BOLD}UUP File Downloader for Windows 11{Colors.RESET}")
    print("=" * 50)

    builds = get_latest_builds()
    if not builds:
        log_error("Failed to fetch builds")
        return False

    display_builds(builds)

    while True:
        try:
            choice = input(
                f"{Colors.BOLD}Select build number [1-{len(builds)}] or 'q' to quit:{Colors.RESET} "
            ).strip()

            if choice.lower() == "q":
                log_info("Cancelled by user")
                return False

            idx = int(choice) - 1
            if 0 <= idx < len(builds):
                selected_build = builds[idx]
                build_id = selected_build["id"]

                print(
                    f"\n{Colors.BOLD}Selected:{Colors.RESET} {selected_build.get('title', 'Unknown')}"
                )
                print(f"{Colors.BOLD}Build ID:{Colors.RESET} {build_id}")

                # Fetch build info once
                build_info = get_build_info(build_id)
                if not build_info:
                    log_error("Failed to get build information")
                    return False

                # Ask for edition selection
                edition_filter = select_editions(build_info)

                confirm = (
                    input(
                        f"\n{Colors.BOLD}Proceed with download? [Y/n]:{Colors.RESET} "
                    )
                    .strip()
                    .lower()
                )
                if confirm == "" or confirm == "y":
                    return download_build(
                        build_id, output_dir, edition_filter, build_info=build_info
                    )
                else:
                    log_info("Download cancelled")
                    return False
            else:
                log_warn(f"Please enter a number between 1 and {len(builds)}")

        except ValueError:
            log_warn("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print()
            log_info("Cancelled by user")
            return False


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Download UUP files from uupdump.net for Windows 11 ISO building",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Interactive mode
  %(prog)s --build-id UUID          # Download specific build by ID
  %(prog)s --output /custom/path    # Custom output directory
  %(prog)s --list                   # List latest builds only
  %(prog)s --editions UUID          # List available editions for a build
  %(prog)s --languages UUID        # List available languages for a build
  %(prog)s --latest                # Fetch latest build from Windows Update

For more information, visit: https://uupdump.net
        """,
    )

    parser.add_argument(
        "-o",
        "--output",
        default="uup_files",
        help="Output directory for downloaded files (default: uup_files)",
    )

    parser.add_argument("-b", "--build-id", help="Specific build ID to download")

    parser.add_argument(
        "-l", "--list", action="store_true", help="List latest builds and exit"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of builds to list (default: 10)",
    )

    parser.add_argument(
        "-e",
        "--editions",
        help="List available editions for a specific build ID and exit",
    )

    parser.add_argument(
        "--languages",
        const="",
        nargs="?",
        help="List available languages (optionally for a specific build ID)",
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Fetch latest build info from Windows Update servers",
    )

    parser.add_argument(
        "--arch",
        default="amd64",
        choices=["amd64", "x86", "arm64", "all"],
        help="Architecture for --latest (default: amd64)",
    )

    parser.add_argument(
        "--ring",
        default="Retail",
        choices=["Dev", "Beta", "ReleasePreview", "Retail"],
        help="Update ring for --latest (default: Retail)",
    )

    parser.add_argument(
        "--version", action="store_true", help="Show API version info and exit"
    )

    return parser.parse_args(args)


def main():
    args = parse_args()

    # Check dependencies (skip for info-only commands)
    info_only = (
        args.list
        or args.editions
        or args.languages is not None
        or args.latest
        or args.version
    )
    if not info_only and not check_dependencies():
        return 1

    # API version check
    # Info-only modes should exit before any download/output-dir setup so they can
    # run without invoking normal-path dependency or filesystem checks.
    info_only_mode = (
        args.version or args.editions or args.languages is not None or args.latest
    )

    if info_only_mode:
        if args.version:
            version_info = get_api_version()
            if version_info:
                log_success("UUP dump API is online")
                print(f"  API Version: {version_info.get('apiVersion', 'unknown')}")
                print(
                    f"  JSON API Version: {version_info.get('jsonApiVersion', 'unknown')}"
                )
                return 0
            return 1

        # List editions mode
        if args.editions:
            editions_info = get_available_editions(args.editions)
            if editions_info:
                print(f"\n{Colors.BOLD}Available Editions for Build:{Colors.RESET}\n")
                edition_list = editions_info.get("editionList", [])
                fancy_names = editions_info.get("editionFancyNames", {})
                for edition in edition_list:
                    fancy_name = fancy_names.get(edition, edition)
                    print(f"  {Colors.CYAN}{edition}{Colors.RESET} - {fancy_name}")
                return 0
            return 1

        # List languages mode
        if args.languages is not None:
            langs_info = get_available_languages(args.languages or None)
            if langs_info:
                print(f"\n{Colors.BOLD}Available Languages:{Colors.RESET}\n")
                lang_list = langs_info.get("langList", [])
                fancy_names = langs_info.get("langFancyNames", {})
                for lang in lang_list:
                    fancy_name = fancy_names.get(lang, lang)
                    print(f"  {Colors.CYAN}{lang}{Colors.RESET} - {fancy_name}")
                return 0
            return 1

        # Fetch latest from Windows Update
        if args.latest:
            latest_info = fetch_latest_from_wu(args.arch, args.ring)
            if latest_info:
                print(
                    f"\n{Colors.BOLD}Latest Build from Windows Update:{Colors.RESET}\n"
                )
                print(f"  Update ID: {latest_info.get('updateId', 'N/A')}")
                print(f"  Title: {latest_info.get('updateTitle', 'N/A')}")
                print(f"  Build: {latest_info.get('foundBuild', 'N/A')}")
                print(f"  Arch: {latest_info.get('arch', 'N/A')}")
                return 0
            return 1
    # Resolve output directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Security: Resolve and validate output path to prevent traversal
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = project_root.joinpath(output_dir)

    try:
        output_dir.resolve().relative_to(project_root.resolve())
    except (ValueError, RuntimeError):
        log_error(f"Path traversal attempt detected for output: {args.output}")
        return 1

    # List mode
    if args.list:
        builds = get_latest_builds(args.max_results)
        if builds:
            display_builds(builds)
            return 0
        return 1

    # Direct build ID mode
    if args.build_id:
        log_info(f"Downloading build ID: {args.build_id}")
        success = download_build(args.build_id, output_dir)
        return 0 if success else 1

    # Interactive mode
    success = interactive_mode(output_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
