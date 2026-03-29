import unittest
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import sys
import os

# Add project root to path to import scripts.download_uup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.download_uup import fetch_url  # noqa: E402


class TestDownloadUUP(unittest.TestCase):
    @patch("scripts.download_uup.urlopen")
    @patch("scripts.download_uup.log_error")
    def test_fetch_url_httperror(self, mock_log_error, mock_urlopen):
        # Create a mock HTTPError
        mock_error = HTTPError(
            url="http://example.com",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None
        )
        mock_urlopen.side_effect = mock_error

        # Call the function
        result = fetch_url("http://example.com")

        # Assertions
        self.assertIsNone(result)
        mock_log_error.assert_called_once_with("HTTP Error 404: Not Found")

    @patch("scripts.download_uup.urlopen")
    @patch("scripts.download_uup.log_error")
    def test_fetch_url_urlerror(self, mock_log_error, mock_urlopen):
        # Create a mock URLError
        mock_error = URLError(reason="Name or service not known")
        mock_urlopen.side_effect = mock_error

        # Call the function
        result = fetch_url("http://example.com")

class TestGetLatestBuilds(unittest.TestCase):
    @patch('download_uup.fetch_url')
    @patch('download_uup.log_error')
    def test_get_latest_builds_invalid_json(self, mock_log_error, mock_fetch_url):
        # Mock fetch_url to return invalid JSON
        mock_fetch_url.return_value = "{ invalid }"

        result = download_uup.get_latest_builds()

        self.assertEqual(result, [])
        mock_log_error.assert_called()
        # Verify the error message starts with the expected prefix
        args, _ = mock_log_error.call_args
        self.assertTrue(args[0].startswith("Failed to parse JSON response"))

    @patch('download_uup.fetch_url')
    @patch('download_uup.log_warn')
    def test_get_latest_builds_no_builds(self, mock_log_warn, mock_fetch_url):
        # Mock fetch_url to return JSON with no builds
        mock_fetch_url.return_value = '{"response": {"builds": {}}}'

        result = download_uup.get_latest_builds()

        self.assertEqual(result, [])
        mock_log_warn.assert_called_with("No builds found in API response")

    @patch('download_uup.fetch_url')
    def test_get_latest_builds_success(self, mock_fetch_url):
        # Mock fetch_url to return valid builds
        mock_fetch_url.return_value = json.dumps({
            "response": {
                "builds": {
                    "uuid1": {"title": "Build 1", "build": "22621.1", "created": 100},
                    "uuid2": {"title": "Build 2", "build": "22621.2", "created": 200}
                }
            }
        })

        result = download_uup.get_latest_builds(max_results=1)

        self.assertEqual(len(result), 1)
        # Should be the newest build (uuid2)
        self.assertEqual(result[0]["id"], "uuid2")
        self.assertEqual(result[0]["title"], "Build 2")

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

    @patch("builtins.print")
    @patch("download_uup.log_warn")
    def test_invalid_selection_inputs(self, mock_log_warn, _mock_print):
        """Tests that invalid selections are handled correctly."""
        for choice in ["99", "invalid"]:
            with self.subTest(choice=choice):
                with patch("builtins.input", return_value=choice):
                    result = download_uup.select_editions(self.sample_build_info)
                    self.assertIsNone(result)
                    mock_log_warn.assert_called_with("Invalid selection, downloading all editions")
                # Reset mock for next subtest to ensure assertion is specific to the subtest
                mock_log_warn.reset_mock()


if __name__ == "__main__":
    unittest.main()
