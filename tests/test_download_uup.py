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

    @patch('download_uup.get_build_info')
    def test_build_info_provided_skips_api_call(self, mock_get_build_info):
        """When build_info is passed in, get_build_info must not be called."""
        # Passing an empty files dict causes an early return ("No files found"),
        # so no filesystem or network activity is needed.
        build_info = {"files": {}}
        result = download_uup.download_build("fake-id", "/tmp/out", build_info=build_info)

        mock_get_build_info.assert_not_called()
        self.assertFalse(result)

    @patch('download_uup.get_build_info', return_value=None)
    def test_no_build_info_calls_api(self, mock_get_build_info):
        """When build_info is not passed, get_build_info is called."""
        result = download_uup.download_build("fake-id", "/tmp/out")
        mock_get_build_info.assert_called_once_with("fake-id")
        self.assertFalse(result)


class TestCheckDependencies(unittest.TestCase):
    @patch('shutil.which')
    @patch('download_uup.log_error')
    @patch('download_uup.log_info')
    def test_check_dependencies_all_present(self, mock_log_info, mock_log_error, mock_which):
        # Mock shutil.which to return a path for aria2c
        mock_which.return_value = '/usr/bin/aria2c'


class TestDownloadUUP(unittest.TestCase):
    def test_parse_args_defaults(self):
        args = parse_args([])
        self.assertEqual(args.output, "uup_files")
        self.assertIsNone(args.build_id)
        self.assertFalse(args.list)
        self.assertEqual(args.max_results, 10)


class TestDownloadBuild(unittest.TestCase):
    @patch("download_uup.get_build_info")
    @patch("download_uup._prepare_output_directory")
    @patch("download_uup._prepare_download_list")
    @patch("download_uup._run_aria2_download")
    @patch("download_uup.log_success")
    @patch("download_uup.log_error")
    def test_download_build_success(
        self,
        mock_log_error,
        mock_log_success,
        mock_run_aria2,
        mock_prep_list,
        mock_prep_dir,
        mock_get_info,
    ):
        mock_get_info.return_value = {"files": {"test.esd": {"size": 100}}}
        mock_prep_list.return_value = [{"url": "http://test", "name": "test.esd"}]
        mock_run_aria2.return_value = True

        result = download_uup.download_build("build123", "out_dir")

        self.assertTrue(result)
        mock_get_info.assert_called_with("build123")
        mock_prep_dir.assert_called_once()
        mock_prep_list.assert_called_once()
        mock_run_aria2.assert_called_once()
        mock_log_success.assert_called_with("Will download 1 files")

    @patch("download_uup.get_build_info")
    @patch("download_uup.log_error")
    def test_download_build_no_info(self, mock_log_error, mock_get_info):
        mock_get_info.return_value = None

        result = download_uup.download_build("build123", "out_dir")

        self.assertFalse(result)
        mock_log_error.assert_called_with("Failed to get build information")


class TestHelpers(unittest.TestCase):
    @patch("download_uup.Path.mkdir")
    @patch("download_uup.Path.glob")
    @patch("builtins.input")
    @patch("download_uup.log_info")
    def test_prepare_output_directory_clears(
        self, mock_log_info, mock_input, mock_glob, mock_mkdir
    ):
        from pathlib import Path

        mock_input.return_value = "y"
        mock_file = unittest.mock.MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.name = "old_file.txt"
        mock_glob.return_value = [mock_file]

        download_uup._prepare_output_directory(Path("test_out"))

        mock_mkdir.assert_called_with(parents=True, exist_ok=True)
        mock_file.unlink.assert_called_once()
        mock_log_info.assert_called_with("Clearing existing files...")

    def test_prepare_download_list(self):
        files = {
            "test1.esd": {"size": 100},
            "test2.esd": {"size": 200},
            "other.txt": {"size": 50},
        }
        edition_filter = ["test1.esd"]

        # Test with filter: should include test1.esd (matched filter) and other.txt (not .esd)
        dl_list = download_uup._prepare_download_list("build123", files, edition_filter)
        self.assertEqual(len(dl_list), 2)
        names = [item["name"] for item in dl_list]
        self.assertIn("test1.esd", names)
        self.assertIn("other.txt", names)
        self.assertNotIn("test2.esd", names)

        # Test without filter
        dl_list = download_uup._prepare_download_list("build123", files, None)
        self.assertEqual(len(dl_list), 3)

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("subprocess.run")
    @patch("download_uup.Path.unlink")
    @patch("download_uup.Path.glob")
    @patch("download_uup.log_success")
    @patch("download_uup.log_info")
    def test_run_aria2_download_success(
        self,
        mock_log_info,
        mock_log_success,
        mock_glob,
        mock_unlink,
        mock_run,
        mock_open,
    ):
        from pathlib import Path

        dl_list = [{"url": "http://test", "name": "test.esd"}]
        mock_glob.return_value = [Path("test.esd")]

        result = download_uup._run_aria2_download(
            Path("out"), Path("in.txt"), dl_list
        )

        self.assertTrue(result)
        mock_run.assert_called_once()
        mock_unlink.assert_called_once()
        mock_log_success.assert_called()



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
        mock_fetch_url.return_value = 'Not a JSON string'

        result = download_uup.get_latest_builds()

        self.assertIsNone(result)
        # Since the error message includes the exception string, we just check that it starts correctly
        mock_log_error.assert_called_once()
        self.assertTrue(mock_log_error.call_args[0][0].startswith("Failed to parse JSON response:"))

if __name__ == "__main__":
    unittest.main()
