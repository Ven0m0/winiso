import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download_uup
from download_uup import parse_args


class TestDownloadBuildBuildInfoFastPath(unittest.TestCase):
    """Tests that download_build reuses a supplied build_info and skips the API call."""

    @patch("download_uup.get_build_info")
    def test_build_info_provided_skips_api_call(self, mock_get_build_info):
        """When build_info is passed in, get_build_info must not be called."""
        # Passing an empty files dict causes an early return ("No files found"),
        # so no filesystem or network activity is needed.
        build_info = {"files": {}}
        result = download_uup.download_build(
            "fake-id", "/tmp/out", build_info=build_info
        )

        mock_get_build_info.assert_not_called()
        self.assertFalse(result)

    @patch("download_uup.get_build_info", return_value=None)
    def test_no_build_info_calls_api(self, mock_get_build_info):
        """When build_info is not passed, get_build_info is called."""
        result = download_uup.download_build("fake-id", "/tmp/out")
        mock_get_build_info.assert_called_once_with("fake-id")
        self.assertFalse(result)


class TestCheckDependencies(unittest.TestCase):
    @patch("shutil.which")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_check_dependencies_all_present(
        self, mock_log_info, mock_log_error, mock_which
    ):
        # Mock shutil.which to return a path for aria2c
        mock_which.return_value = "/usr/bin/aria2c"


class TestDownloadUUP(unittest.TestCase):
    def test_parse_args_defaults(self):
        args = parse_args([])
        self.assertEqual(args.output, "uup_files")
        self.assertIsNone(args.build_id)
        self.assertFalse(args.list)
        self.assertEqual(args.max_results, 10)


class TestGetLatestBuilds(unittest.TestCase):
    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_latest_builds_api_error(self, mock_log_error, mock_fetch_url):
        # Simulate API returning a JSON string with an error field
        mock_fetch_url.return_value = '{"response": {"error": "Invalid request"}}'

        result = download_uup.get_latest_builds()

        self.assertIsNone(result)
        mock_log_error.assert_called_with("API Error: Invalid request")

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_latest_builds_no_response(self, mock_log_error, mock_fetch_url):
        # Simulate no response from the URL fetch
        mock_fetch_url.return_value = None

        result = download_uup.get_latest_builds()

        self.assertIsNone(result)
        mock_log_error.assert_called_with("Failed to fetch builds from uupdump.net")

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_latest_builds_json_decode_error(self, mock_log_error, mock_fetch_url):
        # Simulate an invalid JSON string
        mock_fetch_url.return_value = "Not a JSON string"

        result = download_uup.get_latest_builds()

        self.assertIsNone(result)
        # Since the error message includes the exception string, we just check that it starts correctly
        mock_log_error.assert_called_once()
        self.assertTrue(
            mock_log_error.call_args[0][0].startswith("Failed to parse JSON response:")
        )


class TestGetBuildInfo(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_build_info_success(self, mock_fetch_url):
        import json

        mock_fetch_url.return_value = json.dumps(
            {"response": {"build": "info", "files": {}}}
        )

        result = download_uup.get_build_info("fake-id")

        self.assertEqual(result, {"build": "info", "files": {}})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id"
        )


class TestFetchUrl(unittest.TestCase):
    @patch("download_uup.urlopen")
    def test_fetch_url_success_get(self, mock_urlopen):
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = b"success content"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = download_uup.fetch_url("http://example.com")

        self.assertEqual(result, "success content")
        mock_urlopen.assert_called_once()

    @patch("download_uup.urlopen")
    @patch("download_uup.Request")
    def test_fetch_url_success_post(self, mock_request, mock_urlopen):
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = b"post success"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        data = {"key": "value"}
        result = download_uup.fetch_url("http://example.com", data=data)

        self.assertEqual(result, "post success")
        mock_request.assert_called_once()
        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["data"], b"key=value")

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_http_error(self, mock_log_error, mock_urlopen):
        from urllib.error import HTTPError
        from io import BytesIO

        mock_urlopen.side_effect = HTTPError(
            "http://example.com", 404, "Not Found", {}, BytesIO(b"")
        )

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("HTTP Error 404", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_url_error(self, mock_log_error, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("reason")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("URL Error", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_generic_exception(self, mock_log_error, mock_urlopen):
        mock_urlopen.side_effect = Exception("generic error")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Error fetching URL", mock_log_error.call_args[0][0])


class TestSelectEditions(unittest.TestCase):
    @patch("download_uup.log_warn")
    def test_select_editions_no_esd_files(self, mock_log_warn):
        build_info = {"files": {"test.txt": {"size": 100}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with(
            "No edition-specific files found, will download all files"
        )

    @patch("download_uup.log_warn")
    def test_select_editions_no_matching_esd_files(self, mock_log_warn):
        build_info = {"files": {"unknown.esd": {"size": 100}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with(
            "No edition-specific files found, will download all files"
        )

    @patch("builtins.input", return_value="")
    def test_select_editions_empty_choice(self, mock_input):
        build_info = {
            "files": {
                "Windows_Professional.esd": {"size": 100},
                "Windows_Home.esd": {"size": 100},
            }
        }
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)

    @patch("builtins.input", return_value="A")
    def test_select_editions_all_choice(self, mock_input):
        build_info = {"files": {"Windows_Professional.esd": {"size": 100}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)

    @patch("builtins.input", return_value="1")
    def test_select_editions_valid_choice(self, mock_input):
        # We need to be careful with the order of editions because it uses list(edition_files.keys())
        # Python 3.7+ dicts are ordered, so "professional" then "home"
        build_info = {
            "files": {
                "Windows_Professional.esd": {"size": 100},
                "Windows_Home.esd": {"size": 100},
            }
        }
        result = download_uup.select_editions(build_info)
        # It should return a list with the filename
        # editions = ["professional", "home"]
        # choice "1" -> idx 0 -> edition_files["professional"] -> "Windows_Professional.esd"
        self.assertEqual(result, ["Windows_Professional.esd"])

    @patch("download_uup.log_warn")
    @patch("builtins.input", return_value="invalid")
    def test_select_editions_non_numeric_choice(self, mock_input, mock_log_warn):
        build_info = {"files": {"Windows_Professional.esd": {"size": 100}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with("Invalid selection, downloading all editions")

    @patch("download_uup.log_warn")
    @patch("builtins.input", return_value="99")
    def test_select_editions_out_of_range_choice(self, mock_input, mock_log_warn):
        build_info = {"files": {"Windows_Professional.esd": {"size": 100}}}
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)
        mock_log_warn.assert_called_with("Invalid selection, downloading all editions")


if __name__ == "__main__":
    unittest.main()
