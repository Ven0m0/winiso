import sys
import unittest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download_uup


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.script_dir = Path(download_uup.__file__).parent
        self.project_root = self.script_dir.parent.resolve()

    def test_path_traversal_prevention(self):
        """Test that path traversal is correctly prevented."""

        with patch("download_uup.parse_args") as mock_parse_args, patch(
            "download_uup.check_dependencies", return_value=True
        ), patch("download_uup.log_error") as mock_log_error:

            # Case 1: Normal relative path (Safe)
            mock_parse_args.return_value = MagicMock(
                output="uup_files", list=False, build_id=None
            )
            with patch("download_uup.interactive_mode", return_value=True):
                self.assertEqual(download_uup.main(), 0)
                mock_log_error.assert_not_called()

            # Case 2: Absolute path inside project (Safe)
            safe_abs_path = str(self.project_root / "custom_output")
            mock_parse_args.return_value = MagicMock(
                output=safe_abs_path, list=False, build_id=None
            )
            with patch("download_uup.interactive_mode", return_value=True):
                self.assertEqual(download_uup.main(), 0)
                mock_log_error.assert_not_called()

            # Case 3: Path traversal attempt (Unsafe)
            unsafe_path = "../../../etc/passwd"
            mock_parse_args.return_value = MagicMock(
                output=unsafe_path, list=False, build_id=None
            )
            self.assertEqual(download_uup.main(), 1)
            mock_log_error.assert_called_with(
                f"Path traversal attempt detected for output: {unsafe_path}"
            )
            mock_log_error.reset_mock()

            # Case 4: Exploiting the startswith vulnerability (Now FIXED)
            malicious_path_str = str(self.project_root) + "_malicious"

            with patch("pathlib.Path.resolve") as mock_resolve:
                # Order in main():
                # 1. output_dir.resolve()
                # 2. project_root.resolve()
                # 3. output_dir.resolve() (called again in the relative_to check)

                # NOTE: In the fixed version, output_dir.resolve() is called twice if it passes the first check.
                # Actually, in the fixed version:
                # 1. output_dir.resolve().relative_to(...)
                #    Inside this, resolve() is called.
                #    And project_root.resolve() is called.

                mock_resolve.side_effect = [Path(malicious_path_str), self.project_root]

                mock_parse_args.return_value = MagicMock(
                    output="uup_files_malicious", list=False, build_id=None
                )

                result = download_uup.main()
                # Now it SHOULD return 1 because Path("/app/project_malicious").relative_to("/app/project") raises ValueError
                self.assertEqual(
                    result,
                    1,
                    "Security fix failed: path outside root was still accepted!",
                )
                mock_log_error.assert_called_with(
                    f"Path traversal attempt detected for output: uup_files_malicious"
                )
                print(
                    "\nSECURITY TEST: Fix verified! Path outside root was correctly rejected."
                )


if __name__ == "__main__":
    unittest.main()
