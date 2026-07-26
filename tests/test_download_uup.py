import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download_uup
from download_uup import parse_args


class TestDownloadBuildBuildInfoFastPath(unittest.TestCase):
    """Tests that download_build reuses a supplied build_info and skips the API call."""

    @patch("download_uup.get_build_info_cached")
    def test_build_info_provided_skips_api_call(self, mock_get_build_info_cached):
        """When build_info is passed in, get_build_info_cached must not be called."""
        # Passing an empty files dict causes an early return ("No files found"),
        # so no filesystem or network activity is needed.
        build_info = {"files": {}}
        result = download_uup.download_build(
            "fake-id", "/tmp/out", build_info=build_info
        )

        mock_get_build_info_cached.assert_not_called()
        self.assertFalse(result)

    @patch("download_uup.get_build_info_cached", return_value=None)
    def test_no_build_info_calls_api(self, mock_get_build_info_cached):
        """When build_info is not passed, get_build_info_cached is called."""
        result = download_uup.download_build("fake-id", "/tmp/out")
        mock_get_build_info_cached.assert_called_once()
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
    @patch("download_uup.get_build_info_cached")
    @patch("download_uup.log_error")
    def test_download_build_no_build_info(
        self, mock_log_error, mock_get_build_info_cached
    ):
        mock_get_build_info_cached.return_value = None
        result = download_uup.download_build("build123", Path("out"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("Failed to get build information")

    @patch("download_uup.get_build_info_cached")
    @patch("download_uup.log_error")
    def test_download_build_no_files(self, mock_log_error, mock_get_build_info_cached):
        mock_get_build_info_cached.return_value = {"files": {}}
        result = download_uup.download_build("build123", Path("out"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("No files found for this build")

    @patch("download_uup.log_error")
    def test_download_build_invalid_output_path(self, mock_log_error):
        build_info = {"files": {"a.esd": {"size": 1}}}
        result = download_uup.download_build(
            "build123", "/tmp/outside", build_info=build_info
        )
        self.assertFalse(result)
        mock_log_error.assert_called_with(
            "Output directory must be within the current directory"
        )

    @patch("download_uup.log_error")
    def test_download_build_no_files_after_filter(self, mock_log_error):
        build_info = {"files": {"a.esd": {"size": 1}}}
        result = download_uup.download_build(
            "build123",
            "uup_files",
            edition_filter=["b.esd"],
            build_info=build_info,
        )
        self.assertFalse(result)
        mock_log_error.assert_called_with("No files to download after filtering")


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


class TestGetUpdateInfo(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_update_info_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {
            "response": {
                "updateId": "test-update-id",
                "title": "Windows 11 Update",
                "build": "22621.1",
            }
        }

        result = download_uup.get_update_info("test-update-id")

        self.assertIsNotNone(result)
        self.assertEqual(result["updateId"], "test-update-id")
        self.assertEqual(result["title"], "Windows 11 Update")
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/updateinfo.php?id=test-update-id", return_json=True
        )

    @patch("download_uup.fetch_url")
    def test_get_update_info_fetch_fails(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_update_info("test-update-id")
        self.assertIsNone(result)

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_update_info_api_error(self, mock_log_error, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"error": "Update not found"}}
        result = download_uup.get_update_info("invalid-id")
        self.assertIsNone(result)
        mock_log_error.assert_called_once_with("API Error: Update not found")


class TestGetBuildInfo(unittest.TestCase):
    @patch("download_uup.fetch_url")
    def test_get_build_info_success(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"build": "info", "files": {}}}

        result = download_uup.get_build_info("fake-id")

        self.assertEqual(result, {"build": "info", "files": {}})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id&lang=en-us", return_json=True
        )

    @patch("download_uup.fetch_url")
    def test_get_build_info_with_language(self, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"build": "info", "files": {}}}

        result = download_uup.get_build_info("fake-id", language="fr-fr")

        self.assertEqual(result, {"build": "info", "files": {}})
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id&lang=fr-fr", return_json=True
        )

    @patch("download_uup.fetch_url")
    def test_get_build_info_fetch_fails(self, mock_fetch_url):
        mock_fetch_url.return_value = None
        result = download_uup.get_build_info("fake-id")
        self.assertIsNone(result)
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id&lang=en-us", return_json=True
        )

    @patch("download_uup.fetch_url")
    @patch("download_uup.log_error")
    def test_get_build_info_api_error(self, mock_log_error, mock_fetch_url):
        mock_fetch_url.return_value = {"response": {"error": "Invalid build ID"}}
        result = download_uup.get_build_info("fake-id")
        self.assertIsNone(result)
        mock_log_error.assert_called_once_with("API Error: Invalid build ID")
        mock_fetch_url.assert_called_once_with(
            "https://api.uupdump.net/get.php?id=fake-id&lang=en-us", return_json=True
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
        from io import BytesIO
        from urllib.error import HTTPError

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
        self.assertIn("Unexpected error fetching URL", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_timeout_error(self, mock_log_error, mock_urlopen):

        mock_urlopen.side_effect = TimeoutError("timed out")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Network error fetching URL", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_timeout_error_timeout(self, mock_log_error, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Network error fetching URL", mock_log_error.call_args[0][0])

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_fetch_url_connection_reset_error(self, mock_log_error, mock_urlopen):
        mock_urlopen.side_effect = ConnectionResetError("Connection reset by peer")

        result = download_uup.fetch_url("http://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()
        self.assertIn("Network error fetching URL", mock_log_error.call_args[0][0])


class TestRunAria2Download(unittest.TestCase):
    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_called_process_error(
        self, mock_log_error, mock_run, mock_open
    ):
        mock_run.side_effect = subprocess.CalledProcessError(1, "aria2c")
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=False
        )

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

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=False
        )

        self.assertFalse(result)
        mock_log_warn.assert_called_with(
            "\nDownload cancelled by user - session saved for resume"
        )

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_generic_exception(
        self, mock_log_error, mock_run, mock_open
    ):
        mock_run.side_effect = Exception("Unexpected error")
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=False
        )

        mock_log_error.assert_called_with(
            "An unexpected error occurred during download: Unexpected error"
        )

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_os_error(self, mock_log_error, mock_run, mock_open):
        mock_run.side_effect = FileNotFoundError("No such file")
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=False
        )

        self.assertFalse(result)
        mock_log_error.assert_called_with("System error during download: No such file")

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.Path.unlink")
    def test_run_aria2_download_success(self, mock_unlink, mock_run, mock_open):
        mock_result = unittest.mock.MagicMock()
        mock_result.stdout = "Download progress"
        mock_run.return_value = mock_result
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=True
        )

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_error_verbose(
        self, mock_log_error, mock_run, mock_open
    ):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "aria2c", output="err out", stderr="err err"
        )
        dl_list = [{"url": "http://test", "name": "test.esd"}]

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list, verbose=True
        )

        self.assertFalse(result)
        mock_log_error.assert_called_with("Download failed with exit code 1")

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.log_error")
    def test_run_aria2_download_invalid_filename(
        self, mock_log_error, mock_run, mock_open
    ):
        dl_list = [{"url": "http://test", "name": "../escape.esd"}]

        result = download_uup._run_aria2_download(Path("out"), Path("in.txt"), dl_list)

        self.assertFalse(result)
        mock_log_error.assert_called_with("Invalid filename detected: ../escape.esd")


