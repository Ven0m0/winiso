import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import debloat_wim


class TestIsProtectedPattern(unittest.TestCase):
    def test_protected_keywords_blocked(self):
        for pattern in (
            "*Store*",
            "*WebView*",
            "*VCLibs*",
            "*UI.Xaml*",
            "*Defender*",
            "*DesktopAppInstaller*",
        ):
            self.assertTrue(debloat_wim.is_protected_pattern(pattern), pattern)

    def test_unrelated_pattern_allowed(self):
        self.assertFalse(debloat_wim.is_protected_pattern("*Xbox*"))


class TestLoadGroupPatterns(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        tmp_root = Path(self._tmpdir.name)

        self._orig_groups_file = debloat_wim.GROUPS_SELECTION_FILE
        self._orig_component_groups_file = debloat_wim.COMPONENT_GROUPS_FILE
        debloat_wim.GROUPS_SELECTION_FILE = tmp_root / ".uup-groups"
        debloat_wim.COMPONENT_GROUPS_FILE = tmp_root / "component_groups.json"
        self.addCleanup(self._restore)

        debloat_wim.COMPONENT_GROUPS_FILE.write_text(
            json.dumps(
                {
                    "groups": {
                        "gaming": {"patterns": ["*Xbox*", "*Solitaire*"]},
                        "telemetry": {"patterns": ["*Copilot*", "*Store*"]},
                    }
                }
            ),
            encoding="utf-8",
        )

    def _restore(self):
        debloat_wim.GROUPS_SELECTION_FILE = self._orig_groups_file
        debloat_wim.COMPONENT_GROUPS_FILE = self._orig_component_groups_file

    def test_no_selection_file_returns_empty(self):
        self.assertEqual(debloat_wim.load_group_patterns(), [])

    def test_expands_selected_groups_and_dedupes(self):
        debloat_wim.GROUPS_SELECTION_FILE.write_text(
            "gaming\ngaming\ntelemetry\n", encoding="utf-8"
        )
        patterns = debloat_wim.load_group_patterns()
        self.assertEqual(patterns, ["*Xbox*", "*Solitaire*", "*Copilot*"])

    def test_protected_pattern_in_group_is_skipped(self):
        debloat_wim.GROUPS_SELECTION_FILE.write_text("telemetry\n", encoding="utf-8")
        patterns = debloat_wim.load_group_patterns()
        self.assertNotIn("*Store*", patterns)
        self.assertIn("*Copilot*", patterns)

    def test_unknown_group_is_ignored(self):
        debloat_wim.GROUPS_SELECTION_FILE.write_text(
            "not-a-real-group\n", encoding="utf-8"
        )
        self.assertEqual(debloat_wim.load_group_patterns(), [])


if __name__ == "__main__":
    unittest.main()
