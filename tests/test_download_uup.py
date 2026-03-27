import unittest
import json
from unittest.mock import patch
import sys
import os

# Add scripts directory to path so we can import download_uup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import download_uup

class TestCheckDependencies(unittest.TestCase):
    @patch('shutil.which')
    @patch('download_uup.log_error')
    @patch('download_uup.log_info')
    def test_check_dependencies_all_present(self, mock_log_info, mock_log_error, mock_which):
        # Mock shutil.which to return a path for aria2c
        mock_which.return_value = '/usr/bin/aria2c'

        result = download_uup.check_dependencies()

        self.assertTrue(result)
        mock_log_error.assert_not_called()
        mock_which.assert_called_once_with('aria2c')

    @patch('shutil.which')
    @patch('download_uup.log_error')
    @patch('download_uup.log_info')
    def test_check_dependencies_missing(self, mock_log_info, mock_log_error, mock_which):
        # Mock shutil.which to return None for aria2c
        mock_which.return_value = None

        result = download_uup.check_dependencies()

        self.assertFalse(result)
        mock_log_error.assert_called()
        mock_log_info.assert_called_with("Run 'make deps' to install dependencies")
        mock_which.assert_called_once_with('aria2c')

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