class TestPrepareDownloadList(unittest.TestCase):
    def test_prepare_download_list_no_filter(self):
        build_id = "test-id"
        files = {
            "file1.esd": {"size": 100},
            "file2.cab": {"size": 200},
        }
        result = download_uup._prepare_download_list(build_id, files)

        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0]["url"],
            "https://uupdump.net/get.php?id=test-id&pack=file1.esd&aria2=2",
        )
        self.assertEqual(result[0]["name"], "file1.esd")

    def test_prepare_download_list_with_filter(self):
        build_id = "test-id"
        files = {
            "file1.esd": {"size": 100},
            "file2.cab": {"size": 200},
        }
        edition_filter = ["file1.esd"]
        result = download_uup._prepare_download_list(build_id, files, edition_filter)

        # .cab files are always included, .esd files are filtered
        self.assertEqual(len(result), 2)
        names = [item["name"] for item in result]
        self.assertIn("file1.esd", names)
        self.assertIn("file2.cab", names)

    def test_prepare_download_list_filter_removes_esd(self):
        build_id = "test-id"
        files = {
            "file1.esd": {"size": 100},
            "file2.esd": {"size": 200},
        }
        edition_filter = ["file1.esd"]
        result = download_uup._prepare_download_list(build_id, files, edition_filter)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "file1.esd")

    def test_prepare_download_list_empty_files(self):
        result = download_uup._prepare_download_list("test-id", {})
        self.assertEqual(result, [])


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
    @patch("download_uup.get_latest_builds_cached", return_value=None)
    @patch("download_uup.log_error")
    def test_interactive_mode_no_builds(self, mock_log_error, mock_get_builds_cached):
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_error.assert_called_once_with("Failed to fetch builds")

    @patch("download_uup.log_info")
    @patch("builtins.input", return_value="q")
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds_cached")
    def test_interactive_mode_quit(
        self,
        mock_get_builds_cached,
        mock_display_builds,
        mock_input,
        mock_log_info,
    ):
        mock_get_builds_cached.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_info.assert_called_once_with("Cancelled by user")

    @patch("download_uup.log_warn")
    @patch("builtins.input", side_effect=["invalid", "q"])
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds_cached")
    def test_interactive_mode_value_error(
        self,
        mock_get_builds_cached,
        mock_display_builds,
        mock_input,
        mock_log_warn,
    ):
        mock_get_builds_cached.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_warn.assert_any_call("Invalid input. Please enter a number.")

    @patch("download_uup.log_info")
    @patch("builtins.input", side_effect=KeyboardInterrupt)
    @patch("download_uup.display_builds")
    @patch("download_uup.get_latest_builds_cached")
    def test_interactive_mode_keyboard_interrupt(
        self,
        mock_get_builds_cached,
        mock_display_builds,
        mock_input,
        mock_log_info,
    ):
        mock_get_builds_cached.return_value = [{"id": "1", "title": "Build 1"}]
        result = download_uup.interactive_mode(Path("/tmp"))
        self.assertFalse(result)
        mock_log_info.assert_any_call("Cancelled by user")


class TestGetAvailableEditions(unittest.TestCase):
    @patch("download_uup.fetch_url")
    @patch("download_uup.log_info")
    def test_get_available_editions_success(self, mock_log_info, mock_fetch_url):
        mock_fetch_url.return_value = {
            "response": {"editionList": ["Core", "Professional"]}
        }

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

    @patch("download_uup.fetch_url")
    def test_get_api_version_success(self, mock_fetch_url):
        mock_fetch_url.return_value = '{"response": {"version": "1.0.0"}}'
        result = download_uup.get_api_version()
        self.assertEqual(result, {"version": "1.0.0"})
        mock_fetch_url.assert_called_once_with("https://api.uupdump.net/")

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
        mock_fetch_url.return_value = '{"other_key": "value"}'
        result = download_uup.get_api_version()
        self.assertEqual(result, {})


class TestDisplayBuilds(unittest.TestCase):
    def _get_print_calls(self, mock_print):
        return [call[0][0] for call in mock_print.call_args_list if call[0]]

    @patch("download_uup.log_warn")
    def test_display_builds_empty(self, mock_log_warn):
        download_uup.display_builds([])
        mock_log_warn.assert_called_once_with("No builds available.")

    @patch("builtins.print")
    def test_display_builds_success(self, mock_print):
        builds = [
            {
                "id": "build-1",
                "title": "Windows 11 Test Build",
                "build": "22621.1",
                "arch": "amd64",
                "created": "1600000000",
            }
        ]
        download_uup.display_builds(builds)

        calls = self._get_print_calls(mock_print)

        # Check header
        self.assertTrue(any("Available Windows 11 Builds" in c for c in calls))
        # Check build details
        self.assertTrue(any("[1]" in c and "Windows 11 Test Build" in c for c in calls))
        self.assertTrue(
            any(
                "Build: 22621.1" in c
                and "Arch: amd64" in c
                and "Created: 1600000000" in c
                for c in calls
            )
        )

    @patch("builtins.print")
    def test_display_builds_missing_fields(self, mock_print):
        builds = [{"id": "build-1"}]
        download_uup.display_builds(builds)

        calls = self._get_print_calls(mock_print)

        self.assertTrue(any("Unknown" in c for c in calls))  # Title
        self.assertTrue(
            any(
                "Build: N/A" in c and "Arch: N/A" in c and "Created: N/A" in c
                for c in calls
            )
        )


class TestProcessSelectedBuild(unittest.TestCase):
    @patch("download_uup.download_build", return_value=True)
    @patch("builtins.input", return_value="y")
    @patch("download_uup.select_editions", return_value=None)
    @patch("download_uup.get_build_info_cached")
    def test_process_selected_build_success(
        self,
        mock_get_build_info_cached,
        mock_select_editions,
        mock_input,
        mock_download_build,
    ):
        mock_get_build_info_cached.return_value = {"files": {}}
        selected_build = {"id": "test-build-id", "title": "Test Build"}

        result = download_uup._process_selected_build(
            selected_build, Path("/tmp"), verbose=False
        )

        self.assertTrue(result)
        mock_download_build.assert_called_once()

    @patch("download_uup.download_build", return_value=True)
    @patch("download_uup.resolve_edition_filter", return_value=["filter"])
    @patch("download_uup.get_build_info_cached")
    def test_process_selected_build_with_edition(
        self,
        mock_get_build_info_cached,
        mock_resolve_edition_filter,
        mock_download_build,
    ):
        mock_get_build_info_cached.return_value = {"files": {"a.esd": {"size": 1}}}
        selected_build = {"id": "test-build-id", "title": "Test Build"}

        result = download_uup._process_selected_build(
            selected_build, Path("uup_files"), edition="Professional"
        )

        self.assertTrue(result)
        mock_download_build.assert_called_once()
        mock_resolve_edition_filter.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch("download_uup.select_editions", return_value=None)
    @patch("download_uup.get_build_info_cached")
    def test_process_selected_build_cancelled(
        self, mock_get_build_info_cached, mock_select_editions, mock_input
    ):
        mock_get_build_info_cached.return_value = {"files": {"a.esd": {"size": 1}}}
        selected_build = {"id": "test-build-id", "title": "Test Build"}

        result = download_uup._process_selected_build(selected_build, Path("uup_files"))

        self.assertFalse(result)


class TestPrepareOutputDirectory(unittest.TestCase):
    @patch("builtins.input", return_value="")
    def test_prepare_output_directory_creates_dir(self, mock_input):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output" / "uup_files"
            # The directory doesn't exist yet
            download_uup._prepare_output_directory(output_path)
            # Directory should be created
            self.assertTrue(output_path.exists())

    @patch("builtins.input", return_value="y")
    def test_prepare_output_directory_clears_files(self, mock_input):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output" / "uup_files"
            output_path.mkdir(parents=True, exist_ok=True)
            # Create a test file
            (output_path / "test.txt").write_text("test content")

            download_uup._prepare_output_directory(output_path)
            # Test file should be deleted
            self.assertFalse((output_path / "test.txt").exists())

    def test_prepare_output_directory_creates_empty_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output" / "uup_files"
            download_uup._prepare_output_directory(output_path)
            self.assertTrue(output_path.exists())


class TestProfiles(unittest.TestCase):
    def test_get_profiles_returns_dict(self):
        result = download_uup.get_profiles()
        self.assertIsInstance(result, dict)
        self.assertIn("minimal", result)
        self.assertIn("standard", result)
        self.assertIn("gaming", result)
        self.assertIn("enterprise", result)
        self.assertIn("dev", result)

    def test_get_profile_existing(self):
        result = download_uup.get_profile("minimal")
        self.assertIsNotNone(result)
        self.assertEqual(result["edition"], "Core")

    def test_get_profile_nonexistent(self):
        result = download_uup.get_profile("nonexistent")
        self.assertIsNone(result)

    @patch("builtins.print")
    def test_display_profiles(self, mock_print):
        download_uup.display_profiles()
        calls = [
            str(call.args[0]) if call.args else "" for call in mock_print.call_args_list
        ]
        self.assertTrue(any("Available Build Profiles" in c for c in calls))


