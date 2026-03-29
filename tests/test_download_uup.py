import unittest
from unittest.mock import patch
import sys
import os

# Add scripts directory to path so we can import download_uup
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)
import download_uup


class TestCheckDependencies(unittest.TestCase):
    @patch("shutil.which")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_check_dependencies_all_present(
        self, mock_log_info, mock_log_error, mock_which
    ):
        # Mock shutil.which to return a path for aria2c
        mock_which.return_value = "/usr/bin/aria2c"

        result = download_uup.check_dependencies()

        self.assertTrue(result)
        mock_log_error.assert_not_called()
        mock_which.assert_called_once_with("aria2c")

    @patch("shutil.which")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_check_dependencies_missing(
        self, mock_log_info, mock_log_error, mock_which
    ):
        # Mock shutil.which to return None for aria2c
        mock_which.return_value = None

        result = download_uup.check_dependencies()

        self.assertFalse(result)
        mock_log_error.assert_called()
        mock_log_info.assert_called_with("Run 'make deps' to install dependencies")
        mock_which.assert_called_once_with("aria2c")


class TestSelectEditions(unittest.TestCase):
    def setUp(self):
        self.sample_build_info = {
            "files": {
                "Professional_en-us.esd": {"size": 100},
                "Enterprise_en-us.esd": {"size": 100},
                "Home_en-us.esd": {"size": 100},
                "other_file.txt": {"size": 10},
            }
        }

    @patch("download_uup.log_warn")
    def test_no_edition_files(self, mock_log_warn):
        build_info = {"files": {"random.txt": {}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with("No edition-specific files found, will download all files")

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_select_all_default(self, mock_print, mock_input):
        result = download_uup.select_editions(self.sample_build_info)
        self.assertIsNone(result)

    @patch("builtins.input", return_value="A")
    @patch("builtins.print")
    def test_select_all_explicit(self, mock_print, mock_input):
        result = download_uup.select_editions(self.sample_build_info)
        self.assertIsNone(result)

    @patch("builtins.print")
    def test_valid_selections(self, _mock_print):
        """Tests that valid numeric selections return the correct edition file."""
        test_cases = [
            ("1", "Professional_en-us.esd"),
            ("2", "Enterprise_en-us.esd"),
            ("3", "Home_en-us.esd"),
        ]

        for choice, expected_file in test_cases:
            with self.subTest(choice=choice):
                with patch("builtins.input", return_value=choice):
                    result = download_uup.select_editions(self.sample_build_info)
                    self.assertEqual(result, [expected_file])

    @patch("builtins.input", return_value="99")
    @patch("builtins.print")
    @patch("download_uup.log_warn")
    def test_invalid_number(self, mock_log_warn, mock_print, mock_input):
        result = download_uup.select_editions(self.sample_build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with("Invalid selection, downloading all editions")

    @patch("builtins.input", return_value="invalid")
    @patch("builtins.print")
    @patch("download_uup.log_warn")
    def test_invalid_input(self, mock_log_warn, mock_print, mock_input):
        result = download_uup.select_editions(self.sample_build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with("Invalid selection, downloading all editions")


if __name__ == "__main__":
    unittest.main()
