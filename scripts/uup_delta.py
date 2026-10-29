"""uup_delta.py - Per-build file manifests and delta calculation for UUP downloads.

Owns the on-disk delta store (a directory of JSON manifests, one per build) and the
comparison of two file lists. download_uup.py decides *when* to use a delta; this
module decides what a delta is and keeps manifest paths inside the store.
"""

import time
from pathlib import Path
from typing import Any, cast

import orjson
from pyutils import log_error, log_warn

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
