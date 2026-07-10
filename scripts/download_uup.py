#!/usr/bin/env python3
"""UUP File Downloader for Windows 11 ISO Builder
Automates the download of UUP files from uupdump.net
"""

import sys
import os
import time
from typing import Optional, Dict, List, Any, Union
import json
import argparse
import shutil
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

CACHE_DIR_NAME: str = ".uup_cache"
DEFAULT_CACHE_TTL_SECONDS: int = 3600
COMPONENT_GROUPS_FILE: str = "config/component_groups.json"
ALL_COMPONENT_GROUPS: List[str] = [
    "gaming",
    "productivity",
    "social",
    "telemetry",
    "media",
    "system",
    "news",
    "oem",
]

# Profile definitions for different use cases
PROFILES: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "description": "Stripped-down Windows 11 with maximum debloating",
        "edition": "Core",
        "language": "en-us",
        "component_groups": ["gaming", "productivity", "social", "telemetry", "media", "system", "news", "oem"],
    },
    "standard": {
        "description": "Default debloated Windows 11 (Professional)",
        "edition": "Professional",
        "language": "en-us",
        "component_groups": ["telemetry", "social", "oem", "news"],
    },
    "gaming": {
        "description": "Gaming-optimized Windows 11 with Game Mode enabled",
        "edition": "Professional",
        "language": "en-us",
        "component_groups": ["productivity", "telemetry", "system", "news", "oem"],
    },
    "enterprise": {
        "description": "Enterprise-ready Windows 11 with domain features",
        "edition": "Enterprise",
        "language": "en-us",
        "component_groups": ["gaming", "social", "media", "news", "oem"],
    },
    "dev": {
        "description": "Developer configuration with WSL and tools",
        "edition": "Professional",
        "language": "en-us",
        "component_groups": ["social", "oem", "news", "media"],
    },
}


class Colors:
    CYAN = "\033[0;36m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


_url_cache: Dict[str, Union[str, Dict[str, Any]]] = {}


def log_info(msg: str) -> None:
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def check_dependencies() -> bool:
    """Check if required tools are installed"""
    required = ["aria2c", "wimlib-imagex", "cabextract"]
    missing: List[str] = []
    for tool in required:
        if not shutil.which(tool):
            missing.append(tool)
    if missing:
        log_error(f"Missing required tools: {', '.join(missing)}")
        log_info("Run 'make deps' to install dependencies")
        return False
    return True


def fetch_url(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
    return_json: bool = False,
) -> Optional[Union[str, Dict[str, Any]]]:
    """Fetch URL with error handling and optional caching"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    cache_key = f"{url}:{return_json}" if not data else None
    if cache_key and cache_key in _url_cache:
        return _url_cache[cache_key]

    try:
        if data:
            data = urlencode(data).encode("utf-8")
        req = Request(url, headers=headers, data=data)
        with urlopen(req, timeout=30) as response:
            result = response.read().decode("utf-8")

            if return_json:
                try:
                    result = json.loads(result)
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse JSON response: {e}")
                    return None

            if cache_key:
                _url_cache[cache_key] = result

            return result
    except HTTPError as e:
        log_error(f"HTTP Error {e.code}: {e.reason}")
        return None
    except URLError as e:
        log_error(f"URL Error: {e.reason}")
        return None
    except OSError as e:
        log_error(f"Network error fetching URL: {e}")
        return None
    except Exception as e:
        log_error(f"Unexpected error fetching URL: {e}")
        return None


def get_latest_builds(max_results: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Fetch latest Windows 11 builds from uupdump.net API"""
    log_info("Fetching latest Windows 11 builds from uupdump.net...")

    api_url = "https://api.uupdump.net/listid.php"
    params = {"search": "windows 11", "sortByDate": "1"}
    url = f"{api_url}?{urlencode(params)}"
    data = fetch_url(url, return_json=True)

    if not data:
        log_error("Failed to fetch builds from uupdump.net")
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    builds = data.get("response", {}).get("builds", {})
    if not builds:
        log_warn("No builds found in API response")
        return []

    build_list: List[Dict[str, Any]] = []
    for build_id, build_info in builds.items():
        build_info["id"] = build_id
        build_list.append(build_info)

    build_list.sort(key=lambda x: int(x.get("created") or 0), reverse=True)
    return build_list[:max_results]


