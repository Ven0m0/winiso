import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import keep_list


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
            self.assertTrue(keep_list.is_protected_pattern(pattern), pattern)

    def test_unrelated_pattern_allowed(self):
        self.assertFalse(keep_list.is_protected_pattern("*Xbox*"))


class TestLoadGroupPatterns(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        tmp_root = Path(self._tmpdir.name)

        self._orig_groups_file = keep_list.GROUPS_SELECTION_FILE
        self._orig_component_groups_file = keep_list.COMPONENT_GROUPS_FILE
        keep_list.GROUPS_SELECTION_FILE = tmp_root / ".uup-groups"
        keep_list.COMPONENT_GROUPS_FILE = tmp_root / "component_groups.json"
        self.addCleanup(self._restore)

        keep_list.COMPONENT_GROUPS_FILE.write_text(
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
        keep_list.GROUPS_SELECTION_FILE = self._orig_groups_file
        keep_list.COMPONENT_GROUPS_FILE = self._orig_component_groups_file

    def test_no_selection_file_returns_empty(self):
        self.assertEqual(keep_list.load_group_patterns(), [])

    def test_expands_selected_groups_and_dedupes(self):
        keep_list.GROUPS_SELECTION_FILE.write_text(
            "gaming\ngaming\ntelemetry\n", encoding="utf-8"
        )
        patterns = keep_list.load_group_patterns()
        self.assertEqual(patterns, ["*Xbox*", "*Solitaire*", "*Copilot*"])

    def test_protected_pattern_in_group_is_skipped(self):
        keep_list.GROUPS_SELECTION_FILE.write_text("telemetry\n", encoding="utf-8")
        patterns = keep_list.load_group_patterns()
        self.assertNotIn("*Store*", patterns)
        self.assertIn("*Copilot*", patterns)

    def test_unknown_group_is_ignored(self):
        keep_list.GROUPS_SELECTION_FILE.write_text(
            "not-a-real-group\n", encoding="utf-8"
        )
        self.assertEqual(keep_list.load_group_patterns(), [])


class TestGroupRoundTrip(unittest.TestCase):
    def test_written_selection_is_read_back_and_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            groups_file = root / "component_groups.json"
            groups_file.write_text(
                json.dumps({"groups": {"gaming": {"patterns": ["*Xbox*"]}}}),
                encoding="utf-8",
            )
            selection = root / ".uup-groups"
            self.assertTrue(keep_list.write_group_selection(["gaming"], selection))
            self.assertEqual(keep_list.read_group_selection(selection), ["gaming"])
            self.assertEqual(
                keep_list.collect_component_patterns(
                    keep_list.read_group_selection(selection), groups_file
                ),
                ["*Xbox*"],
            )

    def test_write_failure_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(
                keep_list.write_group_selection(["a"], Path(tmp) / "no" / "dir")
            )


class TestStdlibOnly(unittest.TestCase):
    def test_windows_script_imports_without_httpx_or_orjson(self):
        scripts = Path(__file__).resolve().parent.parent / "scripts"
        code = (
            "import sys; sys.modules['orjson'] = None; sys.modules['httpx'] = None; "
            f"sys.path.insert(0, {str(scripts)!r}); import apply_image_settings"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class TestKeepListMatchesAgentsDoc(unittest.TestCase):
    def test_every_documented_keyword_is_protected(self):
        agents = (Path(__file__).resolve().parent.parent / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        for keyword in ("Store", "WebView", "VCLibs", "UI.Xaml", "Defender"):
            self.assertIn(f"*{keyword}*", agents)
            self.assertTrue(keep_list.is_protected_pattern(f"*{keyword}*"), keyword)
        self.assertTrue(keep_list.is_protected_pattern("*DesktopAppInstaller*"))


if __name__ == "__main__":
    unittest.main()
