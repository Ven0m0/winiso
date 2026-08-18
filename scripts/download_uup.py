#!/usr/bin/env python3
"""UUP File Downloader for Windows 11 ISO Builder
Automates the download of UUP files from uupdump.net
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Literal, cast, overload
from urllib.parse import urlencode

import httpx
import orjson

CACHE_DIR_NAME: str = ".uup_cache"
DEFAULT_CACHE_TTL_SECONDS: int = 3600
COMPONENT_GROUPS_FILE: str = "config/component_groups.json"
ALL_COMPONENT_GROUPS: list[str] = [
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
PROFILES: dict[str, dict[str, Any]] = {
    "minimal": {
        "description": "Stripped-down Windows 11 with maximum debloating",
        "edition": "Core",
        "language": "en-us",
        "component_groups": [
            "gaming",
            "productivity",
            "social",
            "telemetry",
            "media",
            "system",
            "news",
            "oem",
        ],
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


_url_cache: dict[str, str | dict[str, Any]] = {}
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Return the shared httpx client, creating it on first use."""
    global _client
    if _client is None:
        _client = httpx.Client(http2=True, timeout=30.0, follow_redirects=True)
    return _client


def log_info(msg: str) -> None:
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def log_debug(msg: str) -> None:
    if os.environ.get("LOG_LEVEL", "").lower() == "debug":
        print(f"{Colors.CYAN}[DEBUG]{Colors.RESET} {msg}")


def check_dependencies() -> bool:
    """Check if required tools are installed"""
    required = ["aria2c", "wimlib-imagex", "cabextract"]
    missing: list[str] = []
    for tool in required:
        if not shutil.which(tool):
            missing.append(tool)
    if missing:
        log_error(f"Missing required tools: {', '.join(missing)}")
        log_info("Run 'make deps' to install dependencies")
        return False
    return True


@overload
def fetch_url(
    url: str,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    return_json: Literal[False] = False,
) -> str | None: ...


@overload
def fetch_url(
    url: str,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    *,
    return_json: Literal[True],
) -> dict[str, Any] | None: ...


def fetch_url(
    url: str,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    return_json: bool = False,
) -> str | dict[str, Any] | None:
    """Fetch URL with error handling and optional caching"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    cache_key = f"{url}:{return_json}" if not data else None
    if cache_key and cache_key in _url_cache:
        return _url_cache[cache_key]

    try:
        client = _get_client()
        if data:
            payload = urlencode(data).encode("utf-8")
            response = client.post(url, headers=headers, content=payload)
        else:
            response = client.get(url, headers=headers)
        response.raise_for_status()
        text = response.text
        result: str | dict[str, Any] | None = text

        if return_json:
            try:
                parsed = orjson.loads(text)
            except orjson.JSONDecodeError as e:
                log_error(f"Failed to parse JSON response: {e}")
                return None
            if not isinstance(parsed, dict):
                log_error("JSON response is not an object")
                return None
            result = parsed

        if cache_key and result is not None:
            _url_cache[cache_key] = result

        return result
    except httpx.HTTPStatusError as e:
        log_error(f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}")
        return None
    except httpx.RequestError as e:
        log_error(f"URL Error: {e}")
        return None
    except OSError as e:
        log_error(f"Network error fetching URL: {e}")
        return None
    except Exception as e:  # noqa: BLE001 - last-resort guard so an unexpected error surfaces as a log line, not a crash
        log_error(f"Unexpected error fetching URL: {e}")
        return None


@overload
def _get_response_dict(data: dict[str, Any]) -> dict[str, Any] | None: ...


@overload
def _get_response_dict(
    data: dict[str, Any], default: dict[str, Any]
) -> dict[str, Any]: ...


def _get_response_dict(
    data: dict[str, Any], default: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Extract the 'response' field from API data with proper typing."""
    response = data.get("response")
    if isinstance(response, dict):
        return cast(dict[str, Any], response)
    return default


def get_latest_builds(max_results: int = 10) -> list[dict[str, Any]] | None:
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

    build_list: list[dict[str, Any]] = []
    for build_id, build_info in builds.items():
        build_info["id"] = build_id
        build_list.append(build_info)

    build_list.sort(key=lambda x: int(x.get("created") or 0), reverse=True)
    return build_list[:max_results]