class TestParseArgsWithPreset(unittest.TestCase):
    def test_parse_args_preset(self):
        args = parse_args(["--preset", "gaming"])
        self.assertEqual(args.preset, "gaming")

    def test_parse_args_list_presets(self):
        args = parse_args(["--list-presets"])
        self.assertTrue(args.list_presets)


class TestPinFunctions(unittest.TestCase):
    """Tests for get_pinned_build/save_pinned_build using a temp project root."""

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        # Patch Path so the project root is the temp dir
        self._orig_path = download_uup.Path

        def _patched_path(*args, **kwargs):
            # Replace the project_root path with our temp dir
            if args and args[0] == __file__:
                self._orig_path(*args, **kwargs)
                return MagicMock()
            return self._orig_path(*args, **kwargs)

        # Simpler approach: monkey-patch the function's resolution
        self._pin_path = self.tmp_path / ".uup-pin.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_get_pinned_build_no_file(self):
        # When the pin file doesn't exist, returns None
        # Use a path that definitely doesn't exist
        result = download_uup.get_pinned_build()
        # If repo has no pin file, returns None
        self.assertIsNone(result)

    def test_parse_args_pin_build(self):
        args = parse_args(["--build-id", "abc-123", "--pin-build"])
        self.assertTrue(args.pin_build)
        self.assertEqual(args.build_id, "abc-123")

    def test_parse_args_use_pin(self):
        args = parse_args(["--use-pin"])
        self.assertTrue(args.use_pin)

    def test_parse_args_show_pin(self):
        args = parse_args(["--show-pin"])
        self.assertTrue(args.show_pin)


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._cwd = os.getcwd()
        os.chdir(self.tmp)
        download_uup.cache_clear()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cache_set_and_get(self):
        ok = download_uup.cache_set("mykey", {"a": 1, "b": [1, 2]})
        self.assertTrue(ok)
        result = download_uup.cache_get("mykey", ttl_seconds=60)
        self.assertEqual(result, {"a": 1, "b": [1, 2]})

    def test_cache_get_missing(self):
        self.assertIsNone(download_uup.cache_get("nope", ttl_seconds=60))

    def test_cache_get_expired(self):
        download_uup.cache_set("k", "v")
        # ttl=0 should treat it as expired
        self.assertIsNone(download_uup.cache_get("k", ttl_seconds=0))

    def test_cache_clear_single(self):
        download_uup.cache_set("a", 1)
        download_uup.cache_set("b", 2)
        removed = download_uup.cache_clear("a")
        self.assertEqual(removed, 1)
        self.assertIsNone(download_uup.cache_get("a", ttl_seconds=60))
        self.assertEqual(download_uup.cache_get("b", ttl_seconds=60), 2)

    def test_cache_clear_all(self):
        download_uup.cache_set("a", 1)
        download_uup.cache_set("b", 2)
        removed = download_uup.cache_clear()
        self.assertGreaterEqual(removed, 2)
        self.assertIsNone(download_uup.cache_get("a", ttl_seconds=60))
        self.assertIsNone(download_uup.cache_get("b", ttl_seconds=60))

    def test_cache_get_corrupt_json(self):
        cache_dir = download_uup.get_cache_dir()
        cache_file = cache_dir / download_uup._safe_cache_name("corrupt")
        cache_file.write_text("{ not json")
        self.assertIsNone(download_uup.cache_get("corrupt", ttl_seconds=60))

    def test_cache_get_malformed_entry(self):
        cache_dir = download_uup.get_cache_dir()
        cache_file = cache_dir / download_uup._safe_cache_name("malformed")
        cache_file.write_text(json.dumps(["just", "a", "list"]))
        self.assertIsNone(download_uup.cache_get("malformed", ttl_seconds=60))

    def test_safe_cache_name_sanitizes(self):
        name = download_uup._safe_cache_name("foo/bar baz?")
        self.assertNotIn("/", name)
        self.assertTrue(name.endswith(".json"))

    def test_latest_builds_cached_uses_cache(self):
        from unittest.mock import patch

        sample = [
            {"id": "b1", "title": "Test", "created": 1, "build": "1", "arch": "x64"}
        ]
        with patch.object(
            download_uup, "get_latest_builds", return_value=sample
        ) as mock_api:
            first = download_uup.get_latest_builds_cached(max_results=5, ttl_seconds=60)
            second = download_uup.get_latest_builds_cached(
                max_results=5, ttl_seconds=60
            )
            self.assertEqual(first, sample)
            self.assertEqual(second, sample)
            self.assertEqual(mock_api.call_count, 1)

    def test_latest_builds_cached_force_refresh(self):
        from unittest.mock import patch

        sample = [{"id": "b1", "title": "Test"}]
        with patch.object(
            download_uup, "get_latest_builds", return_value=sample
        ) as mock_api:
            download_uup.get_latest_builds_cached(
                max_results=5, ttl_seconds=60, force_refresh=True
            )
            download_uup.get_latest_builds_cached(
                max_results=5, ttl_seconds=60, force_refresh=True
            )
            self.assertEqual(mock_api.call_count, 2)

    def test_latest_builds_cached_api_failure_no_cache(self):
        from unittest.mock import patch

        with patch.object(download_uup, "get_latest_builds", return_value=None):
            result = download_uup.get_latest_builds_cached(
                max_results=5, ttl_seconds=60
            )
            self.assertIsNone(result)

    def test_build_info_cached_uses_cache(self):
        from unittest.mock import patch

        info = {"files": {"a.cab": {"size": 1}}}
        with patch.object(
            download_uup, "get_build_info", return_value=info
        ) as mock_api:
            r1 = download_uup.get_build_info_cached("xyz", ttl_seconds=60)
            r2 = download_uup.get_build_info_cached("xyz", ttl_seconds=60)
            self.assertEqual(r1, info)
            self.assertEqual(r2, info)
            self.assertEqual(mock_api.call_count, 1)

    def test_parse_args_cache_flags(self):
        args = parse_args(["--no-cache", "--cache-ttl", "120"])
        self.assertTrue(args.no_cache)
        self.assertEqual(args.cache_ttl, 120)
        self.assertEqual(args.cache_ttl, 120)

        args2 = parse_args(["--clear-cache"])
        self.assertTrue(args2.clear_cache)


class TestEditionSelection(unittest.TestCase):
    def _build_info(self):
        return {
            "files": {
                "Microsoft.Windows.Professional.esd": {"size": 100},
                "Microsoft.Windows.Enterprise.esd": {"size": 100},
                "Microsoft.Windows.Home.esd": {"size": 100},
                "Microsoft.Windows.Core.esd": {"size": 100},
                "Microsoft.Windows.Education.esd": {"size": 100},
                "Microsoft.Windows.SomeUpdate.cab": {"size": 50},
            }
        }

    def test_list_edition_files_extracts_known(self):
        result = download_uup.list_edition_files(self._build_info())
        self.assertIn("professional", result)
        self.assertIn("enterprise", result)
        self.assertIn("home", result)
        self.assertIn("core", result)
        self.assertIn("education", result)
        self.assertNotIn("Microsoft.Windows.SomeUpdate.cab", str(result))

    def test_list_edition_files_empty(self):
        self.assertEqual(download_uup.list_edition_files({"files": {}}), {})

    def test_resolve_edition_filter_none(self):
        result = download_uup.resolve_edition_filter(self._build_info(), None)
        self.assertIsNone(result)

    def test_resolve_edition_filter_known(self):
        result = download_uup.resolve_edition_filter(self._build_info(), "professional")
        self.assertEqual(result, ["Microsoft.Windows.Professional.esd"])

    def test_resolve_edition_filter_case_insensitive(self):
        result = download_uup.resolve_edition_filter(self._build_info(), "ENTERPRISE")
        self.assertEqual(result, ["Microsoft.Windows.Enterprise.esd"])

    def test_resolve_edition_filter_prefix(self):
        result = download_uup.resolve_edition_filter(self._build_info(), "home")
        self.assertEqual(result, ["Microsoft.Windows.Home.esd"])

    def test_resolve_edition_filter_unknown(self):
        result = download_uup.resolve_edition_filter(self._build_info(), "datacenter")
        self.assertIsNone(result)

    def test_resolve_edition_filter_no_edition_files(self):
        info = {"files": {"Microsoft.Windows.Updates.cab": {"size": 1}}}
        result = download_uup.resolve_edition_filter(info, "professional")
        self.assertIsNone(result)

    def test_parse_args_edition_flag(self):
        args = parse_args(["--build-id", "abc", "--edition", "enterprise"])
        self.assertEqual(args.edition, "enterprise")
        self.assertEqual(args.build_id, "abc")


