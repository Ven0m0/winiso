import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import apply_image_settings
import debloat_wim


class TestGetAppxPatterns(unittest.TestCase):
    def test_matches_debloat_list_minus_protected(self):
        expected = tuple(
            p
            for p in debloat_wim.load_patterns()
            if not debloat_wim.is_protected_pattern(p)
        )
        self.assertEqual(apply_image_settings.get_appx_patterns(), expected)
        self.assertGreater(len(expected), 0)

    def test_no_pattern_is_protected(self):
        for pattern in apply_image_settings.get_appx_patterns():
            self.assertFalse(debloat_wim.is_protected_pattern(pattern), pattern)


if __name__ == "__main__":
    unittest.main()
