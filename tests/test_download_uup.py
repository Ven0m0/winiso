import sys
import unittest
from pathlib import Path

# Add the scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from download_uup import parse_args


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


if __name__ == "__main__":
    unittest.main()
import os
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
download_uup_path = scripts_dir / "download_uup.py"
_loader = SourceFileLoader("download_uup", str(download_uup_path))
_spec = spec_from_loader("download_uup", _loader)
download_uup = module_from_spec(_spec)
_loader.exec_module(download_uup)
parse_args = download_uup.parse_args