class TestComponentGroups(unittest.TestCase):
    """Tests for component groups loading, validation and CLI integration."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.groups_file = os.path.join(self.tmpdir, "component_groups.json")
        self.sample_data = {
            "_about": "test fixture",
            "groups": {
                "gaming": {
                    "description": "Game launchers",
                    "patterns": ["*Xbox*", "*Solitaire*"],
                },
                "telemetry": {
                    "description": "Telemetry and AI",
                    "patterns": ["*Copilot*", "*Recall*"],
                },
            },
        }
        with open(self.groups_file, "w", encoding="utf-8") as f:
            json.dump(self.sample_data, f)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_component_groups_returns_groups(self):
        groups = download_uup.load_component_groups(self.groups_file)
        self.assertIn("gaming", groups)
        self.assertIn("telemetry", groups)
        self.assertEqual(groups["gaming"]["patterns"], ["*Xbox*", "*Solitaire*"])
        self.assertEqual(groups["gaming"]["description"], "Game launchers")

    def test_load_component_groups_missing_file(self):
        result = download_uup.load_component_groups("/nonexistent/path.json")
        self.assertEqual(result, {})

    def test_load_component_groups_malformed(self):
        bad_file = os.path.join(self.tmpdir, "bad.json")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json")
        result = download_uup.load_component_groups(bad_file)
        self.assertEqual(result, {})

    def test_load_component_groups_skips_invalid_entries(self):
        mixed_data = {
            "groups": {
                "good": {"patterns": ["*Foo*"]},
                "no_patterns": {"description": "no patterns"},
                "bad_patterns": {"patterns": "not a list"},
                "not_a_dict": ["list", "value"],
            }
        }
        path = os.path.join(self.tmpdir, "mixed.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mixed_data, f)
        result = download_uup.load_component_groups(path)
        self.assertIn("good", result)
        self.assertNotIn("no_patterns", result)
        self.assertNotIn("bad_patterns", result)
        self.assertNotIn("not_a_dict", result)

    def test_load_component_groups_top_level_dict(self):
        # Accepts both {"groups": {...}} and a bare mapping
        flat = {"gaming": {"patterns": ["*Xbox*"]}}
        path = os.path.join(self.tmpdir, "flat.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(flat, f)
        result = download_uup.load_component_groups(path)
        self.assertIn("gaming", result)

    def test_list_component_groups_sorted(self):
        result = download_uup.list_component_groups(self.groups_file)
        self.assertEqual(result, ["gaming", "telemetry"])

    def test_get_component_group_existing(self):
        group = download_uup.get_component_group("gaming", self.groups_file)
        self.assertIsNotNone(group)
        self.assertIn("*Xbox*", group["patterns"])

    def test_get_component_group_missing(self):
        result = download_uup.get_component_group("nope", self.groups_file)
        self.assertIsNone(result)

    def test_validate_component_groups_all_valid(self):
        result = download_uup.validate_component_groups(
            ["gaming", "telemetry"], self.groups_file
        )
        self.assertEqual(result, ["gaming", "telemetry"])

    def test_validate_component_groups_filters_unknown(self):
        result = download_uup.validate_component_groups(
            ["gaming", "nope", "telemetry"], self.groups_file
        )
        self.assertEqual(result, ["gaming", "telemetry"])

    def test_collect_component_patterns_dedupes(self):
        patterns = download_uup.collect_component_patterns(
            ["gaming", "telemetry"], self.groups_file
        )
        self.assertEqual(patterns, ["*Xbox*", "*Solitaire*", "*Copilot*", "*Recall*"])

    def test_collect_component_patterns_dedupes_overlap(self):
        # Add overlap
        overlap_file = os.path.join(self.tmpdir, "overlap.json")
        with open(overlap_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "groups": {
                        "a": {"patterns": ["*X*", "*Y*"]},
                        "b": {"patterns": ["*Y*", "*Z*"]},
                    }
                },
                f,
            )
        patterns = download_uup.collect_component_patterns(["a", "b"], overlap_file)
        self.assertEqual(patterns, ["*X*", "*Y*", "*Z*"])

    def test_collect_component_patterns_skips_unknown(self):
        patterns = download_uup.collect_component_patterns(
            ["gaming", "nope"], self.groups_file
        )
        self.assertEqual(patterns, ["*Xbox*", "*Solitaire*"])

    def test_write_component_groups_for_build_success(self):
        out_path = os.path.join(self.tmpdir, ".uup-groups")
        ok = download_uup.write_component_groups_for_build(
            ["gaming", "telemetry"], out_path
        )
        self.assertTrue(ok)
        with open(out_path) as f:
            contents = f.read()
        self.assertEqual(contents, "gaming\ntelemetry\n")

    def test_write_component_groups_for_build_failure(self):
        ok = download_uup.write_component_groups_for_build(
            ["gaming"], "/no/such/dir/.uup-groups"
        )
        self.assertFalse(ok)

    def test_parse_args_groups_flag(self):
        args = parse_args(["--groups", "gaming, telemetry,oem"])
        self.assertEqual(args.groups, "gaming, telemetry,oem")
        self.assertFalse(args.list_groups)

    def test_parse_args_list_groups_flag(self):
        args = parse_args(["--list-groups"])
        self.assertTrue(args.list_groups)

    def test_parse_args_write_groups_flag(self):
        args = parse_args(["--groups", "gaming,telemetry", "--write-groups", "/tmp/x"])
        self.assertEqual(args.write_groups, "/tmp/x")
        self.assertEqual(args.groups, "gaming,telemetry")


class TestMainInfoModes(unittest.TestCase):
    """Tests for the high-level main() entrypoint info-only branches."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmp)
        download_uup.cache_clear()

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("download_uup.cache_clear", return_value=3)
    @patch("download_uup.log_success")
    def test_main_clear_cache(self, mock_log_success, mock_cache_clear):
        with patch.object(sys, "argv", ["download_uup.py", "--clear-cache"]):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_cache_clear.assert_called_once()
        mock_log_success.assert_called_once()

    @patch("download_uup.display_profiles")
    def test_main_list_presets(self, mock_display):
        with patch.object(sys, "argv", ["download_uup.py", "--list-presets"]):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_display.assert_called_once()

    @patch("download_uup.get_pinned_build", return_value=None)
    @patch("download_uup.log_info")
    def test_main_show_pin_none(self, mock_log_info, mock_get_pin):
        with patch.object(sys, "argv", ["download_uup.py", "--show-pin"]):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_get_pin.assert_called_once()

    @patch("download_uup.get_pinned_build", return_value={"build_id": "abc"})
    def test_main_show_pin_present(self, mock_get_pin):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--show-pin"]),
            patch("builtins.print") as mock_print,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        self.assertTrue(mock_print.called)

    @patch(
        "download_uup.get_pinned_build",
        return_value={"build_id": "abc", "title": "Win11", "edition": "Pro"},
    )
    def test_main_show_pin_with_title_and_edition(self, mock_get_pin):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--show-pin"]),
            patch("builtins.print") as mock_print,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
        self.assertIn("Win11", printed)
        self.assertIn("Pro", printed)

    @patch("download_uup.display_component_groups")
    def test_main_list_groups(self, mock_display):
        with patch.object(sys, "argv", ["download_uup.py", "--list-groups"]):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_display.assert_called_once()

    def test_main_write_groups_requires_groups(self):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--write-groups", "/tmp/x"]),
            patch("download_uup.log_error") as mock_log_error,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_log_error.assert_called()

    @patch("download_uup.write_component_groups_for_build", return_value=False)
    def test_main_write_groups_write_failure(self, mock_write):
        with patch.object(
            sys,
            "argv",
            ["download_uup.py", "--groups", "gaming", "--write-groups", "/tmp/x"],
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)

    def test_main_use_pin_no_pin(self):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--use-pin"]),
            patch("download_uup.get_pinned_build", return_value=None),
            patch("download_uup.log_error") as mock_log_error,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_log_error.assert_called()

    def test_main_pin_build_without_build_id(self):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--pin-build"]),
            patch("download_uup.log_error") as mock_log_error,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_log_error.assert_called()

    @patch("download_uup.save_pinned_build", return_value=False)
    def test_main_pin_build_failure(self, mock_save):
        with patch.object(
            sys,
            "argv",
            ["download_uup.py", "--build-id", "abc", "--pin-build"],
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_save.assert_called_once()

    @patch("download_uup.check_dependencies", return_value=False)
    def test_main_check_dependencies_failure(self, mock_check):
        with patch.object(sys, "argv", ["download_uup.py"]):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_check.assert_called_once()

    @patch("download_uup.get_latest_builds_cached", return_value=[{"id": "x"}])
    @patch("download_uup.display_builds")
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_list_builds(self, mock_check, mock_display, mock_get):
        with patch.object(sys, "argv", ["download_uup.py", "--list"]):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_display.assert_called_once()

    @patch("download_uup.get_latest_builds_cached", return_value=None)
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_list_builds_no_results(self, mock_check, mock_get):
        with patch.object(sys, "argv", ["download_uup.py", "--list"]):
            rc = download_uup.main()
        self.assertEqual(rc, 1)

    @patch("download_uup.get_build_info_cached", return_value=None)
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_build_id_no_info(self, mock_check, mock_get_info):
        with (
            patch.object(sys, "argv", ["download_uup.py", "--build-id", "abc"]),
            patch("download_uup.log_error") as mock_log_error,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_log_error.assert_called()

    @patch(
        "download_uup.get_build_info_cached",
        return_value={"files": {"Microsoft.Windows.Professional.esd": {"size": 1}}},
    )
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_build_id_with_edition(self, mock_check, mock_get_info):
        with (
            patch.object(
                sys,
                "argv",
                ["download_uup.py", "--build-id", "abc", "--edition", "professional"],
            ),
            patch("download_uup.download_build", return_value=True) as mock_dl,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_dl.assert_called_once()
        args, _ = mock_dl.call_args
        self.assertEqual(args[2], ["Microsoft.Windows.Professional.esd"])

    @patch("download_uup.get_latest_builds_cached", return_value=[{"id": "x"}])
    @patch("download_uup.display_builds")
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_preset_mode(self, mock_check, mock_display, mock_get):
        with patch.object(sys, "argv", ["download_uup.py", "--preset", "minimal"]):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_display.assert_called_once()

    @patch("download_uup.get_latest_builds_cached", return_value=None)
    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_preset_no_builds(self, mock_check, mock_get):
        with patch.object(sys, "argv", ["download_uup.py", "--preset", "minimal"]):
            rc = download_uup.main()
        self.assertEqual(rc, 1)

    def test_main_preset_unknown(self):
        with (
            patch.object(
                sys, "argv", ["download_uup.py", "--preset", "no-such-profile"]
            ),
            patch("download_uup.log_error") as mock_log_error,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 1)
        mock_log_error.assert_called()

    @patch("download_uup.check_dependencies", return_value=True)
    def test_main_interactive(self, mock_check):
        with (
            patch.object(sys, "argv", ["download_uup.py"]),
            patch(
                "download_uup.interactive_mode", return_value=True
            ) as mock_interactive,
        ):
            rc = download_uup.main()
        self.assertEqual(rc, 0)
        mock_interactive.assert_called_once()


class TestHandleInfoMode(unittest.TestCase):
    """Tests for _handle_info_mode individual branches."""

    @patch(
        "download_uup.get_available_editions",
        return_value={"editionList": ["pro"], "editionFancyNames": {"pro": "Pro"}},
    )
    def test_editions_success(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions="abc",
            languages=None,
            latest=False,
        )
        with patch("builtins.print"):
            rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 0)

    @patch("download_uup.get_available_editions", return_value=None)
    def test_editions_failure(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions="abc",
            languages=None,
            latest=False,
        )
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)

    @patch(
        "download_uup.get_available_languages",
        return_value={"langList": ["en-us"], "langFancyNames": {"en-us": "English"}},
    )
    def test_languages_success(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions=None,
            languages="abc",
            latest=False,
        )
        with patch("builtins.print"):
            rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 0)

    @patch("download_uup.get_available_languages", return_value=None)
    def test_languages_failure(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions=None,
            languages="abc",
            latest=False,
        )
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)

    @patch(
        "download_uup.fetch_latest_from_wu",
        return_value={
            "updateId": "u1",
            "updateTitle": "T",
            "foundBuild": "B",
            "arch": "x64",
        },
    )
    def test_latest_success(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions=None,
            languages=None,
            latest=True,
            arch="amd64",
            ring="Retail",
        )
        with patch("builtins.print"):
            rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 0)

    @patch("download_uup.fetch_latest_from_wu", return_value=None)
    def test_latest_failure(self, mock_get):
        from argparse import Namespace

        args = Namespace(
            editions=None,
            languages=None,
            latest=True,
            arch="amd64",
            ring="Retail",
        )
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)

    def test_not_handled(self):
        from argparse import Namespace

        args = Namespace(
            editions=None,
            languages=None,
            latest=False,
            update_info=None,
            save_delta_manifest=None,
            delta_info=None,
        )
        rc = download_uup._handle_info_mode(args)
        self.assertIsNone(rc)


