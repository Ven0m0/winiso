import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import subprocess

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
        # Mock shutil.which to return a path for aria2c, wimlib-imagex, cabextract
        mock_which.return_value = "/usr/bin/tool"

        result = download_uup.check_dependencies()

        self.assertTrue(result)
        mock_log_error.assert_not_called()
        mock_log_info.assert_not_called()
        self.assertEqual(mock_which.call_count, 3)

    @patch("shutil.which")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_check_dependencies_missing_tools(
        self, mock_log_info, mock_log_error, mock_which
    ):
        mock_which.return_value = None

        result = download_uup.check_dependencies()

        self.assertFalse(result)
        mock_log_error.assert_called_once_with(
            "Missing required tools: aria2c, wimlib-imagex, cabextract"
        )
        mock_log_info.assert_called_once_with("Run 'make deps' to install dependencies")
        self.assertEqual(mock_which.call_count, 3)

    @patch("shutil.which")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_check_dependencies_some_missing(
        self, mock_log_info, mock_log_error, mock_which
    ):
        def side_effect(tool):
            if tool == "aria2c":
                return "/usr/bin/aria2c"
            return None

        mock_which.side_effect = side_effect

        result = download_uup.check_dependencies()

        self.assertFalse(result)
        mock_log_error.assert_called_once_with(
            "Missing required tools: wimlib-imagex, cabextract"
        )
        mock_log_info.assert_called_once_with("Run 'make deps' to install dependencies")
        self.assertEqual(mock_which.call_count, 3)


class TestDownloadUUP(unittest.TestCase):
    def test_parse_args_defaults(self):
        args = parse_args([])
        self.assertEqual(args.output, "uup_files")
        self.assertIsNone(args.build_id)
        self.assertFalse(args.list)
        self.assertEqual(args.max_results, 10)


