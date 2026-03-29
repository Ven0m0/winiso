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

if __name__ == '__main__':
    unittest.main()