class TestResolveOutputDir(unittest.TestCase):
    def test_resolve_output_dir_within_project(self):
        out = download_uup._resolve_output_dir("uup_files")
        self.assertIsNotNone(out)
        self.assertTrue(str(out).endswith("uup_files"))

    def test_resolve_output_dir_absolute_within_project(self):
        project_root = Path(download_uup.__file__).parent.parent.resolve()
        target = project_root / "uup_files"
        out = download_uup._resolve_output_dir(str(target))
        self.assertEqual(out, target)

    def test_resolve_output_dir_traversal(self):
        out = download_uup._resolve_output_dir("../../etc/passwd")
        self.assertIsNone(out)


class TestCacheEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._cwd = os.getcwd()
        os.chdir(self.tmp)
        download_uup.cache_clear()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cache_get_malformed_structure(self):
        cache_dir = download_uup.get_cache_dir()
        cache_file = cache_dir / download_uup._safe_cache_name("weird")
        cache_file.write_text(json.dumps({"timestamp": 1.0}))
        self.assertIsNone(download_uup.cache_get("weird", ttl_seconds=60))

    def test_cache_get_corrupt_unlinks(self):
        cache_dir = download_uup.get_cache_dir()
        cache_file = cache_dir / download_uup._safe_cache_name("bad")
        cache_file.write_text("{ not json")
        download_uup.cache_get("bad", ttl_seconds=60)
        self.assertFalse(cache_file.exists())

    def test_cache_set_non_serializable(self):
        ok = download_uup.cache_set("oops", {"fn": lambda: 1})
        self.assertFalse(ok)

    def test_cache_clear_missing_key(self):
        removed = download_uup.cache_clear("never-existed")
        self.assertEqual(removed, 0)

    def test_cache_clear_with_key_present(self):
        download_uup.cache_set("present", 42)
        removed = download_uup.cache_clear("present")
        self.assertEqual(removed, 1)


