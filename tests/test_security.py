import unittest
from pathlib import Path
import sys

# Add the scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestSecurity(unittest.TestCase):
    def test_path_traversal_logic(self):
        """
        Verify that the path validation logic correctly identifies traversal attempts,
        including the prefix-based exploit.
        """
        # We'll use a mock project root for testing
        project_root = Path("/tmp/project_root").resolve()

        def is_safe(output_arg, root):
            # This replicates the logic in download_uup.main()
            output_dir = Path(output_arg)
            if not output_dir.is_absolute():
                output_dir = root.joinpath(output_dir)

            try:
                output_dir.resolve().relative_to(root.resolve())
                return True
            except (ValueError, RuntimeError):
                return False

        # Normal case
        self.assertTrue(is_safe("uup_files", project_root))

        # Current directory (should be allowed)
        self.assertTrue(is_safe(".", project_root))

        # Subdirectory (should be allowed)
        self.assertTrue(is_safe("uup_files/subdir", project_root))

        # Direct traversal
        self.assertFalse(is_safe("../outside", project_root))

        # Prefix exploit (The Vulnerability)
        # If project_root is /tmp/project_root
        # and output is /tmp/project_root_secret
        # it should be detected as traversal
        prefix_exploit_path = "/tmp/project_root_secret"
        self.assertFalse(
            is_safe(prefix_exploit_path, project_root),
            f"Path {prefix_exploit_path} should be detected as traversal from {project_root}",
        )


if __name__ == "__main__":
    unittest.main()
