#!/usr/bin/env python3
"""uupdump.net API client: HTTP fetch, JSON endpoints and the on-disk metadata cache."""

import time
from pathlib import Path
from typing import Any, Literal, cast, overload
from urllib.parse import urlencode

import httpx
import orjson
from pyutils import log_error, log_info, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


CACHE_DIR_NAME: str = ".uup_cache"
DEFAULT_CACHE_TTL_SECONDS: int = 3600

_url_cache: dict[str, str | dict[str, Any]] = {}
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Return the shared httpx client, creating it on first use."""
    global _client
    if _client is None:
        _client = httpx.Client(http2=True, timeout=30.0, follow_redirects=True)
    return _client


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
    cache_dir = PROJECT_ROOT / CACHE_DIR_NAME
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
