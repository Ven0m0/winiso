"""UUP file download: edition filtering, output-dir guard, delta filter and aria2c."""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import uup_api
import uup_delta
from pyutils import BOLD, CYAN, NC, YELLOW, log_error, log_info, log_success, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def download_language_packs(
    build_id: str,
    languages: list[str],
    output_dir: str | Path,
    edition_filter: list[str] | None = None,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = uup_api.DEFAULT_CACHE_TTL_SECONDS,
) -> bool:
    """Download language packs for a build."""
    log_info(f"Downloading language packs: {', '.join(languages)}")

    all_success = True
    for lang in languages:
        lang_output = Path(output_dir) / f"lang_{lang}"
        log_info(f"Fetching language pack: {lang}")

        lang_build_info = uup_api.get_build_info_cached(
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


def select_editions(
    build_info: dict[str, Any], ask: Callable[[str], str] | None = None
) -> list[str] | None:
    """Allow user to select which editions to download"""
    edition_files = list_edition_files(build_info)
    if not edition_files:
        log_warn("No edition-specific files found, will download all files")
        return None

    print(f"\n{BOLD}Available Editions:{NC}\n")
    editions = list(edition_files.keys())
    for i, edition in enumerate(editions, 1):
        print(f"{CYAN}[{i}]{NC} {edition}")
    print(f"{CYAN}[A]{NC} All editions (default)")

    choice = (ask or input)(f"\n{BOLD}Select edition [A]:{NC} ").strip().upper()

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


def _is_within(path: Path, root: Path) -> bool:
    """True if ``path`` resolves to ``root`` or somewhere below it.

    The one containment check behind both output-directory guards (cwd in
    download_build, project root in _resolve_output_dir).
    """
    try:
        _ = path.resolve().relative_to(root.resolve())
    except ValueError, RuntimeError:
        return False
    return True


def _prepare_output_directory(
    output_path: Path, ask: Callable[[str], str] | None = None
) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    existing_files = list(output_path.glob("*"))
    if existing_files:
        print(
            f"\n{YELLOW}Warning:{NC} {len(existing_files)} files exist in {output_path}"
        )
        response = (ask or input)("Clear existing files? [y/N]: ").strip().lower()
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
    mirror_path = PROJECT_ROOT / MIRROR_CONFIG_FILE

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


def _run_aria2_download(
    output_path: Path,
    aria2_input: Path,
    download_list: list[dict[str, Any]],
    verbose: bool = False,
    resume: bool = True,
) -> bool:

    session_file = output_path / ".aria2_session"
    aria2_log = output_path / ".aria2.log"

    try:
        lines = []
        for item in download_list:
            raw_name = str(item["name"])
            if ".." in raw_name or "/" in raw_name or "\\" in raw_name:
                log_error(f"Invalid filename detected: {raw_name}")
                return False
            # CR/LF would inject extra directives into the aria2c input file.
            url = str(item["url"]).replace("\n", "").replace("\r", "")
            name = Path(raw_name).name.replace("\n", "").replace("\r", "")
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
    cache_ttl: int = uup_api.DEFAULT_CACHE_TTL_SECONDS,
    mirrors: list[str] | None = None,
    language: str | None = "en-us",
    delta_from: str | None = None,
    delta_store: str | Path | None = None,
    ask: Callable[[str], str] | None = None,
) -> bool:
    """Download UUP files for a specific build

    If ``delta_from`` is provided and a previously saved manifest exists in the
    delta store for that build, only the files that have been added or modified
    (compared to the saved manifest) are downloaded. A fresh manifest for
    ``build_id`` is written to the delta store after a successful download so
    subsequent delta runs have a baseline.
    """
    if build_info is None:
        build_info = uup_api.get_build_info_cached(
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

    if not _is_within(output_path, Path.cwd()):
        log_error("Output directory must be within the current directory")
        return False

    _prepare_output_directory(output_path, ask)

    target_files = uup_delta.get_build_files(build_info)
    delta_filter: set[str] | None = None
    if delta_from:
        base_files = uup_delta.load_delta_manifest(delta_from, store_dir=delta_store)
        if base_files is None:
            log_warn(
                f"No saved delta manifest for build {delta_from}; "
                "downloading all files (full set)"
            )
        else:
            delta = uup_delta.calculate_delta(base_files, target_files)
            log_info(
                f"Delta vs {delta_from}: +{len(delta['added'])} added, "
                f"~{len(delta['modified'])} modified, "
                f"-{len(delta['removed'])} removed"
            )
            delta_filter = set(delta["added"]) | set(delta["modified"])
            if not delta_filter:
                log_success(f"No changes detected vs {delta_from}; nothing to download")
                uup_delta.save_delta_manifest(
                    build_id, target_files, store_dir=delta_store
                )
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
    if ok:
        # Always update the manifest so future delta runs have a baseline
        uup_delta.save_delta_manifest(build_id, target_files, store_dir=delta_store)
    return ok
