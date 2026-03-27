import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add scripts directory to sys.path so we can import download_uup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

import download_uup
from urllib.error import HTTPError

class TestDownloadUUP(unittest.TestCase):
    @patch('download_uup.urlopen')
    @patch('download_uup.log_error')
    def test_fetch_url_http_error(self, mock_log_error, mock_urlopen):
        # Create an HTTPError instance
        # url, code, msg, hdrs, fp
        error = HTTPError("http://example.com", 404, "Not Found", None, None)
        mock_urlopen.side_effect = error

        result = download_uup.fetch_url("http://example.com")

        # Verify the result is None as per the exception handling block
        self.assertIsNone(result)

        # Verify log_error was called with the correct message
        mock_log_error.assert_called_once_with("HTTP Error 404: Not Found")

if __name__ == '__main__':
    unittest.main()