def display_builds(builds: list[dict[str, Any]] | None) -> None:
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


def get_build_info(
    build_id: str, language: str | None = "en-us"
) -> dict[str, Any] | None:
    """Get detailed information about a specific build, optionally for a specific language"""
    log_info(f"Fetching build information for ID: {build_id}")

    params: dict[str, str] = {"id": build_id}
    if language:
        params["lang"] = language
    api_url = f"https://api.uupdump.net/get.php?{urlencode(params)}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    return _get_response_dict(data)


def get_available_editions(build_id: str) -> dict[str, Any] | None:
    """Get available editions for a specific build from the API"""
    log_info(f"Fetching available editions for build: {build_id}")

    params = {"id": build_id, "lang": "en-us"}
    api_url = f"https://api.uupdump.net/listeditions.php?{urlencode(params)}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        return None

    response_data = _get_response_dict(data, {})
    if response_data.get("error"):
        log_error(f"API Error: {response_data['error']}")
        return None

    return response_data


def get_available_languages(build_id: str | None = None) -> dict[str, Any] | None:
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

    return _get_response_dict(data, {})


def fetch_latest_from_wu(
    arch: str = "amd64", ring: str = "Retail"
) -> dict[str, Any] | None:
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

    return _get_response_dict(data, {})


def get_api_version() -> dict[str, Any] | None:
    """Get the current UUP dump API version"""
    api_url = "https://api.uupdump.net/"
    response = fetch_url(api_url)

    if not response:
        return None

    try:
        data = orjson.loads(response)
    except orjson.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response: {e}")
        return None

    if not isinstance(data, dict):
        return None

    return _get_response_dict(data, {})


def get_update_info(update_id: str) -> dict[str, Any] | None:
    """Get update information from updateinfo.php endpoint"""
    log_info(f"Fetching update info for ID: {update_id}")

    api_url = f"https://api.uupdump.net/updateinfo.php?id={update_id}"
    data = fetch_url(api_url, return_json=True)

    if not data:
        log_error(f"Failed to fetch update info for {update_id}")
        return None

    if data.get("response", {}).get("error"):
        log_error(f"API Error: {data['response']['error']}")
        return None

    return _get_response_dict(data, {})


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


def cache_get(key: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> Any | None:
    """Read a cached value if present and not expired."""
    cache_file = get_cache_dir() / _safe_cache_name(key)
    if not cache_file.exists():
        return None

    try:
        entry = orjson.loads(cache_file.read_bytes())
    except (orjson.JSONDecodeError, OSError) as e:
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
        cache_file.write_bytes(orjson.dumps(entry))
        return True
    except (OSError, TypeError) as e:
        log_warn(f"Cache write failed for {key}: {e}")
        return False


def cache_clear(key: str | None = None) -> int:
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
) -> list[dict[str, Any]] | None:
    """Fetch latest builds, returning a cached result when fresh enough."""
    cache_key = f"latest_builds_{max_results}"

    if not force_refresh:
        cached = cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

    builds = get_latest_builds(max_results)
    if builds is not None:
        cache_set(cache_key, builds)
    return builds


def get_build_info_cached(
    build_id: str,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
    language: str | None = "en-us",
) -> dict[str, Any] | None:
    """Fetch build info, returning a cached result when fresh enough."""
    cache_key = f"build_info_{build_id}"
    if language:
        cache_key = f"build_info_{build_id}_{language}"

    if not force_refresh:
        cached = cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cast(dict[str, Any], cached)

    info = get_build_info(build_id, language=language)
    if info is not None:
        cache_set(cache_key, info)
    return info


