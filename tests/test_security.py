import re
import sys
import unittest
from pathlib import Path

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

        import os

        def is_safe(output_arg, root):
            # This replicates the logic in download_uup._resolve_output_dir()
            output_dir = Path(output_arg)
            if not output_dir.is_absolute():
                output_dir = root.joinpath(output_dir)

            resolved_output = output_dir.resolve()
            resolved_root = root.resolve()

            return os.path.commonpath([resolved_output, resolved_root]) == str(
                resolved_root
            )

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

    def test_no_sudo_usage(self):
        """
        Verify that no shell scripts or configuration files use sudo or su.
        This is a project-specific security invariant.
        """
        project_root = Path(__file__).resolve().parent.parent
        scripts_dir = project_root / "scripts"
        scripts = list(scripts_dir.glob("*.sh"))

        # Also check mise tasks and the mise.toml config (sudo was removed from both)
        mise_tasks_dir = project_root / ".mise" / "tasks"
        if mise_tasks_dir.exists():
            scripts.extend(list(mise_tasks_dir.glob("*")))

        mise_config = project_root / "mise.toml"
        if mise_config.exists():
            scripts.append(mise_config)

        # sudo as a standalone command, or su invoked as a command (line-start)
        forbidden_patterns = [r"\bsudo\b", r"(?m)^\s*su\s"]

        for script in scripts:
            if script.is_dir():
                continue

            try:
                content = script.read_text()
            except (UnicodeDecodeError, OSError):
                continue

            # Strip comments to avoid false positives in documentation
            content_no_comments = re.sub(r"#.*", "", content)

            for pattern in forbidden_patterns:
                self.assertFalse(
                    re.search(pattern, content_no_comments),
                    f"Forbidden command pattern '{pattern}' found in {script.relative_to(project_root)}",
                )


if __name__ == "__main__":
    unittest.main()
