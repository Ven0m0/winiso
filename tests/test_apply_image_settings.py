import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import apply_image_settings
import keep_list
import win_utils


class TestGetAppxPatterns(unittest.TestCase):
    def test_matches_debloat_list_minus_protected(self):
        expected = tuple(
            p
            for p in keep_list.load_patterns()
            if not keep_list.is_protected_pattern(p)
        )
        self.assertEqual(apply_image_settings.get_appx_patterns(), expected)
        self.assertGreater(len(expected), 0)

    def test_no_pattern_is_protected(self):
        for pattern in apply_image_settings.get_appx_patterns():
            self.assertFalse(keep_list.is_protected_pattern(pattern), pattern)


GET_PACKAGES_OUTPUT = """Deployment Image Servicing and Management tool
Version: 10.0.26100.1

Image Version: 10.0.26100.1

Packages listing:

Package Identity : Microsoft-Windows-Hello-Face-Package~31bf3856ad364e35~amd64~~10.0.26100.1
State : Installed
Release Type : Feature Pack

Package Identity : Microsoft-Windows-Notepad-FoD-Package~31bf3856ad364e35~amd64~~10.0.26100.1
State : Staged
Release Type : Feature Pack

Package Identity : Microsoft-Windows-MSPaint-FoD-Package~31bf3856ad364e35~amd64~~10.0.26100.1
State : Installed
Release Type : Feature Pack

The operation completed successfully.
"""


class TestParseDismInstalled(unittest.TestCase):
    def test_keeps_only_installed_entries(self):
        names = win_utils.parse_dism_installed(GET_PACKAGES_OUTPUT, "Package Identity")
        self.assertEqual(
            [n.split("~")[0] for n in names],
            [
                "Microsoft-Windows-Hello-Face-Package",
                "Microsoft-Windows-MSPaint-FoD-Package",
            ],
        )

    def test_empty_output_yields_nothing(self):
        self.assertEqual(win_utils.parse_dism_installed("", "Package Identity"), [])

    def test_state_without_identity_is_ignored(self):
        self.assertEqual(
            win_utils.parse_dism_installed("State : Installed\n", "Package Identity"),
            [],
        )


class TestDismSeam(unittest.TestCase):
    def test_remove_packages_removes_only_matching_installed(self):
        calls: list[list[str]] = []

        def fake(args: list[str]) -> str:
            calls.append(args)
            return GET_PACKAGES_OUTPUT if "/Get-Packages" in args else ""

        with mock.patch.object(apply_image_settings, "dism_capture", fake):
            apply_image_settings.remove_packages(Path("mnt"))

        removals = [c for c in calls if "/Remove-Package" in c]
        self.assertEqual(len(removals), 2)
        self.assertTrue(all(c[0] == f"/Image:{Path('mnt')}" for c in removals))
        self.assertFalse(any("Notepad" in part for c in removals for part in c))

    def test_remove_appx_never_removes_protected_names(self):
        calls: list[list[str]] = []

        def fake(args: list[str]) -> str:
            calls.append(args)
            return ""

        with (
            mock.patch.object(apply_image_settings, "dism_capture", fake),
            mock.patch.object(
                apply_image_settings,
                "dism_get_names",
                return_value=["Microsoft.BingNews", "Microsoft.WindowsStore"],
            ),
            mock.patch.object(
                apply_image_settings, "get_appx_patterns", return_value=("*BingNews*",)
            ),
        ):
            apply_image_settings.remove_appx_packages(Path("mnt"))

        removed = [
            part for c in calls for part in c if part.startswith("/PackageName:")
        ]
        self.assertEqual(removed, ["/PackageName:Microsoft.BingNews"])


if __name__ == "__main__":
    unittest.main()
