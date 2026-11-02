#!/usr/bin/env python3
"""UUP File Downloader for Windows 11 ISO Builder - command-line entry point.

Talks to uupdump.net through uup_api and downloads through uup_download.
"""

import argparse
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import keep_list
import orjson
import uup_api
import uup_delta
import uup_download
from pyutils import BOLD, CYAN, NC, log_error, log_info, log_success, log_warn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROFILES_FILE = PROJECT_ROOT / "config" / "profiles.json"
PIN_FILE = PROJECT_ROOT / ".uup-pin.json"


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


def display_builds(builds: list[dict[str, Any]] | None) -> None:
    """Display builds in a user-friendly format"""
    if not builds:
        log_warn("No builds available.")
        return

    print(f"\n{BOLD}Available Windows 11 Builds:{NC}\n")

    for i, build in enumerate(builds, 1):
        title = build.get("title", "Unknown")
        build_num = build.get("build", "N/A")
        arch = build.get("arch", "N/A")
        created = build.get("created", "N/A")

        print(f"{CYAN}[{i}]{NC} {title}")
        print(f"    Build: {build_num} | Arch: {arch} | Created: {created}")
        print()


def _process_selected_build(
    selected_build: dict[str, Any],
    output_dir: str | Path,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = uup_api.DEFAULT_CACHE_TTL_SECONDS,
    edition: str | None = None,
    mirrors: list[str] | None = None,
    ask: Callable[[str], str] | None = None,
) -> bool:
    """Process the selected build for download."""
    build_id = selected_build["id"]

    print(f"\n{BOLD}Selected:{NC} {selected_build.get('title', 'Unknown')}")
    print(f"{BOLD}Build ID:{NC} {build_id}")

    # Fetch build info once
    build_info = uup_api.get_build_info_cached(
        build_id, ttl_seconds=cache_ttl, force_refresh=not use_cache
    )
    if not build_info:
        log_error("Failed to get build information")
        return False

    # Resolve edition: non-interactive if --edition was supplied, else prompt
    if edition:
        edition_filter = uup_download.resolve_edition_filter(build_info, edition)
    else:
        edition_filter = uup_download.select_editions(build_info, ask)

    if edition:
        # Non-interactive: skip the confirmation prompt
        return uup_download.download_build(
            build_id,
            output_dir,
            edition_filter,
            build_info=build_info,
            verbose=verbose,
            resume=True,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            mirrors=mirrors,
            ask=ask,
        )

    confirm = (
        (ask or input)(f"\n{BOLD}Proceed with download? [Y/n]:{NC} ").strip().lower()
    )
    if confirm in ("", "y", "yes"):
        return uup_download.download_build(
            build_id,
            output_dir,
            edition_filter,
            build_info=build_info,
            verbose=verbose,
            resume=True,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            mirrors=mirrors,
            ask=ask,
        )
    else:
        log_info("Download cancelled")
        return False