def download_language_packs(
    build_id: str,
    languages: list[str],
    output_dir: str | Path,
    edition_filter: list[str] | None = None,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
) -> bool:
    """Download language packs for a build."""
    log_info(f"Downloading language packs: {', '.join(languages)}")

    all_success = True
    for lang in languages:
        lang_output = Path(output_dir) / f"lang_{lang}"
        log_info(f"Fetching language pack: {lang}")

        lang_build_info = get_build_info_cached(
            build_id, ttl_seconds=cache_ttl, force_refresh=not use_cache, language=lang
        )

        if not lang_build_info:
            log_warn(f"No files found for language {lang}")
            all_success = False
            continue

        if not download_build(
            build_id,
            lang_output,
            edition_filter,
            build_info=lang_build_info,
            verbose=verbose,
            resume=True,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        ):
            all_success = False

    return all_success


def select_editions(build_info: dict[str, Any]) -> list[str] | None:
    """Allow user to select which editions to download"""
    files = build_info.get("files", {})

    # Find edition-specific ESD files
    edition_files: dict[str, str] = {}

    for filename in files:
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


def list_edition_files(build_info: dict[str, Any]) -> dict[str, str]:
    """Return the mapping of known edition name -> ESD filename from build info."""
    edition_files: dict[str, str] = {}
    files = build_info.get("files", {})
    for filename in files:
        if not filename.endswith(".esd"):
            continue
        lower = filename.lower()
        for key in ("professional", "enterprise", "home", "core", "education"):
            if key in lower:
                edition_files[key] = filename
                break
    return edition_files


def resolve_edition_filter(
    build_info: dict[str, Any],
    edition: str | None = None,
) -> list[str] | None:
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

    log_error(
        f"Unknown edition '{edition}'. Available: {', '.join(edition_files.keys())}"
    )
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


# Mirror sources for redundant downloads
# These are alternative CDN endpoints (UUP dump has no official mirrors, but
# users can configure custom mirrors for redundancy in restricted networks)
DEFAULT_MIRRORS: list[str] = [
    "https://uupdump.net/get.php",
]

# User-configurable mirror file
MIRROR_CONFIG_FILE: str = ".uup-mirrors"


def load_mirrors() -> list[str]:
    """Load custom mirrors from .uup-mirrors file or return defaults."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    mirror_path = project_root / MIRROR_CONFIG_FILE

    if mirror_path.exists():
        try:
            with open(mirror_path, encoding="utf-8") as f:
                mirrors = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
            if mirrors:
                return mirrors
        except OSError:
            pass
    return DEFAULT_MIRRORS


def _prepare_download_list(
    build_id: str,
    files: dict[str, Any],
    edition_filter: list[str] | None = None,
    mirrors: list[str] | None = None,
    delta_filter: set[str] | None = None,
) -> list[dict[str, Any]]:
    download_list: list[dict[str, Any]] = []
    base_urls = mirrors if mirrors else load_mirrors()
    primary_url = base_urls[0] if base_urls else "https://uupdump.net/get.php"

    for filename, file_info in files.items():
        if (
            edition_filter
            and filename.endswith(".esd")
            and filename not in edition_filter
        ):
            continue
        if delta_filter is not None and filename not in delta_filter:
            continue
        file_url = f"{primary_url}?id={build_id}&pack={filename}&aria2=2"
        download_list.append(
            {"url": file_url, "name": filename, "size": file_info.get("size", 0)}
        )
    return download_list


# Default on-disk location for delta manifests (per-build file lists). Set
# via --delta-store. Files are JSON objects keyed by filename.
DEFAULT_DELTA_STORE: str = ".uup-delta"


def get_build_files(build_info: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract the per-file metadata from a build info dict.

    Returns a mapping of ``filename -> {size, sha256, ...}`` for every entry in
    ``build_info['files']``. Only entries that are mappings are preserved so a
    malformed value does not crash downstream consumers.

    The returned dict is suitable for passing to :func:`calculate_delta` or
    :func:`save_delta_manifest`.
    """
    raw_files: Any = build_info.get("files", {})
    if not isinstance(raw_files, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for filename, info in raw_files.items():
        if not isinstance(filename, str) or not isinstance(info, dict):
            continue
        result[filename] = dict(info)
    return result


def calculate_delta(
    base_files: dict[str, dict[str, Any]],
    target_files: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """Compare two file lists and classify each file by change type.

    The returned dict has four keys:
    - ``added``: filenames present in ``target_files`` but not in ``base_files``
    - ``removed``: filenames present in ``base_files`` but not in ``target_files``
    - ``modified``: filenames present in both, with a different ``size`` or
      ``sha256`` (or any other top-level key) value
    - ``unchanged``: filenames present in both with identical metadata

    A file is treated as ``modified`` if any of its metadata keys differ; this
    is conservative but correct in the absence of a guaranteed per-file
    checksum.
    """
    base_keys = set(base_files.keys())
    target_keys = set(target_files.keys())

    added: list[str] = sorted(target_keys - base_keys)
    removed: list[str] = sorted(base_keys - target_keys)

    common = base_keys & target_keys
    modified: list[str] = []
    unchanged: list[str] = []
    for name in sorted(common):
        if base_files[name] != target_files[name]:
            modified.append(name)
        else:
            unchanged.append(name)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
    }


def get_delta_store_path(store_dir: str | Path | None = None) -> Path:
    """Return the path to the local delta-manifest store, creating it if needed.

    The store is intentionally outside the project root in spirit (it is a
    runtime cache of file lists), but the default keeps it alongside the
    ``.uup_cache`` directory in the project root for simplicity.
    """
    if store_dir is None:
        project_root = Path(__file__).resolve().parent.parent
        path = project_root / DEFAULT_DELTA_STORE
    else:
        path = Path(store_dir)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            path = project_root / path
    try:
        path = path.resolve()
    except OSError, RuntimeError:
        return path
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log_warn(f"Could not create delta store at {path}: {exc}")
    return path


def _safe_delta_filename(build_id: str) -> str:
    """Return a filesystem-safe filename for a delta manifest.

    Aggressively replaces any non-alphanumeric character (including ``.`` and
    path separators) with ``_`` to prevent path-traversal issues when a
    caller-supplied build ID contains ``..`` or ``/``.
    """
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in build_id)
    return f"{safe[:128]}.json"