class TestDownloadBuild(unittest.TestCase):
    @patch("download_uup.get_build_info")
    @patch("download_uup.log_error")
    def test_download_build_no_build_info(self, mock_log_error, mock_get_build_info):
        mock_get_build_info.return_value = None
        result = download_uup.download_build("build123", Path("out"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("Failed to get build information")

    @patch("download_uup.get_build_info")
    @patch("download_uup.log_error")
    def test_download_build_no_files(self, mock_log_error, mock_get_build_info):
        mock_get_build_info.return_value = {"files": {}}
        result = download_uup.download_build("build123", Path("out"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("No files found for this build")


class TestGetLatestBuilds(unittest.TestCase):
    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_latest_builds_api_error(self, mock_log_error, mock_fetch_url):
        # Simulate API returning a dict with an error field
        mock_fetch_url.return_value = {"response": {"error": "Invalid request"}}

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
        # fetch_url returns None when JSON parsing fails
        mock_fetch_url.return_value = None

        result = download_uup.get_latest_builds()

        self.assertIsNone(result)
        mock_log_error.assert_called_with("Failed to fetch builds from uupdump.net")

    @patch("download_uup.fetch_url")
    def test_get_latest_builds_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {
            "response": {
                "builds": {
                    "build-1": {
                        "title": "Windows 11 Build 1",
                        "created": "1600000000",
                    },
                    "build-2": {
                        "title": "Windows 11 Build 2",
                        "created": "1620000000",
                    },
                    "build-3": {
                        "title": "Windows 11 Build 3",
                        "created": "1610000000",
                    },
                }
            }
        }

        result = download_uup.get_latest_builds(max_results=2)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        # Expected sort order: build-2 (1620000000), build-3 (1610000000)
        self.assertEqual(result[0]["id"], "build-2")
        self.assertEqual(result[0]["title"], "Windows 11 Build 2")
        self.assertEqual(result[1]["id"], "build-3")
        self.assertEqual(result[1]["title"], "Windows 11 Build 3")


class TestFetchLatestFromWU(unittest.TestCase):
    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_fetch_latest_from_wu_api_error(self, mock_log_error, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"error": "Invalid ring"}}
        result = download_uup.fetch_latest_from_wu()
        self.assertIsNone(result)
        mock_log_error.assert_called_with("API Error: Invalid ring")

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_warn")
    def test_fetch_latest_from_wu_no_response(self, mock_log_warn, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.fetch_latest_from_wu()
        self.assertIsNone(result)
        mock_log_warn.assert_called_with(
            "Failed to fetch from Windows Update, falling back to cached builds"
        )

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_warn")
    def test_fetch_latest_from_wu_json_decode_error(
        self, mock_log_warn, mock_fetch_url
    ):
        mock_fetch_url.return_value = None
        result = download_uup.fetch_latest_from_wu()
        self.assertIsNone(result)
        mock_log_warn.assert_called_with(
            "Failed to fetch from Windows Update, falling back to cached builds"
        )

    @patch("download_uup.fetch_url")
    def test_fetch_latest_from_wu_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {
            "response": {
                "updateId": "12345",
                "updateTitle": "Windows 11 Build",
                "foundBuild": "22621.1",
                "arch": "amd64",
            }
        }
        result = download_uup.fetch_latest_from_wu(arch="amd64", ring="Retail")
        self.assertIsNotNone(result)
        self.assertEqual(result["updateId"], "12345")
        self.assertEqual(result["updateTitle"], "Windows 11 Build")
        self.assertEqual(result["foundBuild"], "22621.1")
        self.assertEqual(result["arch"], "amd64")


class TestGetBuildInfo(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_build_info_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"build": "info", "files": {}}}

        result = download_uup.get_build_info("fake-id")

        self.assertEqual(result, {"build": "info", "files": {}})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id", return_json=True
        )


class TestGetAvailableLanguages(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_available_languages_with_build_id_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"lang": "en-us", "langList": []}}

        result = download_uup.get_available_languages("fake-id")

        self.assertEqual(result, {"lang": "en-us", "langList": []})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/listlangs.php?id=fake-id&lang=en-us",
            return_json=True,
        )

    @patch("download_uup.fetch_url")
    def test_get_available_languages_no_build_id_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"lang": "en-us", "langList": []}}

        result = download_uup.get_available_languages()

        self.assertEqual(result, {"lang": "en-us", "langList": []})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/listlangs.php", return_json=True
        )

    @patch("download_uup.fetch_url")
    def test_get_available_languages_fetch_fails(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_available_languages("fake-id")
        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    def test_get_available_languages_api_error(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"error": "Invalid build id"}}
        result = download_uup.get_available_languages("fake-id")
        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    def test_get_available_languages_json_error(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_available_languages("fake-id")
        self.assertIsNone(result)


class TestFetchUrl(unittest.TestCase):
    def setUp(self):
        download_uup._url_cache.clear()

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

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_timeout_error(self, mock_log_error, mock_urlopen):
        import socket

        mock_urlopen.side_effect = socket.timeout("timed out")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Error fetching URL", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_timeout_error_timeout(self, mock_log_error, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Error fetching URL", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_connection_reset_error(self, mock_log_error, mock_urlopen):
        mock_urlopen.side_effect = ConnectionResetError("Connection reset by peer")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Error fetching URL", mock_log_error.call_args[0][0])


class TestRunAria2Download(unittest.TestCase):
    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_called_process_error(
        self, mock_log_error, mock_run, mock_open
    ):
        mock_run.side_effect = subprocess.CalledProcessError(1, "aria2c")
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(Path("out"), Path("in.txt"), dl_list)

        self.assertFalse(result)
        mock_log_error.assert_called_with("Download failed with exit code 1")

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_warn")
    @patch("download_uup.Path.unlink")
    def test_run_aria2_download_keyboard_interrupt(
        self, mock_unlink, mock_log_warn, mock_run, mock_open
    ):
        mock_run.side_effect = KeyboardInterrupt()
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(Path("out"), Path("in.txt"), dl_list)

        self.assertFalse(result)
        mock_log_warn.assert_called_with("\nDownload cancelled by user")
        # Should call unlink on aria2_input

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_generic_exception(
        self, mock_log_error, mock_run, mock_open
    ):
        mock_run.side_effect = Exception("Unexpected error")
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(Path("out"), Path("in.txt"), dl_list)

        self.assertFalse(result)
        mock_log_error.assert_called_with(
            "An unexpected error occurred: Unexpected error"
        )


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


class TestInteractiveMode(unittest.TestCase):
    @patch("download_uup.log_error")
    @patch("download_uup.get_latest_builds", return_value=None)
    def test_interactive_mode_no_builds(self, mock_get_builds, mock_log_error):
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("Failed to fetch builds")

    @patch("download_uup.log_info")
    @patch("builtins.input", return_value="q")
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds")
    def test_interactive_mode_quit(
        self, mock_get_builds, mock_display_builds, mock_input, mock_log_info
    ):
        mock_get_builds.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_info.assert_called_once_with("Cancelled by user")

    @patch("download_uup.log_warn")
    @patch("builtins.input", side_effect=["invalid", "q"])
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds")
    def test_interactive_mode_value_error(
        self, mock_get_builds, mock_display_builds, mock_input, mock_log_warn
    ):
        mock_get_builds.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_warn.assert_any_call("Invalid input. Please enter a number.")

    @patch("download_uup.log_info")
    @patch("builtins.input", side_effect=KeyboardInterrupt)
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds")
    def test_interactive_mode_keyboard_interrupt(
        self, mock_get_builds, mock_display_builds, mock_input, mock_log_info
    ):
        mock_get_builds.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_info.assert_any_call("Cancelled by user")


class TestGetAvailableEditions(unittest.TestCase):
    @patch("download_uup.fetch_url")
    @patch("download_uup.log_info")
    def test_get_available_editions_success(self, mock_log_info, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"editionList": ["Core", "Professional"]}}

        result = download_uup.get_available_editions("fake-build-id")

        self.assertEqual(result, {"editionList": ["Core", "Professional"]})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/listeditions.php?id=fake-build-id&lang=en-us",
            return_json=True,
        )
        mock_log_info.assert_called_once_with(
            "Fetching available editions for build: fake-build-id"
        )

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_info")
    def test_get_available_editions_no_response(self, mock_log_info, mock_fetch_url):
        mock_fetch_url.return_value = None

        result = download_uup.get_available_editions("fake-build-id")

        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    @patch("download_uup.log_info")
    def test_get_available_editions_api_error(
        self, mock_log_info, mock_log_error, mock_fetch_url
    ):
        mock_fetch_url.return_value = {"response": {"error": "Invalid build ID"}}

        result = download_uup.get_available_editions("fake-build-id")

        self.assertIsNone(result)
        mock_log_error.assert_called_once_with("API Error: Invalid build ID")

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_info")
    def test_get_available_editions_json_decode_error(
        self, mock_log_info, mock_fetch_url
    ):
        mock_fetch_url.return_value = None

        result = download_uup.get_available_editions("fake-build-id")

        self.assertIsNone(result)


class TestGetApiVersion(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_api_version_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"version": "1.0.0"}}
        result = download_uup.get_api_version()
        self.assertEqual(result, {"version": "1.0.0"})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/", return_json=True
        )

    @patch("download_uup.fetch_url")
    def test_get_api_version_fetch_fails(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_api_version()
        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    def test_get_api_version_invalid_json(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_api_version()
        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    def test_get_api_version_no_response_key(self, mock_fetch_url):
        mock_fetch_url.return_value = {"other_key": "value"}
        result = download_uup.get_api_version()
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
