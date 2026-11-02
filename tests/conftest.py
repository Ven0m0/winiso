import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import uup_api


@pytest.fixture(autouse=True)
def _isolated_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test away from the developer's real .uup_cache (cache_clear wipes it)."""
    monkeypatch.setattr(uup_api, "CACHE_DIR", tmp_path / ".uup_cache")
