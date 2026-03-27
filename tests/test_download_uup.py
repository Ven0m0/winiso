import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add scripts directory to sys.path to import download_uup
sys.path.append(os.path.abspath("scripts"))
import download_uup

class TestDownloadUUP(unittest.TestCase):
    @patch('download_uup.get_build_info')
    @patch('download_uup.subprocess.run')
    def test_path_traversal_sanitization(self, mock_run, mock_get_build_info):
        # Mock build info with malicious filenames
        mock_build_info = {
            "files": {
                "../../../etc/passwd": {"size": 1024},
                "..\\..\\Windows\\System32\\cmd.exe": {"size": 2048},
                "/absolute/path/file.esd": {"size": 4096},
                "normal_file.cab": {"size": 8192}
            }
        }
        mock_get_build_info.return_value = mock_build_info

        # We need to mock open to inspect what gets written to aria2_input.txt
        m_open = mock_open()

        # Mock Path methods to avoid actual file system operations like mkdir
        with patch('download_uup.Path.mkdir'):
            with patch('download_uup.Path.glob', return_value=[]):
                with patch('builtins.open', m_open):
                    with patch('download_uup.Path.unlink'): # Mock unlink to prevent FileNotFoundError
                        # Mock successful aria2c execution
                        mock_run.return_value = MagicMock(returncode=0)

                        # Run the download
                        result = download_uup.download_build(
                            "dummy_build_id",
                            "dummy_output_dir",
                            build_info=mock_build_info
                        )

        self.assertTrue(result)

        # Verify what was written to the file
        written_lines = []
        for call in m_open().write.mock_calls:
            args, kwargs = call[1], call[2]
            if args:
                written_lines.append(args[0])

        # Check that out= parameters are sanitized
        out_lines = [line.strip() for line in written_lines if line.strip().startswith('out=')]

        self.assertEqual(len(out_lines), 4)
        self.assertIn('out=passwd', out_lines)
        self.assertIn('out=cmd.exe', out_lines)
        self.assertIn('out=file.esd', out_lines)
        self.assertIn('out=normal_file.cab', out_lines)

        # Ensure no path traversal elements are present
        for line in out_lines:
            self.assertNotIn('../', line)
            self.assertNotIn('..\\', line)
            self.assertNotIn('/', line.replace('out=', ''))
            self.assertNotIn('\\', line.replace('out=', ''))

if __name__ == '__main__':
    unittest.main()
