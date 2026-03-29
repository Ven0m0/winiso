import unittest
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

        # Assertions
        self.assertIsNone(result)
        mock_log_error.assert_called_once_with(
            "URL Error: Name or service not known"
        )

    @patch("scripts.download_uup.urlopen")
    @patch("scripts.download_uup.log_error")
    def test_fetch_url_generic_exception(self, mock_log_error, mock_urlopen):
        # Create a mock generic Exception
        mock_error = Exception("Something went wrong")
        mock_urlopen.side_effect = mock_error

        # Call the function
        result = fetch_url("http://example.com")

        # Assertions
        self.assertIsNone(result)
        mock_log_error.assert_called_once_with(
            "Error fetching URL: Something went wrong"
        )

    @patch("scripts.download_uup.urlopen")
    def test_fetch_url_success(self, mock_urlopen):
        # Mock successful response
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = b"success content"

        # Call the function
        result = fetch_url("http://example.com")

        # Assertions
        self.assertEqual(result, "success content")


if __name__ == "__main__":
    unittest.main()
