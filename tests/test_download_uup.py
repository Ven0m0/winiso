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
