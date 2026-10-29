# Python quality verification

Date: 2026-10-29. Scope: all 25 Python files in `scripts/`, `tests/`, and `.claude/hooks/`.
The working tree was clean before this work. No commit was created.

## Changes

- `scripts/pyutils.py` and `scripts/win_utils.py`: guard the optional stream
  `reconfigure()` method. Both previously crashed during import when a redirected
  non-UTF-8 stream lacked that method. Regression tests reproduced both failures
  before the fix and now pass. Supported streams still get UTF-8 and replacement errors.
- `scripts/download_uup.py`: remove unused `ALL_COMPONENT_GROUPS`; both scanners
  identified it, and a repository-wide reference search confirmed no callers.
- `tests/test_download_uup.py`: narrow optional results with assertions, explicitly
  import `unittest.mock`, identify intentionally unused injected mocks with underscores,
  and remove unused pin-test setup, attributes, and a discarded path expression.
  Removed setup never installed its proposed patch. Searches verified the deletions;
  tests also pass, but cannot by themselves prove absence of external consumers.
- `tests/test_validators.py`: regression tests for redirected and reconfigurable streams.
- `scripts/keep_list.py` and `scripts/uup_delta.py`: remove shebangs from import-only,
  non-executable modules. Neither had a main entry point.
- `.kilo/kilo.json`: formatting only, needed by the full hook gate. Parsed JSON values
  were verified unchanged. `CHANGELOG.md` records the contributor-facing changes.

## Verification

Commands below were prefixed with `rtk proxy`.

| Check | Command / method | Result |
| --- | --- | --- |
| Tests | `uv run --group dev pytest tests/ -q` | 273 tests and 4 subtests passed |
| Ruff lint | `uv run --group dev ruff check scripts tests .claude/hooks` | Passed |
| Ruff format | `uv run --group dev ruff format --check scripts tests .claude/hooks` | All 25 files formatted |
| ty configured gate | `uv run --group dev ty check scripts/download_uup.py` | Passed |
| ty full scope | `uv run --group dev ty check --extra-search-path scripts scripts tests .claude/hooks` | Passed |
| basedpyright configured gate | `uv tool run basedpyright scripts/download_uup.py` | Zero errors or warnings |
| basedpyright full scope | `uv tool run basedpyright --project <temporary-config>` | Zero errors or warnings |
| Compilation | `uv run --group dev python -c` calling `py_compile.compile(..., doraise=True)` for every scoped file | All 25 compiled |
| Vulture | `uv run --group dev vulture scripts tests .claude/hooks --min-confidence 60 --ignore-names log_debug` | Passed with the documented public logging helper excluded |
| deadcode | See compatibility limitation below | No remaining findings after explicit exclusions in diagnostic run |
| Full gate | `prek run --all-files` | Exit 0; every applicable hook passed |
| Diff and endings | `git diff --check`; count CRLF/LF in changed files | Passed; changed files retain LF |

The temporary basedpyright configuration extended the repository's configuration,
included all three Python directories, added `scripts/` to `extraPaths`, and selected
the repository `.venv`. It was removed afterward; permanent checker settings were unchanged.

The full gate passed Ruff, Ruff format, basedpyright, pyupgrade, whitespace/EOF,
YAML/JSON/TOML, BOM/line-ending, private-key, case-conflict and shebang checks,
XML validation, Renovate, Biome, Dependabot/workflow schemas, and both PowerShell
hooks. Submodule and GitHub Actions checks skipped because no matching files existed.

## Limits and explicit exclusions

`deadcode` crashes unmodified under Python 3.14 because it uses removed `ast.Str`
and `Constant.s` APIs. Running it under 3.13 skipped four files using newer syntax.
For diagnosis only, the following process-local shim allowed the complete scan:

```powershell
rtk proxy uv run --group dev python -c "import ast; ast.Str = ast.Constant; ast.Constant.s = property(lambda self: self.value); from deadcode.cli import print_main; print_main()" scripts tests .claude/hooks --no-color --ignore-names log_debug setUp tearDown
```

This diagnostic command passed, but is not an unmodified deadcode pass. No shim,
dependency change, or scanner configuration was added to the repository.
`setUp` and `tearDown` are unittest callbacks. `log_debug` is a documented shared
logging API in `AGENTS.md`; it remains available despite having no current callers.

No ISO build, Linux/FUSE run, Windows servicing operation, or boot test was performed.
No performance benchmarks were run. These checks establish validity within their
scope; they do not prove global optimality or correctness on every target system.