def save_delta_manifest(
    build_id: str,
    files: dict[str, dict[str, Any]],
    store_dir: str | Path | None = None,
) -> Path | None:
    """Persist a build's file list to the local delta store.

    Returns the manifest path on success, or ``None`` on failure. The manifest
    is a JSON object with ``build_id``, ``saved_at`` (unix timestamp), and
    ``files`` keys.
    """
    store_path = get_delta_store_path(store_dir)
    manifest_path = store_path / _safe_delta_filename(build_id)
    payload = {
        "build_id": build_id,
        "saved_at": time.time(),
        "files": files,
    }
    try:
        manifest_path.write_bytes(
            orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
        )
        return manifest_path
    except (OSError, TypeError) as exc:
        log_error(f"Failed to save delta manifest for {build_id}: {exc}")
        return None


def load_delta_manifest(
    build_id: str,
    store_dir: str | Path | None = None,
) -> dict[str, dict[str, Any]] | None:
    """Load a previously saved delta manifest for ``build_id``.

    Returns the ``files`` mapping, or ``None`` if the manifest is missing or
    malformed. The resolved manifest path is verified to be inside the
    resolved store directory to prevent path traversal via a malicious
    ``build_id``.
    """
    store_path = get_delta_store_path(store_dir)
    safe_name = _safe_delta_filename(build_id)
    manifest_path = (store_path / safe_name).resolve()

    try:
        store_resolved = store_path.resolve()
    except OSError, RuntimeError:
        return None

    try:
        manifest_path.relative_to(store_resolved)
    except ValueError, RuntimeError:
        log_error("Delta manifest path is outside the delta store")
        return None

    if not manifest_path.exists():
        return None
    try:
        data: Any = orjson.loads(manifest_path.read_bytes())
    except (OSError, orjson.JSONDecodeError) as exc:
        log_warn(f"Failed to read delta manifest for {build_id}: {exc}")
        return None
    if not isinstance(data, dict):
        return None
    files: Any = data.get("files", {})
    if not isinstance(files, dict):
        return None
    result: dict[str, dict[str, Any]] = {}
    for name, info in files.items():
        if isinstance(name, str) and isinstance(info, dict):
            result[name] = cast(dict[str, Any], info)
    return result


