# ISO Creation

Two independent paths produce a bootable Windows 11 ISO in this repo. Path A is the default and
requires only Linux. Path B is an optional, Windows-only manual stage that assembles a final ISO
from an already-staged directory tree. See `AGENTS.md` (canonical repo guide) for the full
pipeline reference and hard invariants.

| Path | Platform | Entry point | Required |
|------|----------|--------------|----------|
| A — Linux pipeline | Linux | `make build` / `scripts/build.py` | Default, always available |
| B — Windows manual ISO assembly | Windows | `scripts/new_iso.py` | Optional, only for the Windows servicing stage |

## Path A: Linux pipeline (`make build` / `scripts/build.py`)

Default build flow. Runs entirely as the current user — no `sudo` — via `wimlib-imagex` over FUSE.

```
make deps       # Install: aria2c, cabextract, wimlib-imagex, chntpw, genisoimage/mkisofs
make download   # Fetch UUP packages into uup_files/ (runtime dir, not committed)
make validate   # Check tools, disk space, UUP files, config
make build      # Full pipeline: UUP -> WIM -> debloat -> ISO
```

`mise run install-deps` is the mise equivalent of `make deps`.

Stage breakdown:

- **`make download`** fetches UUP `.cab`/`.esd` packages into `uup_files/` via
  `scripts/download_uup.py`, which talks to `uupdump.net` only.
- **`make validate`** checks tools, disk space, UUP files, and config before a full build.
- **`make build`** runs UUP-to-WIM conversion (`scripts/custom_convert.sh`, upstream-derived,
  patch-only), AppX debloating and offline registry hardening
  (`scripts/debloat_wim.py`, enforces the AppX keep-list from `config/debloat_list.txt`), then
  final ISO assembly. Output lands in `output/` — a runtime directory, not committed.

### Build variants

| Target | Effect |
|--------|--------|
| `make build` | Default: `TARGET_EDITION=ProfessionalWorkstation`, fallback `Professional` |
| `make build-pro` | Forces `Professional` edition only |
| `make build-nano` | `NANO=1` — aggressive debloating |
| `make build-pause` | `PAUSE_FOR_WINDOWS_STAGE=1` — pauses after WIM export so the optional Windows servicing stage (Path B, below) can run before the ISO is finalized |

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TARGET_EDITION` | `ProfessionalWorkstation` | Preferred WIM edition name |
| `FALLBACK_EDITION` | `Professional` | Used if target edition not found |
| `PAUSE_FOR_WINDOWS_STAGE` | `0` | Pause after WIM export for Windows DISM servicing |
| `NANO` | `0` | Enable aggressive debloating mode |

### Signing and cleanup

```
make sign ISO=output/Win11.iso [GPG=1 KEY=<key-id>]  # SHA256/SHA512 (+ optional GPG), via scripts/sign_iso.py
make clean                                            # Remove build artifacts
```

### Verifying the result

After a build, `scripts/Test-IsoBoot.ps1` (Windows, Hyper-V required) can verify the ISO actually
boots and completes install — see `docs/hyperv-testing.md`.

## Path B: Windows-side manual ISO assembly (`scripts/new_iso.py`)

Standalone Python script, stdlib-only, runs under a bare Windows `python.exe` with no venv (no
`httpx`/`orjson` — those are the Linux-pipeline-only dependencies). Wraps `oscdimg.exe` to build a
bootable UEFI+BIOS ISO from an already-staged directory tree. Converted from an upstream
`ISO.cmd`/`New-Iso.ps1`.

### Usage

```
python scripts/new_iso.py [--iso-root PATH] [--output-iso PATH]
```

| Flag | Default | Notes |
|------|---------|-------|
| `--iso-root` | `C:\ISO` | Root of the staged install media. Must already contain `boot\etfsboot.com` (BIOS boot sector) and `efi\Microsoft\boot\efisys.bin` (UEFI boot sector), or the script errors out before calling oscdimg. |
| `--output-iso` | `C:\Win.iso` | |

`oscdimg.exe` is located via `win_utils.find_oscdimg()`, adjustable through `scripts/win_config.py`.
The script builds the dual-boot data string `2#p0,e,bETFSBOOT#pEF,e,bEFISYS` and invokes:

```
oscdimg -m -o -u2 -udfver102 -bootdata:<data> <iso-root> <output-iso>
```

A non-zero `oscdimg` exit code is treated as fatal.

### Where this fits

`new_iso.py` is the last step of the optional Windows servicing stage. Typical flow:

1. Pause the Linux build: `make build-pause`.
2. Copy `install.wim` to a Windows machine.
3. Run `scripts/windows_service.cmd` (DISM cleanup, 8.3 stripping) or
   `scripts/apply_image_settings.py` (ISO extraction, unattend injection, debloat re-run, driver
   injection — see `AGENTS.md`'s file table for details) to stage a fresh `iso-root`-style
   directory.
4. Run `scripts/new_iso.py` against that staged directory to produce the final ISO.

### Scope boundary

Per `.claude/rules/windows-servicing.md`, `new_iso.py` and its sibling servicing scripts are
optional and Windows-only — never required for the default Linux build flow. `*.cmd` files in the
servicing stage keep CRLF line endings; `new_iso.py` itself is a normal Python text file.

## See also

- `docs/hyperv-testing.md` — verifying a built ISO boots, and the online-servicing manual workflow
- `AGENTS.md` — canonical repo guide: full build flow, hard invariants, pipeline script rules