def display_builds(builds: Optional[List[Dict[str, Any]]]) -> None:
    """Display builds in a user-friendly format"""
    if not builds:
        log_warn("No builds available.")
        return

    print(f"\n{Colors.BOLD}Available Windows 11 Builds:{Colors.RESET}\n")

    for i, build in enumerate(builds, 1):
        title = build.get("title", "Unknown")
        build_num = build.get("build", "N/A")
        arch = build.get("arch", "N/A")
        created = build.get("created", "N/A")

        print(f"{Colors.CYAN}[{i}]{Colors.RESET} {title}")
        print(f"    Build: {build_num} | Arch: {arch} | Created: {created}")
        print()


def get_build_info(build_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific build"""
    log_info(f"Fetching build information for ID: {build_id}")

    api_url = f"https://api.uupdump.net/get.php?id={build_id}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    return data.get("response")


def get_available_editions(build_id: str) -> Optional[Dict[str, Any]]:
    """Get available editions for a specific build from the API"""
    log_info(f"Fetching available editions for build: {build_id}")

    params = {"id": build_id, "lang": "en-us"}
    api_url = f"https://api.uupdump.net/listeditions.php?{urlencode(params)}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        return None

    response_data = data.get("response") or {}
    if response_data.get("error"):
        log_error(f"API Error: {response_data['error']}")
        return None

    return response_data


def get_available_languages(build_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get available languages for a specific build from the API"""
    if build_id:
        log_info(f"Fetching available languages for build: {build_id}")
        params = {"id": build_id, "lang": "en-us"}
        api_url = f"https://api.uupdump.net/listlangs.php?{urlencode(params)}"
    else:
        log_info("Fetching all available languages")
        api_url = "https://api.uupdump.net/listlangs.php"

    data = fetch_url(api_url, return_json=True)

    if not data:
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    return data.get("response", {})


def fetch_latest_from_wu(arch: str = "amd64", ring: str = "Retail") -> Optional[Dict[str, Any]]:
    """Fetch the latest build from Windows Update servers"""
    log_info(f"Fetching latest {arch} build from Windows Update ({ring} ring)...")

    params = {"arch": arch, "ring": ring}
    api_url = f"https://api.uupdump.net/fetchupd.php?{urlencode(params)}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        log_warn("Failed to fetch from Windows Update, falling back to cached builds")
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    return data.get("response", {})


def get_api_version() -> Optional[Dict[str, Any]]:
    """Get the current UUP dump API version"""
    api_url = "https://api.uupdump.net/"
    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None

    if not isinstance(data, dict):
        return None

    return data.get("response", {})


def get_cache_dir() -> Path:
    """Return the cache directory, creating it if necessary."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    cache_dir = project_root / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _safe_cache_name(key: str) -> str:
    """Convert a cache key into a filesystem-safe filename."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return safe[:128] + ".json"


def cache_get(key: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> Optional[Any]:
    """Read a cached value if present and not expired."""
    cache_file = get_cache_dir() / _safe_cache_name(key)
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log_warn(f"Cache read failed for {key}: {e}")
        try:
            cache_file.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    if not isinstance(entry, dict) or "timestamp" not in entry or "data" not in entry:
        try:
            cache_file.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    age = time.time() - float(entry["timestamp"])
    if age > ttl_seconds:
        return None

    return entry["data"]


def cache_set(key: str, data: Any) -> bool:
    """Store a value in the local cache with the current timestamp."""
    cache_file = get_cache_dir() / _safe_cache_name(key)
    entry = {"timestamp": time.time(), "data": data}
    try:
        with open(cache_file, "w") as f:
            json.dump(entry, f)
        return True
    except (OSError, TypeError) as e:
        log_warn(f"Cache write failed for {key}: {e}")
        return False


def cache_clear(key: Optional[str] = None) -> int:
    """Remove a single cache entry (if key given) or all entries. Returns the number removed."""
    cache_dir = get_cache_dir()
    if key:
        target = cache_dir / _safe_cache_name(key)
        if target.exists():
            try:
                target.unlink()
                return 1
            except OSError as e:
                log_warn(f"Cache clear failed for {key}: {e}")
                return 0
        return 0

    count = 0
    for f in cache_dir.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count


def get_latest_builds_cached(
    max_results: int = 10,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch latest builds, returning a cached result when fresh enough."""
    cache_key = f"latest_builds_{max_results}"

    if not force_refresh:
        cached = cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached

    builds = get_latest_builds(max_results)
    if builds is not None:
        cache_set(cache_key, builds)
    return builds


def get_build_info_cached(
    build_id: str,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """Fetch build info, returning a cached result when fresh enough."""
    cache_key = f"build_info_{build_id}"

    if not force_refresh:
        cached = cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached

    info = get_build_info(build_id)
    if info is not None:
        cache_set(cache_key, info)
    return info


def select_editions(build_info: Dict[str, Any]) -> Optional[List[str]]:
    """Allow user to select which editions to download"""
    files = build_info.get("files", {})

    # Find edition-specific ESD files
    edition_files: Dict[str, str] = {}

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


def list_edition_files(build_info: Dict[str, Any]) -> Dict[str, str]:
    """Return the mapping of known edition name -> ESD filename from build info."""
    edition_files: Dict[str, str] = {}
    files = build_info.get("files", {})
    for filename in files.keys():
        if not filename.endswith(".esd"):
            continue
        lower = filename.lower()
        for key in ("professional", "enterprise", "home", "core", "education"):
            if key in lower:
                edition_files[key] = filename
                break
    return edition_files


def resolve_edition_filter(
    build_info: Dict[str, Any],
    edition: Optional[str] = None,
) -> Optional[List[str]]:
    """Resolve the edition name to its ESD filename, or return None for all.

    Used by the --edition CLI flag to bypass the interactive prompt. The edition
    name is matched case-insensitively against known keys (professional, enterprise,
    home, core, education). If the edition cannot be resolved, an error is logged
    and None is returned (which means: download all files).
    """
    if not edition:
        return None

    edition_files = list_edition_files(build_info)
    if not edition_files:
        log_warn("No edition-specific files in build metadata; downloading all files")
        return None

    key = edition.lower()
    if key in edition_files:
        log_info(f"Filtering to edition: {key} -> {edition_files[key]}")
        return [edition_files[key]]

    # Allow matching against the full filename too
    for k, filename in edition_files.items():
        if filename.lower() == key or k.startswith(key):
            log_info(f"Filtering to edition: {k} -> {filename}")
            return [filename]

    log_error(f"Unknown edition '{edition}'. Available: {', '.join(edition_files.keys())}")
    return None


def _prepare_output_directory(output_path: Path) -> None:
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


def _prepare_download_list(
    build_id: str,
    files: Dict[str, Any],
    edition_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    download_list: List[Dict[str, Any]] = []
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


def _run_aria2_download(
    output_path: Path,
    aria2_input: Path,
    download_list: List[Dict[str, Any]],
    verbose: bool = False,
) -> bool:
    import subprocess

    try:
        lines = []
        for item in download_list:
            sanitized_name = str(Path(item["name"].replace("\\", "/")).name)
            if ".." in sanitized_name or "/" in sanitized_name:
                log_error(f"Invalid filename detected: {item['name']}")
                return False
            url = str(item["url"])
            if "\n" in url or "\r" in url:
                url = url.replace("\n", "").replace("\r", "")

            name = str(item["name"])
            if "\n" in name or "\r" in name:
                name = name.replace("\n", "").replace("\r", "")
            lines.append(f"{url}\n  out={name}")

        with open(aria2_input, "w") as f:
            f.write("\n".join(lines))

        cmd = [
            "aria2c",
            "-i",
            str(aria2_input),
            "-d",
            str(output_path),
            "-j",
            "16",
            "-x",
            "16",
            "-s",
            "16",
            "--file-allocation=none",
            "--continue=true",
        ]
        log_info("Starting download...")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if verbose and result.stdout:
            print(result.stdout)
        log_success("Download completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Download failed with exit code {e.returncode}")
        if verbose and (e.stdout or e.stderr):
            if e.stdout:
                print(f"stdout: {e.stdout}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
        return False
    except KeyboardInterrupt:
        log_warn("\nDownload cancelled by user")
        return False
    except OSError as e:
        log_error(f"System error during download: {e}")
        return False
    except Exception as e:
        log_error(f"An unexpected error occurred during download: {e}")
        return False
    finally:
        for f in output_path.glob("aria2_input*"):
            try:
                f.unlink()
            except OSError:
                pass


def download_build(
    build_id: str,
    output_dir: Union[str, Path],
    edition_filter: Optional[List[str]] = None,
    build_info: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
) -> bool:
    """Download UUP files for a specific build"""
    if build_info is None:
        build_info = get_build_info_cached(
            build_id, ttl_seconds=cache_ttl, force_refresh=not use_cache
        )

    if not build_info:
        log_error("Failed to get build information")
        return False

    files = build_info.get("files", {})
    if not files:
        log_error("No files found for this build")
        return False

    output_path = Path(output_dir)
    if output_path.is_absolute():
        output_path = output_path.resolve()
    else:
        output_path = Path.cwd().joinpath(output_path).resolve()

    resolved_cwd = Path.cwd().resolve()
    if os.path.commonpath([output_path, resolved_cwd]) != str(resolved_cwd):
        log_error("Output directory must be within the current directory")
        return False

    _prepare_output_directory(output_path)

    log_info(f"Preparing to download {len(files)} files...")
    download_list = _prepare_download_list(build_id, files, edition_filter)

    if not download_list:
        log_error("No files to download after filtering")
        return False

    log_success(f"Will download {len(download_list)} files")

    aria2_input = output_path / "aria2_input.txt"
    return _run_aria2_download(output_path, aria2_input, download_list, verbose=verbose)


def _process_selected_build(
    selected_build: Dict[str, Any],
    output_dir: Union[str, Path],
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    edition: Optional[str] = None,
) -> bool:
    """Process the selected build for download."""
    build_id = selected_build["id"]

    print(
        f"\n{Colors.BOLD}Selected:{Colors.RESET} {selected_build.get('title', 'Unknown')}"
    )
    print(f"{Colors.BOLD}Build ID:{Colors.RESET} {build_id}")

    # Fetch build info once
    build_info = get_build_info_cached(
        build_id, ttl_seconds=cache_ttl, force_refresh=not use_cache
    )
    if not build_info:
        log_error("Failed to get build information")
        return False

    # Resolve edition: non-interactive if --edition was supplied, else prompt
    if edition:
        edition_filter = resolve_edition_filter(build_info, edition)
    else:
        edition_filter = select_editions(build_info)

    if edition:
        # Non-interactive: skip the confirmation prompt
        return download_build(
            build_id,
            output_dir,
            edition_filter,
            build_info=build_info,
            verbose=verbose,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )

    confirm = (
        input(f"\n{Colors.BOLD}Proceed with download? [Y/n]:{Colors.RESET} ")
        .strip()
        .lower()
    )
    if confirm in ("", "y", "yes"):
        return download_build(
            build_id,
            output_dir,
            edition_filter,
            build_info=build_info,
            verbose=verbose,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
    else:
        log_info("Download cancelled")
        return False


def interactive_mode(
    output_dir: Union[str, Path],
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    edition: Optional[str] = None,
) -> bool:
    """Interactive mode for selecting and downloading builds"""
    print(f"\n{Colors.BOLD}UUP File Downloader for Windows 11{Colors.RESET}")
    print("=" * 50)

    builds = get_latest_builds_cached(
        ttl_seconds=cache_ttl, force_refresh=not use_cache
    )
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
                if _process_selected_build(
                    builds[idx],
                    output_dir,
                    verbose=verbose,
                    use_cache=use_cache,
                    cache_ttl=cache_ttl,
                    edition=edition,
                ):
                    return True
            else:
                log_warn(f"Please enter a number between 1 and {len(builds)}")

        except ValueError:
            log_warn("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print()
            log_info("Cancelled by user")
            return False


def get_profiles() -> Dict[str, Dict[str, Any]]:
    """Load build profiles from config file or return built-in defaults."""
    script_dir = Path(__file__).parent
    profiles_path = script_dir.parent / "config" / "profiles.json"

    if profiles_path.exists():
        try:
            with open(profiles_path, "r") as f:
                data = json.load(f)
                return data.get("profiles", PROFILES)
        except (json.JSONDecodeError, OSError):
            log_warn("Failed to load profiles.json, using built-in profiles")

    return PROFILES


def get_pinned_build() -> Optional[Dict[str, Any]]:
    """Load pinned build configuration from .uup-pin.json in the project root."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pin_path = project_root / ".uup-pin.json"

    if not pin_path.exists():
        return None

    try:
        with open(pin_path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict) and "build_id" in data:
                return data
            log_warn("Invalid pin file: missing 'build_id'")
            return None
    except (json.JSONDecodeError, OSError) as e:
        log_warn(f"Failed to read pin file: {e}")
        return None


def save_pinned_build(
    build_id: str,
    title: Optional[str] = None,
    edition: Optional[str] = None,
) -> bool:
    """Save a build as the pinned version for reproducibility."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pin_path = project_root / ".uup-pin.json"

    data: Dict[str, Any] = {"build_id": build_id}
    if title:
        data["title"] = title
    if edition:
        data["edition"] = edition

    try:
        with open(pin_path, "w") as f:
            json.dump(data, f, indent=2)
        log_success(f"Pinned build {build_id} to {pin_path}")
        return True
    except OSError as e:
        log_error(f"Failed to write pin file: {e}")
        return False


def display_profiles() -> None:
    """Display available build profiles in a user-friendly format."""
    profiles = get_profiles()

    print(f"\n{Colors.BOLD}Available Build Profiles:{Colors.RESET}\n")

    for name, profile in profiles.items():
        description = profile.get("description", "No description")
        edition = profile.get("edition", "N/A")
        print(f"{Colors.CYAN}[{name}]{Colors.RESET} {description}")
        print(f"    Edition: {edition}")
        print()


def get_profile(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific build profile by name."""
    profiles = get_profiles()
    return profiles.get(name)


def load_component_groups(path: Optional[str] = None) -> Dict[str, Any]:
    """Load component groups from config/component_groups.json.

    Returns a dict mapping group name -> {"description": str, "patterns": List[str]}.
    Returns an empty dict if the file is missing, malformed, or has unexpected shape.
    """
    if path is None:
        path = COMPONENT_GROUPS_FILE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log_warn(f"Could not load component groups from {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        log_warn(f"Component groups file {path} is not a JSON object")
        return {}
    raw_groups: Any = data.get("groups", data)
    if not isinstance(raw_groups, dict):
        log_warn(f"Component groups in {path} are not a mapping")
        return {}
    result: Dict[str, Any] = {}
    for name, body in raw_groups.items():
        if not isinstance(name, str) or not isinstance(body, dict):
            continue
        patterns: Any = body.get("patterns", [])
        if not isinstance(patterns, list):
            continue
        cleaned: List[str] = [p for p in patterns if isinstance(p, str) and p]
        if not cleaned:
            continue
        description: str = body.get("description", "") if isinstance(body.get("description"), str) else ""
        result[name] = {"description": description, "patterns": cleaned}
    return result


def list_component_groups(path: Optional[str] = None) -> List[str]:
    """Return the names of all available component groups (sorted)."""
    groups = load_component_groups(path)
    return sorted(groups.keys())


def get_component_group(name: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single component group by name, or None if not found."""
    groups = load_component_groups(path)
    return groups.get(name)


def validate_component_groups(names: List[str], path: Optional[str] = None) -> List[str]:
    """Return the subset of `names` that exist in the component groups file.

    Logs a warning for any names that are unknown.
    """
    available = set(list_component_groups(path))
    valid: List[str] = []
    for name in names:
        if name in available:
            valid.append(name)
        else:
            log_warn(f"Unknown component group: {name}")
    return valid


def collect_component_patterns(
    group_names: List[str], path: Optional[str] = None
) -> List[str]:
    """Collect deduplicated glob patterns from the given component groups.

    Order is preserved (group order, then pattern order within each group).
    """
    seen: set = set()
    combined: List[str] = []
    for group_name in group_names:
        group = get_component_group(group_name, path)
        if not group:
            continue
        for pattern in group.get("patterns", []):
            if pattern in seen:
                continue
            seen.add(pattern)
            combined.append(pattern)
    return combined


def write_component_groups_for_build(
    group_names: List[str], output_path: str = ".uup-groups"
) -> bool:
    """Write the selected component groups to a file consumable by the build pipeline.

    The output file is a simple newline-separated list of group names.
    Returns True on success, False on failure.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for name in group_names:
                f.write(f"{name}\n")
        return True
    except OSError as exc:
        log_error(f"Could not write component groups file {output_path}: {exc}")
        return False


def display_component_groups(path: Optional[str] = None) -> None:
    """Print all available component groups with descriptions to stdout."""
    groups = load_component_groups(path)
    if not groups:
        print("No component groups available.")
        return
    print(f"\n{Colors.BOLD}Available Component Groups:{Colors.RESET}\n")
    for name in sorted(groups.keys()):
        description = groups[name].get("description", "")
        pattern_count = len(groups[name].get("patterns", []))
        print(f"  {Colors.CYAN}{name}{Colors.RESET} ({pattern_count} patterns)")
        if description:
            print(f"    {description}")
    print()


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
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
  %(prog)s --preset gaming         # Use a predefined profile

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
        "--verbose", action="store_true", help="Show verbose output including aria2c stderr/stdout"
    )

    parser.add_argument(
        "-p",
        "--preset",
        dest="preset",
        help="Use a predefined build profile (minimal, standard, gaming, enterprise, dev)",
    )

    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available build profiles and exit",
    )

    parser.add_argument(
        "--pin-build",
        action="store_true",
        help="Pin the current --build-id to .uup-pin.json for reproducible builds",
    )

    parser.add_argument(
        "--use-pin",
        action="store_true",
        help="Use the build ID from .uup-pin.json instead of fetching latest",
    )

    parser.add_argument(
        "--show-pin",
        action="store_true",
        help="Show the currently pinned build and exit",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the build metadata cache and force a network refresh",
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the local build metadata cache and exit",
    )

    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=DEFAULT_CACHE_TTL_SECONDS,
        help=f"Cache TTL in seconds (default: {DEFAULT_CACHE_TTL_SECONDS})",
    )

    parser.add_argument(
        "--edition",
        help=(
            "Non-interactive edition filter: pick a specific edition by name "
            "(professional, enterprise, home, core, education) or by ESD filename"
        ),
    )

    parser.add_argument(
        "--groups",
        dest="groups",
        help=(
            "Comma-separated component group names to remove during build "
            "(gaming, productivity, social, telemetry, media, system, news, oem)"
        ),
    )

    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="List available component groups and exit",
    )

    parser.add_argument(
        "--write-groups",
        metavar="PATH",
        help="Write selected component group names to PATH (one per line) and exit",
    )

    return parser.parse_args(args)


def _handle_info_mode(args: argparse.Namespace) -> Optional[int]:
    """Handles info-only modes and returns the appropriate exit code. Returns None if not handled."""
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
            print(f"\n{Colors.BOLD}Latest Build from Windows Update:{Colors.RESET}\n")
            print(f"  Update ID: {latest_info.get('updateId', 'N/A')}")
            print(f"  Title: {latest_info.get('updateTitle', 'N/A')}")
            print(f"  Build: {latest_info.get('foundBuild', 'N/A')}")
            print(f"  Arch: {latest_info.get('arch', 'N/A')}")
            return 0
        return 1

    return None


def _resolve_output_dir(output_arg: str) -> Optional[Path]:
    """Resolves and validates the output directory to prevent traversal."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Security: Resolve and validate output path to prevent traversal
    output_dir = Path(output_arg)
    if not output_dir.is_absolute():
        output_dir = project_root.joinpath(output_dir)

    try:
        output_dir.resolve().relative_to(project_root.resolve())
    except (ValueError, RuntimeError):
        log_error(f"Path traversal attempt detected for output: {output_arg}")
        return None

    return output_dir


def main() -> int:
    args = parse_args()

    # Handle --clear-cache mode
    if args.clear_cache:
        count = cache_clear()
        log_success(f"Cleared {count} cache entries")
        return 0

    # Handle list-presets mode
    if args.list_presets:
        display_profiles()
        return 0

    # Handle show-pin mode
    if args.show_pin:
        pin = get_pinned_build()
        if pin:
            print(f"Pinned build: {pin.get('build_id')}")
            if "title" in pin:
                print(f"  Title: {pin['title']}")
            if "edition" in pin:
                print(f"  Edition: {pin['edition']}")
            return 0
        log_info("No build currently pinned (no .uup-pin.json found)")
        return 1

    # Handle list-groups mode
    if args.list_groups:
        display_component_groups()
        return 0

    # Handle write-groups mode
    if args.write_groups:
        names: List[str] = []
        if args.groups:
            names = [n.strip() for n in args.groups.split(",") if n.strip()]
        if not names:
            log_error("--write-groups requires --groups to be specified")
            return 1
        valid = validate_component_groups(names)
        if not valid:
            return 1
        if write_component_groups_for_build(valid, args.write_groups):
            log_success(f"Wrote {len(valid)} component groups to {args.write_groups}")
            return 0
        return 1

    # Handle --use-pin: replace build_id with pinned value
    if args.use_pin:
        pin = get_pinned_build()
        if not pin:
            log_error("No pinned build found. Use --pin-build with --build-id to create one.")
            return 1
        log_info(f"Using pinned build: {pin['build_id']}")
        args.build_id = pin["build_id"]

    # Handle --pin-build: save the specified build for future reproducibility
    if args.pin_build:
        if not args.build_id:
            log_error("--pin-build requires --build-id to be specified")
            return 1
        if not save_pinned_build(args.build_id):
            return 1
        # Fall through to download if --build-id is also set

    # Handle preset mode (non-interactive profile selection)
    preset_mode = False
    if args.preset:
        preset_mode = True
        profile = get_profile(args.preset)
        if not profile:
            log_error(f"Unknown profile: {args.preset}")
            log_info(f"Available profiles: {', '.join(get_profiles().keys())}")
            return 1
        log_info(f"Using profile: {args.preset}")
        print(f"  {profile.get('description', '')}")
        # Persist the profile's component groups to .uup-groups for the build pipeline.
        profile_groups: Any = profile.get("component_groups", [])
        if isinstance(profile_groups, list) and profile_groups:
            valid_profile_groups = validate_component_groups(profile_groups)
            if valid_profile_groups:
                if write_component_groups_for_build(valid_profile_groups):
                    log_info(
                        f"Component groups for build: {', '.join(valid_profile_groups)}"
                    )

    # Handle --groups override (always wins over profile defaults)
    if args.groups:
        cli_groups = [n.strip() for n in args.groups.split(",") if n.strip()]
        valid_cli_groups = validate_component_groups(cli_groups)
        if valid_cli_groups:
            if write_component_groups_for_build(valid_cli_groups):
                log_info(
                    f"Component groups (from --groups): {', '.join(valid_cli_groups)}"
                )

    # Check dependencies (skip for info-only commands)
    info_only = (
        args.list
        or args.editions
        or args.languages is not None
        or args.latest
        or args.version
        or args.verbose
    )
    # Note: verbose is not info_only - it affects download behavior
    info_only_mode = (
        args.version or args.editions or args.languages is not None or args.latest
    )

    if not info_only_mode and not check_dependencies():
        return 1

    # API version check
    # Info-only modes should exit before any download/output-dir setup so they can
    # run without invoking normal-path dependency or filesystem checks.
    if info_only_mode:
        result = _handle_info_mode(args)
        if result is not None:
            return result

    output_dir = _resolve_output_dir(args.output)
    if not output_dir:
        return 1

    # List mode
    if args.list:
        builds = get_latest_builds_cached(
            args.max_results, ttl_seconds=args.cache_ttl, force_refresh=args.no_cache
        )
        if builds:
            display_builds(builds)
            return 0
        return 1

    # Direct build ID mode
    if args.build_id:
        log_info(f"Downloading build ID: {args.build_id}")
        edition_filter: Optional[List[str]] = None
        if args.edition:
            build_info = get_build_info_cached(
                args.build_id,
                ttl_seconds=args.cache_ttl,
                force_refresh=args.no_cache,
            )
            if not build_info:
                log_error("Failed to get build information")
                return 1
            edition_filter = resolve_edition_filter(build_info, args.edition)
        success = download_build(
            args.build_id,
            output_dir,
            edition_filter,
            verbose=args.verbose,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
        )
        return 0 if success else 1

    # Preset mode: fetch latest builds and auto-select
    if preset_mode:
        log_info(f"Fetching latest builds for profile '{args.preset}'...")
        builds = get_latest_builds_cached(
            args.max_results,
            ttl_seconds=args.cache_ttl,
            force_refresh=args.no_cache,
        )
        if builds:
            # For preset mode, just list builds and let user select
            display_builds(builds)
            return 0
        return 1

    # Interactive mode
    success = interactive_mode(
        output_dir,
        verbose=args.verbose,
        use_cache=not args.no_cache,
        cache_ttl=args.cache_ttl,
        edition=args.edition,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