def compute_changed_files(
    base_files: dict[str, dict[str, Any]],
    target_files: dict[str, dict[str, Any]],
) -> set[str]:
    """Return the set of filenames that need to be re-downloaded.

    Equivalent to ``added | modified`` from :func:`calculate_delta`. This is
    the convenience helper used by the download pipeline when filtering a
    download list for a delta build.
    """
    delta = calculate_delta(base_files, target_files)
    return set(delta["added"]) | set(delta["modified"])


def format_delta_summary(
    base_id: str,
    target_id: str,
    delta: dict[str, list[str]],
) -> str:
    """Format a human-readable summary of a delta for CLI output."""
    lines = [
        f"Delta: {base_id} -> {target_id}",
        f"  added:    {len(delta['added'])}",
        f"  modified: {len(delta['modified'])}",
        f"  removed:  {len(delta['removed'])}",
        f"  unchanged:{len(delta['unchanged'])}",
        f"  to download: {len(delta['added']) + len(delta['modified'])}",
    ]
    return "\n".join(lines)


def _run_aria2_download(
    output_path: Path,
    aria2_input: Path,
    download_list: list[dict[str, Any]],
    verbose: bool = False,
    resume: bool = True,
) -> bool:
    import subprocess

    session_file = output_path / ".aria2_session"
    aria2_log = output_path / ".aria2.log"

    try:
        lines = []
        for item in download_list:
            raw_name = str(item["name"])
            if ".." in raw_name or "/" in raw_name or "\\" in raw_name:
                log_error(f"Invalid filename detected: {raw_name}")
                return False
            sanitized_name = str(Path(raw_name).name)
            url = str(item["url"])
            if "\n" in url or "\r" in url:
                url = url.replace("\n", "").replace("\r", "")

            name = sanitized_name
            if "\n" in name or "\r" in name:
                name = name.replace("\n", "").replace("\r", "")
            lines.append(f"{url}\n  out={name}")

        with open(aria2_input, "w") as fh:
            fh.write("\n".join(lines))

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
        if resume:
            cmd.extend(
                [
                    "--save-session",
                    str(session_file),
                    "--save-session-interval",
                    "60",
                ]
            )
        if verbose:
            cmd.append("--log")
            cmd.append(str(aria2_log))
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
        # Clean up session file on success
        try:
            session_file.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Download failed with exit code {e.returncode}")
        if verbose and e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            stderr_lines = e.stderr.splitlines()
            tail = stderr_lines if verbose else stderr_lines[-20:]
            for line in tail:
                print(f"stderr: {line}")
        return False
    except KeyboardInterrupt:
        log_warn("\nDownload cancelled by user - session saved for resume")
        return False
    except OSError as e:
        log_error(f"System error during download: {e}")
        return False
    except Exception as e:  # noqa: BLE001 - last-resort guard so an unexpected error surfaces as a log line, not a crash
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
    output_dir: str | Path,
    edition_filter: list[str] | None = None,
    build_info: dict[str, Any] | None = None,
    verbose: bool = False,
    resume: bool = True,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    mirrors: list[str] | None = None,
    language: str | None = "en-us",
    delta_from: str | None = None,
    delta_store: str | Path | None = None,
) -> bool:
    """Download UUP files for a specific build

    If ``delta_from`` is provided and a previously saved manifest exists in the
    delta store for that build, only the files that have been added or modified
    (compared to the saved manifest) are downloaded. A fresh manifest for
    ``build_id`` is written to the delta store after a successful download so
    subsequent delta runs have a baseline.
    """
    if build_info is None:
        build_info = get_build_info_cached(
            build_id,
            ttl_seconds=cache_ttl,
            force_refresh=not use_cache,
            language=language,
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

    target_files = get_build_files(build_info)
    delta_filter: set[str] | None = None
    if delta_from:
        base_files = load_delta_manifest(delta_from, store_dir=delta_store)
        if base_files is None:
            log_warn(
                f"No saved delta manifest for build {delta_from}; "
                "downloading all files (full set)"
            )
        else:
            delta = calculate_delta(base_files, target_files)
            log_info(
                f"Delta vs {delta_from}: +{len(delta['added'])} added, "
                f"~{len(delta['modified'])} modified, "
                f"-{len(delta['removed'])} removed"
            )
            delta_filter = set(delta["added"]) | set(delta["modified"])
            if not delta_filter:
                log_success(f"No changes detected vs {delta_from}; nothing to download")
                save_delta_manifest(build_id, target_files, store_dir=delta_store)
                return True

    log_info(f"Preparing to download {len(files)} files...")
    download_list = _prepare_download_list(
        build_id, files, edition_filter, mirrors=mirrors, delta_filter=delta_filter
    )

    if not download_list:
        log_error("No files to download after filtering")
        return False

    log_success(f"Will download {len(download_list)} files")

    aria2_input = output_path / "aria2_input.txt"
    ok = _run_aria2_download(
        output_path, aria2_input, download_list, verbose=verbose, resume=resume
    )
    if ok and delta_filter is not None:
        save_delta_manifest(build_id, target_files, store_dir=delta_store)
    elif ok:
        # Always update the manifest so future delta runs have a baseline
        save_delta_manifest(build_id, target_files, store_dir=delta_store)
    return ok


def _process_selected_build(
    selected_build: dict[str, Any],
    output_dir: str | Path,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    edition: str | None = None,
    mirrors: list[str] | None = None,
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
            resume=True,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            mirrors=mirrors,
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
            resume=True,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            mirrors=mirrors,
        )
    else:
        log_info("Download cancelled")
        return False


def interactive_mode(
    output_dir: str | Path,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    edition: str | None = None,
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


def get_profiles() -> dict[str, dict[str, Any]]:
    """Load build profiles from config file or return built-in defaults."""
    script_dir = Path(__file__).parent
    profiles_path = script_dir.parent / "config" / "profiles.json"

    if profiles_path.exists():
        try:
            data = orjson.loads(profiles_path.read_bytes())
            if isinstance(data, dict):
                profiles = data.get("profiles", PROFILES)
                if isinstance(profiles, dict):
                    return profiles
        except orjson.JSONDecodeError, OSError:
            log_warn("Failed to load profiles.json, using built-in profiles")

    return PROFILES


def get_pinned_build() -> dict[str, Any] | None:
    """Load pinned build configuration from .uup-pin.json in the project root."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pin_path = project_root / ".uup-pin.json"

    if not pin_path.exists():
        return None

    try:
        data = orjson.loads(pin_path.read_bytes())
        if isinstance(data, dict) and "build_id" in data:
            return data
        log_warn("Invalid pin file: missing 'build_id'")
        return None
    except (orjson.JSONDecodeError, OSError) as e:
        log_warn(f"Failed to read pin file: {e}")
        return None


def save_pinned_build(
    build_id: str,
    title: str | None = None,
    edition: str | None = None,
) -> bool:
    """Save a build as the pinned version for reproducibility."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pin_path = project_root / ".uup-pin.json"

    data: dict[str, Any] = {"build_id": build_id}
    if title:
        data["title"] = title
    if edition:
        data["edition"] = edition

    try:
        pin_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
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


def get_profile(name: str) -> dict[str, Any] | None:
    """Get a specific build profile by name."""
    profiles = get_profiles()
    return profiles.get(name)


def load_component_groups(path: str | None = None) -> dict[str, Any]:
    """Load component groups from config/component_groups.json.

    Returns a dict mapping group name -> {"description": str, "patterns": List[str]}.
    Returns an empty dict if the file is missing, malformed, or has unexpected shape.
    """
    if path is None:
        path = COMPONENT_GROUPS_FILE
    try:
        data: Any = orjson.loads(Path(path).read_bytes())
    except (OSError, orjson.JSONDecodeError, ValueError) as exc:
        log_warn(f"Could not load component groups from {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        log_warn(f"Component groups file {path} is not a JSON object")
        return {}
    raw_groups: Any = data.get("groups", data)
    if not isinstance(raw_groups, dict):
        log_warn(f"Component groups in {path} are not a mapping")
        return {}
    result: dict[str, Any] = {}
    for name, body in raw_groups.items():
        if not isinstance(name, str) or not isinstance(body, dict):
            continue
        patterns: Any = body.get("patterns", [])
        if not isinstance(patterns, list):
            continue
        cleaned: list[str] = [p for p in patterns if isinstance(p, str) and p]
        if not cleaned:
            continue
        description: str = (
            body.get("description", "")
            if isinstance(body.get("description"), str)
            else ""
        )
        result[name] = {"description": description, "patterns": cleaned}
    return result


def list_component_groups(path: str | None = None) -> list[str]:
    """Return the names of all available component groups (sorted)."""
    groups = load_component_groups(path)
    return sorted(groups.keys())


def get_component_group(name: str, path: str | None = None) -> dict[str, Any] | None:
    """Get a single component group by name, or None if not found."""
    groups = load_component_groups(path)
    return groups.get(name)


def validate_component_groups(names: list[str], path: str | None = None) -> list[str]:
    """Return the subset of `names` that exist in the component groups file.

    Logs a warning for any names that are unknown.
    """
    available = set(list_component_groups(path))
    valid: list[str] = []
    for name in names:
        if name in available:
            valid.append(name)
        else:
            log_warn(f"Unknown component group: {name}")
    return valid


def collect_component_patterns(
    group_names: list[str], path: str | None = None
) -> list[str]:
    """Collect deduplicated glob patterns from the given component groups.

    Order is preserved (group order, then pattern order within each group).
    """
    seen: set[str] = set()
    combined: list[str] = []
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
    group_names: list[str], output_path: str = ".uup-groups"
) -> bool:
    """Write the selected component groups to a file consumable by the build pipeline.

    The output file is a simple newline-separated list of group names.
    Returns True on success, False on failure.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(f"{name}\n" for name in group_names)
        return True
    except OSError as exc:
        log_error(f"Could not write component groups file {output_path}: {exc}")
        return False


def display_component_groups(path: str | None = None) -> None:
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


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
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
        "--verbose",
        action="store_true",
        help="Show verbose output including aria2c stderr/stdout",
    )

    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        default=True,
        help="Disable aria2c session persistence for resuming interrupted downloads",
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
        "--mirrors",
        dest="mirrors",
        help="Custom comma-separated list of mirror URLs (for restricted networks)",
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

    parser.add_argument(
        "--update-info",
        metavar="ID",
        dest="update_info",
        help="Fetch update information for a specific update ID and exit",
    )

    parser.add_argument(
        "--language",
        dest="language",
        help="Language pack to download (e.g., en-us, fr-fr, de-de). Use with --build-id.",
    )

    parser.add_argument(
        "--languages-download",
        dest="languages_download",
        help="Comma-separated languages to download for multi-language ISO (e.g., en-us,fr-fr,de-de)",
    )

    parser.add_argument(
        "--delta-from",
        metavar="BUILD_ID",
        dest="delta_from",
        help=(
            "Only download files that have been added or modified compared to a "
            "previous build. BUILD_ID must have a saved manifest in the delta store."
        ),
    )

    parser.add_argument(
        "--delta-store",
        metavar="DIR",
        dest="delta_store",
        help=(
            f"Directory used to store per-build file manifests for delta downloads "
            f"(default: {DEFAULT_DELTA_STORE})"
        ),
    )

    parser.add_argument(
        "--save-delta-manifest",
        metavar="BUILD_ID",
        dest="save_delta_manifest",
        help=(
            "Fetch a build's file list from the API and save it to the delta store, "
            "then exit. Useful for seeding a baseline for future --delta-from runs."
        ),
    )

    parser.add_argument(
        "--delta-info",
        metavar="BUILD_ID",
        dest="delta_info",
        help=("Show information about the saved delta manifest for BUILD_ID and exit."),
    )

    return parser.parse_args(args)


def _handle_info_mode(args: argparse.Namespace) -> int | None:
    """Handles info-only modes and returns the appropriate exit code. Returns None if not handled."""
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

    # Update info mode
    if args.update_info:
        info = get_update_info(args.update_info)
        if info:
            print(f"\n{Colors.BOLD}Update Information:{Colors.RESET}\n")
            print(f"  {orjson.dumps(info, option=orjson.OPT_INDENT_2).decode()}")
            return 0
        return 1

    # Save delta manifest mode
    if args.save_delta_manifest:
        build_id = args.save_delta_manifest
        build_info = get_build_info_cached(
            build_id, ttl_seconds=args.cache_ttl, force_refresh=args.no_cache
        )
        if not build_info:
            log_error(f"Failed to get build information for {build_id}")
            return 1
        files = get_build_files(build_info)
        if not files:
            log_error(f"No files found for build {build_id}")
            return 1
        manifest_path = save_delta_manifest(build_id, files, store_dir=args.delta_store)
        if manifest_path:
            log_success(
                f"Saved delta manifest for {build_id} ({len(files)} files) "
                f"to {manifest_path}"
            )
            return 0
        return 1

    # Delta info mode
    if args.delta_info:
        files = load_delta_manifest(args.delta_info, store_dir=args.delta_store)
        if files is None:
            log_warn(
                f"No saved delta manifest for build {args.delta_info} "
                f"in store {args.delta_store or DEFAULT_DELTA_STORE}"
            )
            return 1
        print(f"\n{Colors.BOLD}Delta Manifest:{Colors.RESET} {args.delta_info}\n")
        print(f"  Files: {len(files)}")
        total_size = sum(
            int(info.get("size", 0))
            for info in files.values()
            if isinstance(info, dict)
        )
        print(f"  Total size: {total_size} bytes")
        return 0

    return None


def _resolve_output_dir(output_arg: str) -> Path | None:
    """Resolves and validates the output directory to prevent traversal."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Security: Resolve and validate output path to prevent traversal
    output_dir = Path(output_arg)
    if not output_dir.is_absolute():
        output_dir = project_root.joinpath(output_dir)

    try:
        output_dir.resolve().relative_to(project_root.resolve())
    except ValueError, RuntimeError:
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
        names: list[str] = []
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
            log_error(
                "No pinned build found. Use --pin-build with --build-id to create one."
            )
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
            if valid_profile_groups and write_component_groups_for_build(
                valid_profile_groups
            ):
                log_info(
                    f"Component groups for build: {', '.join(valid_profile_groups)}"
                )

    # Handle --groups override (always wins over profile defaults)
    if args.groups:
        cli_groups = [n.strip() for n in args.groups.split(",") if n.strip()]
        valid_cli_groups = validate_component_groups(cli_groups)
        if valid_cli_groups and write_component_groups_for_build(valid_cli_groups):
            log_info(f"Component groups (from --groups): {', '.join(valid_cli_groups)}")

    # Note: verbose is not info_only - it affects download behavior
    info_only_mode = (
        args.editions
        or args.languages is not None
        or args.latest
        or args.save_delta_manifest is not None
        or args.delta_info is not None
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

    # Mirrors mode: parse --mirrors option
    custom_mirrors: list[str] | None = None
    if args.mirrors:
        custom_mirrors = [m.strip() for m in args.mirrors.split(",") if m.strip()]
        log_info(f"Using {len(custom_mirrors)} custom mirror(s)")

    # Direct build ID mode
    if args.build_id:
        log_info(f"Downloading build ID: {args.build_id}")
        edition_filter: list[str] | None = None
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

        # Handle multi-language download
        if args.languages_download:
            langs = [
                lang.strip()
                for lang in args.languages_download.split(",")
                if lang.strip()
            ]
            if langs:
                success = download_language_packs(
                    args.build_id,
                    langs,
                    output_dir,
                    edition_filter,
                    verbose=args.verbose,
                    use_cache=not args.no_cache,
                    cache_ttl=args.cache_ttl,
                )
                return 0 if success else 1
            log_error("No valid languages specified for download")
            return 1

        success = download_build(
            args.build_id,
            output_dir,
            edition_filter,
            verbose=args.verbose,
            resume=args.resume,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
            mirrors=custom_mirrors,
            delta_from=args.delta_from,
            delta_store=args.delta_store,
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