class TestFetchUrlBranches(unittest.TestCase):
    def setUp(self):
        download_uup._url_cache.clear()

    def tearDown(self):
        download_uup._url_cache.clear()

    @patch("download_uup.urlopen")
    def test_cache_hit(self, mock_urlopen):
        download_uup._url_cache["cached-url:False"] = "cached-value"
        result = download_uup.fetch_url("cached-url")
        self.assertEqual(result, "cached-value")
        mock_urlopen.assert_not_called()

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_json_decode_error(self, mock_log_error, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        result = download_uup.fetch_url("http://example.com", return_json=True)
        self.assertIsNone(result)
        mock_log_error.assert_called()

    @patch("download_uup.urlopen")
    @patch("download_uup.log_error")
    def test_json_not_dict(self, mock_log_error, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'["a", "list"]'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        result = download_uup.fetch_url("http://example.com", return_json=True)
        self.assertIsNone(result)
        mock_log_error.assert_called()

    @patch("download_uup.urlopen")
    def test_json_success_cached(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"a": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        result = download_uup.fetch_url("http://example.com", return_json=True)
        self.assertEqual(result, {"a": 1})


class TestGetApiVersion(unittest.TestCase):
    @patch("download_uup.fetch_url", return_value='{"response": {"apiVersion": "1.0"}}')
    def test_success(self, mock_fetch):
        info = download_uup.get_api_version()
        self.assertEqual(info, {"apiVersion": "1.0"})

    @patch("download_uup.fetch_url", return_value=None)
    def test_no_response(self, mock_fetch):
        self.assertIsNone(download_uup.get_api_version())

    @patch("download_uup.fetch_url", return_value="not json at all")
    def test_json_decode_error(self, mock_fetch):
        self.assertIsNone(download_uup.get_api_version())


class TestDisplayComponentGroups(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "groups.json")
        with open(self.path, "w") as f:
            json.dump(
                {
                    "groups": {
                        "gaming": {
                            "description": "Games",
                            "patterns": ["*Xbox*"],
                        },
                        "oem": {
                            "description": "",
                            "patterns": ["*OEM*"],
                        },
                    }
                },
                f,
            )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_displays_all(self):
        with patch("builtins.print") as mock_print:
            download_uup.display_component_groups(self.path)
        self.assertTrue(mock_print.called)
        # Each call may use a separate string arg; concatenate all positional args
        out = " ".join(
            " ".join(str(a) for a in c.args) for c in mock_print.call_args_list
        )
        self.assertIn("gaming", out)
        self.assertIn("oem", out)

    def test_empty(self):
        empty = os.path.join(self.tmpdir, "empty.json")
        with open(empty, "w") as f:
            json.dump({}, f)
        with patch("builtins.print") as mock_print:
            download_uup.display_component_groups(empty)
        out = " ".join(
            " ".join(str(a) for a in c.args) for c in mock_print.call_args_list
        )
        self.assertIn("No component groups", out)


class TestLoadComponentGroupsEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_not_dict_top_level(self):
        path = os.path.join(self.tmpdir, "list.json")
        with open(path, "w") as f:
            json.dump(["a", "b"], f)
        self.assertEqual(download_uup.load_component_groups(path), {})

    def test_groups_not_mapping(self):
        path = os.path.join(self.tmpdir, "bad_groups.json")
        with open(path, "w") as f:
            json.dump({"groups": ["a", "b"]}, f)
        self.assertEqual(download_uup.load_component_groups(path), {})


class TestGetProfiles(unittest.TestCase):
    def test_built_in_profiles(self):
        profiles = download_uup.get_profiles()
        self.assertIsInstance(profiles, dict)
        self.assertGreater(len(profiles), 0)
        self.assertIn("minimal", profiles)

    def test_get_profile_existing(self):
        self.assertIsNotNone(download_uup.get_profile("minimal"))

    def test_get_profile_missing(self):
        self.assertIsNone(download_uup.get_profile("not-a-profile"))

    def test_display_profiles(self):
        with patch("builtins.print") as mock_print:
            download_uup.display_profiles()
        self.assertTrue(mock_print.called)


class TestSavePinnedBuild(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        # Patch script_dir / project_root for save_pinned_build
        self._real_path = download_uup.Path

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_pinned_build_minimal(self):
        # Use a build_id-only save by calling in a temp project root
        self.tmp_path / ".uup-pin.json"
        with patch.object(download_uup, "Path") as MockPath:
            MockPath.return_value.parent.parent = self.tmp_path
            ok = download_uup.save_pinned_build("b1")
        self.assertTrue(ok)


class TestSelectEditionsAllEditions(unittest.TestCase):
    """Cover enterprise/home/core/education branches in select_editions."""

    @patch("builtins.input", return_value="")
    def test_all_edition_variants_present(self, mock_input):
        build_info = {
            "files": {
                "Win_Professional.esd": {"size": 1},
                "Win_Enterprise.esd": {"size": 1},
                "Win_Home.esd": {"size": 1},
                "Win_Core.esd": {"size": 1},
                "Win_Education.esd": {"size": 1},
            }
        }
        result = download_uup.select_editions(build_info)
        self.assertIsNone(result)

    @patch("builtins.input", return_value="3")
    def test_select_home(self, mock_input):
        build_info = {
            "files": {
                "Win_Professional.esd": {"size": 1},
                "Win_Enterprise.esd": {"size": 1},
                "Win_Home.esd": {"size": 1},
            }
        }
        result = download_uup.select_editions(build_info)
        self.assertEqual(result, ["Win_Home.esd"])


class TestGetLatestBuildsEmpty(unittest.TestCase):
    @patch("download_uup.fetch_url", return_value={"response": {"builds": []}})
    def test_empty_builds_list(self, mock_fetch):
        self.assertEqual(download_uup.get_latest_builds(), [])


class TestDownloadLanguagePacks(unittest.TestCase):
    @patch("download_uup.download_build", return_value=True)
    @patch("download_uup.get_build_info_cached")
    def test_download_language_packs_success(
        self, mock_get_build_info_cached, mock_download_build
    ):
        mock_get_build_info_cached.return_value = {"files": {"foo.esd": {"size": 1}}}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_uup.download_language_packs(
                "test-id", ["en-us", "fr-fr"], tmpdir
            )
            self.assertTrue(result)
            self.assertEqual(mock_download_build.call_count, 2)
            # First call should be en-us, second should be fr-fr
            first_call_args = mock_download_build.call_args_list[0]
            self.assertIn("lang_en-us", str(first_call_args))
            second_call_args = mock_download_build.call_args_list[1]
            self.assertIn("lang_fr-fr", str(second_call_args))

    @patch("download_uup.download_build", return_value=True)
    @patch("download_uup.get_build_info_cached", return_value=None)
    def test_download_language_packs_no_files(
        self, mock_get_build_info_cached, mock_download_build
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_uup.download_language_packs("test-id", ["en-us"], tmpdir)
            self.assertFalse(result)
            mock_download_build.assert_not_called()


class TestGetBuildFiles(unittest.TestCase):
    def test_get_build_files_basic(self):
        build_info = {
            "files": {
                "a.esd": {"size": 100, "sha256": "abc"},
                "b.cab": {"size": 200},
            }
        }
        result = download_uup.get_build_files(build_info)
        self.assertEqual(set(result.keys()), {"a.esd", "b.cab"})
        self.assertEqual(result["a.esd"], {"size": 100, "sha256": "abc"})

    def test_get_build_files_empty(self):
        self.assertEqual(download_uup.get_build_files({}), {})

    def test_get_build_files_missing_files_key(self):
        self.assertEqual(download_uup.get_build_files({"other": 1}), {})

    def test_get_build_files_filters_non_dict_entries(self):
        build_info = {
            "files": {
                "a.esd": {"size": 1},
                "bad": "not-a-dict",
                42: {"size": 2},
            }
        }
        result = download_uup.get_build_files(build_info)
        self.assertEqual(list(result.keys()), ["a.esd"])

    def test_get_build_files_returns_copies(self):
        """Modifying the returned dict must not affect build_info."""
        info = {"files": {"a.esd": {"size": 1}}}
        result = download_uup.get_build_files(info)
        result["a.esd"]["size"] = 999
        self.assertEqual(info["files"]["a.esd"]["size"], 1)

    def test_get_build_files_files_not_dict(self):
        """Non-dict 'files' entry is treated as empty."""
        self.assertEqual(download_uup.get_build_files({"files": "garbage"}), {})


class TestCalculateDelta(unittest.TestCase):
    def test_identical_builds(self):
        base = target = {"a.esd": {"size": 1}, "b.cab": {"size": 2}}
        delta = download_uup.calculate_delta(base, target)
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(delta["modified"], [])
        self.assertEqual(set(delta["unchanged"]), {"a.esd", "b.cab"})

    def test_added_files(self):
        delta = download_uup.calculate_delta(
            {"a": {"size": 1}}, {"a": {"size": 1}, "b": {"size": 2}, "c": {"size": 3}}
        )
        self.assertEqual(set(delta["added"]), {"b", "c"})
        self.assertEqual(delta["removed"], [])
        self.assertEqual(delta["modified"], [])
        self.assertEqual(delta["unchanged"], ["a"])

    def test_removed_files(self):
        delta = download_uup.calculate_delta(
            {"a": {"size": 1}, "b": {"size": 2}}, {"a": {"size": 1}}
        )
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], ["b"])
        self.assertEqual(delta["modified"], [])
        self.assertEqual(delta["unchanged"], ["a"])

    def test_modified_files_size_changed(self):
        delta = download_uup.calculate_delta({"a": {"size": 1}}, {"a": {"size": 2}})
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(delta["modified"], ["a"])
        self.assertEqual(delta["unchanged"], [])

    def test_modified_files_sha256_changed(self):
        delta = download_uup.calculate_delta(
            {"a": {"size": 1, "sha256": "old"}},
            {"a": {"size": 1, "sha256": "new"}},
        )
        self.assertEqual(delta["modified"], ["a"])

    def test_modified_files_extra_key(self):
        """A new metadata key in the target should mark the file as modified."""
        delta = download_uup.calculate_delta(
            {"a": {"size": 1}}, {"a": {"size": 1, "sha256": "abc"}}
        )
        self.assertEqual(delta["modified"], ["a"])

    def test_both_empty(self):
        delta = download_uup.calculate_delta({}, {})
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(delta["modified"], [])
        self.assertEqual(delta["unchanged"], [])

    def test_disjoint_builds(self):
        delta = download_uup.calculate_delta({"a": {"size": 1}}, {"b": {"size": 2}})
        self.assertEqual(delta["added"], ["b"])
        self.assertEqual(delta["removed"], ["a"])
        self.assertEqual(delta["modified"], [])
        self.assertEqual(delta["unchanged"], [])

    def test_results_sorted(self):
        """added/removed/modified/unchanged must be sorted for stable output."""
        delta = download_uup.calculate_delta(
            {"z": {"size": 1}, "a": {"size": 1}}, {"m": {"size": 1}, "a": {"size": 1}}
        )
        self.assertEqual(delta["added"], ["m"])
        self.assertEqual(delta["removed"], ["z"])
        self.assertEqual(delta["unchanged"], ["a"])

    def test_compute_changed_files(self):
        result = download_uup.compute_changed_files(
            {"a": {"size": 1}, "b": {"size": 2}, "c": {"size": 3}},
            {"a": {"size": 1}, "b": {"size": 99}, "d": {"size": 4}},
        )
        self.assertEqual(result, {"b", "d"})


class TestFormatDeltaSummary(unittest.TestCase):
    def test_format_includes_counts(self):
        delta = {
            "added": ["a", "b"],
            "removed": ["c"],
            "modified": ["d"],
            "unchanged": ["e", "f", "g"],
        }
        text = download_uup.format_delta_summary("base", "target", delta)
        self.assertIn("base", text)
        self.assertIn("target", text)
        self.assertIn("2", text)
        self.assertIn("1", text)
        self.assertIn("3", text)


class TestDeltaManifestIO(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp()
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {
                "a.esd": {"size": 100, "sha256": "abc"},
                "b.cab": {"size": 200},
            }
            path = download_uup.save_delta_manifest("build-1", files, store_dir=tmp)
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).exists())

            loaded = download_uup.load_delta_manifest("build-1", store_dir=tmp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded, files)

    def test_load_missing_manifest_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = download_uup.load_delta_manifest("missing", store_dir=tmp)
            self.assertIsNone(result)

    def test_load_malformed_manifest_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            manifest = store / download_uup._safe_delta_filename("build-1")
            manifest.write_text("not json{", encoding="utf-8")
            self.assertIsNone(
                download_uup.load_delta_manifest("build-1", store_dir=tmp)
            )

    def test_load_manifest_filters_non_dict_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            manifest = store / download_uup._safe_delta_filename("build-1")
            manifest.write_text(
                json.dumps(
                    {"build_id": "build-1", "files": {"a": {"size": 1}, "bad": "x"}}
                ),
                encoding="utf-8",
            )
            loaded = download_uup.load_delta_manifest("build-1", store_dir=tmp)
            self.assertEqual(loaded, {"a": {"size": 1}})

    def test_load_manifest_top_level_not_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            manifest = store / download_uup._safe_delta_filename("build-1")
            manifest.write_text(json.dumps(["a", "b"]), encoding="utf-8")
            self.assertIsNone(
                download_uup.load_delta_manifest("build-1", store_dir=tmp)
            )

    def test_load_manifest_files_not_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            manifest = store / download_uup._safe_delta_filename("build-1")
            manifest.write_text(json.dumps({"files": "nope"}), encoding="utf-8")
            self.assertIsNone(
                download_uup.load_delta_manifest("build-1", store_dir=tmp)
            )

    def test_save_creates_store_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "nested" / "store"
            path = download_uup.save_delta_manifest(
                "build-1", {"a": {"size": 1}}, store_dir=nested
            )
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).exists())

    def test_safe_delta_filename(self):
        """Unsafe characters in build_id must be replaced with underscores."""
        name = download_uup._safe_delta_filename("../../etc/passwd")
        self.assertNotIn("..", name)
        self.assertNotIn("/", name)
        self.assertTrue(name.endswith(".json"))

    def test_safe_delta_filename_preserves_alnum_dash(self):
        name = download_uup._safe_delta_filename("abc-123_XYZ")
        self.assertEqual(name, "abc-123_XYZ.json")

    def test_load_manifest_path_traversal_rejected(self):
        """A build_id that escapes the store must be rejected.

        With the safer filename rules, traversal via build_id is impossible,
        so we verify the safer-by-design path: even an attempt that contains
        ``..`` is harmless because the safe filename sanitizes it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            # Save a normal manifest, then attempt to load a traversal one
            download_uup.save_delta_manifest(
                "build-1", {"a": {"size": 1}}, store_dir=tmp
            )
            # "../../../etc/passwd" sanitizes to ".._.._.._etc_passwd" which
            # is still inside the store - the path is just a non-existent
            # file. The key safety property is that the resolved path is
            # inside the store.
            with patch("download_uup.log_error") as mock_log:
                result = download_uup.load_delta_manifest(
                    "../../../etc/passwd", store_dir=tmp
                )
            self.assertIsNone(result)  # file doesn't exist
            mock_log.assert_not_called()  # and no traversal error


class TestPrepareDownloadListWithDelta(unittest.TestCase):
    def test_delta_filter_includes_only_named_files(self):
        files = {
            "a.esd": {"size": 1},
            "b.cab": {"size": 2},
            "c.esd": {"size": 3},
        }
        result = download_uup._prepare_download_list(
            "test-id", files, delta_filter={"a.esd", "b.cab"}
        )
        names = {item["name"] for item in result}
        self.assertEqual(names, {"a.esd", "b.cab"})

    def test_delta_filter_none_includes_all(self):
        files = {"a.esd": {"size": 1}, "b.cab": {"size": 2}}
        result = download_uup._prepare_download_list(
            "test-id", files, delta_filter=None
        )
        self.assertEqual(len(result), 2)

    def test_delta_filter_empty_set_excludes_all(self):
        files = {"a.esd": {"size": 1}, "b.cab": {"size": 2}}
        result = download_uup._prepare_download_list(
            "test-id", files, delta_filter=set()
        )
        self.assertEqual(result, [])

    def test_delta_filter_with_edition_filter(self):
        files = {
            "a.esd": {"size": 1},
            "b.esd": {"size": 2},
            "c.cab": {"size": 3},
        }
        # Edition filter keeps only a.esd, delta filter keeps a.esd + c.cab -> a.esd + c.cab
        result = download_uup._prepare_download_list(
            "test-id",
            files,
            edition_filter=["a.esd"],
            delta_filter={"a.esd", "c.cab"},
        )
        names = {item["name"] for item in result}
        self.assertEqual(names, {"a.esd", "c.cab"})


class TestDownloadBuildDelta(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp()
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    @patch("download_uup.save_delta_manifest")
    @patch("download_uup._run_aria2_download", return_value=True)
    @patch("download_uup.load_delta_manifest")
    def test_download_build_with_delta_filters_files(
        self, mock_load, mock_run, mock_save
    ):
        mock_load.return_value = {
            "a.esd": {"size": 100},
            "b.cab": {"size": 200},
        }
        build_info = {
            "files": {
                "a.esd": {"size": 100},
                "b.cab": {"size": 200, "sha256": "new"},  # modified
                "c.esd": {"size": 300},  # added
            }
        }
        result = download_uup.download_build(
            "target-id",
            "uup_delta_out",
            build_info=build_info,
            delta_from="base-id",
        )
        self.assertTrue(result)
        # Should have downloaded only b.cab and c.esd
        download_list_arg = mock_run.call_args[0][2]
        names = {item["name"] for item in download_list_arg}
        self.assertEqual(names, {"b.cab", "c.esd"})

    @patch("download_uup.save_delta_manifest")
    @patch("download_uup._run_aria2_download", return_value=True)
    @patch("download_uup.load_delta_manifest")
    def test_download_build_no_changes_skips_aria2(
        self, mock_load, mock_run, mock_save
    ):
        mock_load.return_value = {"a.esd": {"size": 1}, "b.cab": {"size": 2}}
        build_info = {"files": {"a.esd": {"size": 1}, "b.cab": {"size": 2}}}
        result = download_uup.download_build(
            "target-id",
            "uup_delta_out",
            build_info=build_info,
            delta_from="base-id",
        )
        self.assertTrue(result)
        mock_run.assert_not_called()
        # Manifest for target is still saved for future delta runs
        mock_save.assert_called_once()
        self.assertEqual(mock_save.call_args[0][0], "target-id")

    @patch("download_uup.save_delta_manifest")
    @patch("download_uup._run_aria2_download", return_value=True)
    @patch("download_uup.load_delta_manifest", return_value=None)
    def test_download_build_delta_from_missing_manifest_downloads_all(
        self, mock_load, mock_run, mock_save
    ):
        build_info = {"files": {"a.esd": {"size": 1}, "b.cab": {"size": 2}}}
        result = download_uup.download_build(
            "target-id",
            "uup_delta_out",
            build_info=build_info,
            delta_from="missing",
        )
        self.assertTrue(result)
        download_list_arg = mock_run.call_args[0][2]
        self.assertEqual(len(download_list_arg), 2)

    @patch("download_uup.save_delta_manifest")
    @patch("download_uup._run_aria2_download", return_value=True)
    def test_download_build_without_delta_saves_manifest(self, mock_run, mock_save):
        build_info = {"files": {"a.esd": {"size": 1}}}
        download_uup.download_build(
            "test-id",
            "uup_delta_out",
            build_info=build_info,
        )
        # Manifest saved for the current build even without delta
        self.assertTrue(mock_save.called)
        self.assertEqual(mock_save.call_args[0][0], "test-id")

    @patch("download_uup.save_delta_manifest")
    @patch("download_uup._run_aria2_download", return_value=False)
    @patch("download_uup.load_delta_manifest")
    def test_download_build_failed_does_not_save_manifest(
        self, mock_load, mock_run, mock_save
    ):
        """A failed aria2 run must not overwrite the saved manifest."""
        mock_load.return_value = {"a.esd": {"size": 1}}
        build_info = {"files": {"a.esd": {"size": 2}}}
        result = download_uup.download_build(
            "test-id",
            "uup_delta_out",
            build_info=build_info,
            delta_from="base-id",
        )
        self.assertFalse(result)
        mock_save.assert_not_called()


class TestDeltaCLIArgs(unittest.TestCase):
    def test_delta_from_flag(self):
        args = download_uup.parse_args(["--build-id", "abc", "--delta-from", "xyz"])
        self.assertEqual(args.delta_from, "xyz")

    def test_delta_store_flag(self):
        args = download_uup.parse_args(
            ["--build-id", "abc", "--delta-store", "/some/path"]
        )
        self.assertEqual(args.delta_store, "/some/path")

    def test_save_delta_manifest_flag(self):
        args = download_uup.parse_args(["--save-delta-manifest", "abc"])
        self.assertEqual(args.save_delta_manifest, "abc")

    def test_delta_info_flag(self):
        args = download_uup.parse_args(["--delta-info", "abc"])
        self.assertEqual(args.delta_info, "abc")

    def test_defaults_to_none(self):
        args = download_uup.parse_args(["--list"])
        self.assertIsNone(args.delta_from)
        self.assertIsNone(args.delta_store)
        self.assertIsNone(args.save_delta_manifest)
        self.assertIsNone(args.delta_info)


class TestHandleDeltaInfoMode(unittest.TestCase):
    @patch("download_uup.log_warn")
    @patch("download_uup.log_success")
    @patch("download_uup.get_build_info_cached")
    def test_save_delta_manifest_success(self, mock_get, mock_success, mock_warn):
        mock_get.return_value = {"files": {"a.esd": {"size": 1}}}
        args = download_uup.parse_args(
            ["--save-delta-manifest", "abc-123", "--delta-store", "/tmp/x"]
        )
        with tempfile.TemporaryDirectory() as tmp:
            args.delta_store = tmp
            rc = download_uup._handle_info_mode(args)
            self.assertEqual(rc, 0)
            mock_success.assert_called()

    @patch("download_uup.log_error")
    @patch("download_uup.get_build_info_cached", return_value=None)
    def test_save_delta_manifest_no_build_info(self, mock_get, mock_log):
        args = download_uup.parse_args(["--save-delta-manifest", "missing"])
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)
        mock_log.assert_called()

    @patch("download_uup.get_build_info_cached")
    def test_save_delta_manifest_empty_files(self, mock_get):
        mock_get.return_value = {"files": {}}
        args = download_uup.parse_args(["--save-delta-manifest", "abc"])
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)

    @patch("download_uup.load_delta_manifest", return_value={"a.esd": {"size": 1}})
    def test_delta_info_success(self, mock_load):
        args = download_uup.parse_args(["--delta-info", "abc"])
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 0)

    @patch("download_uup.log_warn")
    @patch("download_uup.load_delta_manifest", return_value=None)
    def test_delta_info_missing(self, mock_load, mock_warn):
        args = download_uup.parse_args(["--delta-info", "missing"])
        rc = download_uup._handle_info_mode(args)
        self.assertEqual(rc, 1)
        mock_warn.assert_called()


class TestMainDeltaModes(unittest.TestCase):
    @patch("download_uup.check_dependencies")
    def test_save_delta_manifest_in_info_only(self, mock_check):
        """--save-delta-manifest must be treated as info-only (no dep check)."""
        with (
            patch("download_uup._handle_info_mode", return_value=0) as mock_handle,
            patch(
                "download_uup.parse_args",
                return_value=argparse.Namespace(
                    build_id=None,
                    editions=None,
                    languages=None,
                    latest=False,
                    save_delta_manifest="abc",
                    delta_info=None,
                    delta_from=None,
                    delta_store=None,
                    list_presets=False,
                    show_pin=False,
                    pin_build=False,
                    use_pin=False,
                    list_groups=False,
                    write_groups=None,
                    list=False,
                    clear_cache=False,
                    output="uup_files",
                    cache_ttl=3600,
                    no_cache=False,
                    preset=None,
                    groups=None,
                    resume=True,
                    verbose=False,
                    edition=None,
                    update_info=None,
                    language=None,
                    languages_download=None,
                    arch="amd64",
                    ring="Retail",
                    max_results=10,
                    preset_mode=False,
                    mirrors=None,
                ),
            ),
        ):
            rc = download_uup.main()
            self.assertEqual(rc, 0)
            mock_handle.assert_called_once()
            mock_check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
