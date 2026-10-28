import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download_uup
import uup_delta


class TestPromptSeam(unittest.TestCase):
    def test_existing_files_cleared_when_ask_says_yes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "a.cab").write_text("x")
            download_uup._prepare_output_directory(out, ask=lambda _: "y")
            self.assertFalse((out / "a.cab").exists())

    def test_existing_files_kept_when_ask_says_no(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "a.cab").write_text("x")
            download_uup._prepare_output_directory(out, ask=lambda _: "n")
            self.assertTrue((out / "a.cab").exists())

    def test_declined_confirmation_never_downloads(self):
        build_info = {"files": {"x.cab": {"size": 1}}}
        with (
            mock.patch.object(
                download_uup, "get_build_info_cached", return_value=build_info
            ),
            mock.patch.object(download_uup, "download_build") as download,
        ):
            ok = download_uup._process_selected_build(
                {"id": "b1", "title": "t"}, "out", ask=lambda _: "n"
            )
        self.assertFalse(ok)
        download.assert_not_called()

    def test_accepted_confirmation_forwards_ask_to_download(self):
        build_info = {"files": {"x.cab": {"size": 1}}}
        ask = lambda _: "y"
        with (
            mock.patch.object(
                download_uup, "get_build_info_cached", return_value=build_info
            ),
            mock.patch.object(
                download_uup, "download_build", return_value=True
            ) as download,
        ):
            ok = download_uup._process_selected_build(
                {"id": "b1", "title": "t"}, "out", ask=ask
            )
        self.assertTrue(ok)
        self.assertIs(download.call_args.kwargs["ask"], ask)


class TestIsWithin(unittest.TestCase):
    def test_inside_and_equal(self):
        root = Path.cwd()
        self.assertTrue(download_uup._is_within(root / "a" / "b", root))
        self.assertTrue(download_uup._is_within(root, root))

    def test_dotdot_escape_is_rejected(self):
        root = Path.cwd()
        self.assertFalse(download_uup._is_within(root / ".." / "elsewhere", root))


class TestUupDelta(unittest.TestCase):
    def test_save_load_round_trip_and_delta(self):
        old = {"a.esd": {"size": 1}, "b.esd": {"size": 2}}
        new = {"a.esd": {"size": 1}, "b.esd": {"size": 3}, "c.esd": {"size": 4}}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNotNone(uup_delta.save_delta_manifest("b1", old, tmp))
            loaded = uup_delta.load_delta_manifest("b1", tmp)
        self.assertEqual(loaded, old)
        assert loaded is not None
        delta = uup_delta.calculate_delta(loaded, new)
        self.assertEqual(delta["added"], ["c.esd"])
        self.assertEqual(delta["modified"], ["b.esd"])
        self.assertEqual(delta["unchanged"], ["a.esd"])

    def test_traversal_build_id_stays_inside_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = uup_delta.save_delta_manifest("../../evil", {}, tmp)
            self.assertIsNotNone(path)
            assert path is not None
            self.assertEqual(path.parent.resolve(), Path(tmp).resolve())


if __name__ == "__main__":
    unittest.main()