def interactive_mode(
    output_dir: str | Path,
    verbose: bool = False,
    use_cache: bool = True,
    cache_ttl: int = uup_api.DEFAULT_CACHE_TTL_SECONDS,
    edition: str | None = None,
    ask: Callable[[str], str] | None = None,
) -> bool:
    """Interactive mode for selecting and downloading builds"""
    print(f"\n{BOLD}UUP File Downloader for Windows 11{NC}")
    print("=" * 50)

    builds = uup_api.get_latest_builds_cached(
        ttl_seconds=cache_ttl, force_refresh=not use_cache
    )
    if not builds:
        log_error("Failed to fetch builds")
        return False

    display_builds(builds)

    while True:
        try:
            choice = (ask or input)(
                f"{BOLD}Select build number [1-{len(builds)}] or 'q' to quit:{NC} "
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
                    ask=ask,
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
    """Load build profiles from config/profiles.json (the single source of truth)."""
    try:
        data = orjson.loads(PROFILES_FILE.read_bytes())
    except (orjson.JSONDecodeError, OSError) as e:
        log_warn(f"Failed to load {PROFILES_FILE}: {e}")
        return {}
    profiles = data.get("profiles") if isinstance(data, dict) else None
    return profiles if isinstance(profiles, dict) else {}


def get_pinned_build() -> dict[str, Any] | None:
    """Load pinned build configuration from .uup-pin.json in the project root."""
    pin_path = PIN_FILE

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
    pin_path = PIN_FILE

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

    print(f"\n{BOLD}Available Build Profiles:{NC}\n")

    for name, profile in profiles.items():
        description = profile.get("description", "No description")
        edition = profile.get("edition", "N/A")
        print(f"{CYAN}[{name}]{NC} {description}")
        print(f"    Edition: {edition}")
        print()


def get_profile(name: str) -> dict[str, Any] | None:
    """Get a specific build profile by name."""
    profiles = get_profiles()
    return profiles.get(name)


def display_component_groups(path: str | None = None) -> None:
    """Print all available component groups with descriptions to stdout."""
    groups = keep_list.load_component_groups(path)
    if not groups:
        print("No component groups available.")
        return
    print(f"\n{BOLD}Available Component Groups:{NC}\n")
    for name in sorted(groups.keys()):
        description = groups[name].get("description", "")
        pattern_count = len(groups[name].get("patterns", []))
        print(f"  {CYAN}{name}{NC} ({pattern_count} patterns)")
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
        default=uup_api.DEFAULT_CACHE_TTL_SECONDS,
        help=f"Cache TTL in seconds (default: {uup_api.DEFAULT_CACHE_TTL_SECONDS})",
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
            f"(default: {uup_delta.DEFAULT_DELTA_STORE})"
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
        editions_info = uup_api.get_available_editions(args.editions)
        if editions_info:
            print(f"\n{BOLD}Available Editions for Build:{NC}\n")
            edition_list = editions_info.get("editionList", [])
            fancy_names = editions_info.get("editionFancyNames", {})
            for edition in edition_list:
                fancy_name = fancy_names.get(edition, edition)
                print(f"  {CYAN}{edition}{NC} - {fancy_name}")
            return 0
        return 1

    # List languages mode
    if args.languages is not None:
        langs_info = uup_api.get_available_languages(args.languages or None)
        if langs_info:
            print(f"\n{BOLD}Available Languages:{NC}\n")
            lang_list = langs_info.get("langList", [])
            fancy_names = langs_info.get("langFancyNames", {})
            for lang in lang_list:
                fancy_name = fancy_names.get(lang, lang)
                print(f"  {CYAN}{lang}{NC} - {fancy_name}")
            return 0
        return 1

    # Fetch latest from Windows Update
    if args.latest:
        latest_info = uup_api.fetch_latest_from_wu(args.arch, args.ring)
        if latest_info:
            print(f"\n{BOLD}Latest Build from Windows Update:{NC}\n")
            print(f"  Update ID: {latest_info.get('updateId', 'N/A')}")
            print(f"  Title: {latest_info.get('updateTitle', 'N/A')}")
            print(f"  Build: {latest_info.get('foundBuild', 'N/A')}")
            print(f"  Arch: {latest_info.get('arch', 'N/A')}")
            return 0
        return 1

    # Update info mode
    if args.update_info:
        info = uup_api.get_update_info(args.update_info)
        if info:
            print(f"\n{BOLD}Update Information:{NC}\n")
            print(f"  {orjson.dumps(info, option=orjson.OPT_INDENT_2).decode()}")
            return 0
        return 1

    # Save delta manifest mode
    if args.save_delta_manifest:
        build_id = args.save_delta_manifest
        build_info = uup_api.get_build_info_cached(
            build_id, ttl_seconds=args.cache_ttl, force_refresh=args.no_cache
        )
        if not build_info:
            log_error(f"Failed to get build information for {build_id}")
            return 1
        files = uup_delta.get_build_files(build_info)
        if not files:
            log_error(f"No files found for build {build_id}")
            return 1
        manifest_path = uup_delta.save_delta_manifest(
            build_id, files, store_dir=args.delta_store
        )
        if manifest_path:
            log_success(
                f"Saved delta manifest for {build_id} ({len(files)} files) "
                f"to {manifest_path}"
            )
            return 0
        return 1

    # Delta info mode
    if args.delta_info:
        files = uup_delta.load_delta_manifest(
            args.delta_info, store_dir=args.delta_store
        )
        if files is None:
            log_warn(
                f"No saved delta manifest for build {args.delta_info} "
                f"in store {args.delta_store or uup_delta.DEFAULT_DELTA_STORE}"
            )
            return 1
        print(f"\n{BOLD}Delta Manifest:{NC} {args.delta_info}\n")
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

    # Security: Resolve and validate output path to prevent traversal
    output_dir = Path(output_arg)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT.joinpath(output_dir)

    if not uup_download._is_within(output_dir, PROJECT_ROOT):
        log_error(f"Path traversal attempt detected for output: {output_arg}")
        return None

    return output_dir


def main() -> int:
    args = parse_args()

    # Handle --clear-cache mode
    if args.clear_cache:
        count = uup_api.cache_clear()
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
        valid = keep_list.validate_component_groups(names)
        if not valid:
            return 1
        if keep_list.write_group_selection(valid, args.write_groups):
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
            valid_profile_groups = keep_list.validate_component_groups(profile_groups)
            if valid_profile_groups and keep_list.write_group_selection(
                valid_profile_groups
            ):
                log_info(
                    f"Component groups for build: {', '.join(valid_profile_groups)}"
                )

    # Handle --groups override (always wins over profile defaults)
    if args.groups:
        cli_groups = [n.strip() for n in args.groups.split(",") if n.strip()]
        valid_cli_groups = keep_list.validate_component_groups(cli_groups)
        if valid_cli_groups and keep_list.write_group_selection(valid_cli_groups):
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
        builds = uup_api.get_latest_builds_cached(
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
            build_info = uup_api.get_build_info_cached(
                args.build_id,
                ttl_seconds=args.cache_ttl,
                force_refresh=args.no_cache,
            )
            if not build_info:
                log_error("Failed to get build information")
                return 1
            edition_filter = uup_download.resolve_edition_filter(
                build_info, args.edition
            )

        # Handle multi-language download
        if args.languages_download:
            langs = [
                lang.strip()
                for lang in args.languages_download.split(",")
                if lang.strip()
            ]
            if langs:
                success = uup_download.download_language_packs(
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

        success = uup_download.download_build(
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
        builds = uup_api.get_latest_builds_cached(
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
