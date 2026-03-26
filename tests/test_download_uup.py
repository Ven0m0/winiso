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


if __name__ == "__main__":
    unittest.main()
