import hashlib
import io
import re
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sign_iso
import validate_debloat
import validate_reg_files
import validate_xml


class TestWriteChecksum(unittest.TestCase):
    def test_writes_digest_and_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp) / "Win11.iso"
            iso.write_bytes(b"iso-bytes")
            sign_iso.write_checksum(iso, "sha256")
            expected = hashlib.sha256(b"iso-bytes").hexdigest()
            self.assertEqual(
                (Path(tmp) / "Win11.iso.sha256").read_text(),
                f"{expected}  Win11.iso\n",
            )


class TestRegChecks(unittest.TestCase):
    def test_decode_handles_utf16_bom_and_utf8(self):
        text = validate_reg_files.REG_HEADER
        self.assertEqual(
            validate_reg_files.decode_reg_bytes(b"\xff\xfe" + text.encode("utf-16-le")),
            text,
        )
        self.assertEqual(validate_reg_files.decode_reg_bytes(text.encode()), text)

    def test_header_check(self):
        errors: list[str] = []
        validate_reg_files.check_header("ok", validate_reg_files.REG_HEADER, errors)
        self.assertEqual(errors, [])
        validate_reg_files.check_header("bad", "[HKEY_LOCAL_MACHINE\\x]", errors)
        validate_reg_files.check_header("empty", "", errors)
        self.assertEqual(len(errors), 2)

    def test_scan_safety_flags_disabled_uac(self):
        notes: list[str] = []
        validate_reg_files.scan_safety("f", '"EnableLUA"=dword:00000000', notes)
        self.assertEqual(len(notes), 1)
        self.assertIn("UAC", notes[0])


class TestXmlChecks(unittest.TestCase):
    def test_bom_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml = Path(tmp) / "a.xml"
            xml.write_bytes(validate_xml.BOM + b"<a/>")
            errors: list[str] = []
            validate_xml.check_no_bom(xml, errors)
            self.assertEqual(len(errors), 1)

    def test_malformed_xml_is_reported_without_xmllint(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml = Path(tmp) / "a.xml"
            xml.write_text("<a>", encoding="utf-8")
            errors: list[str] = []
            validate_xml.check_well_formed(xml, False, errors)
            self.assertEqual(len(errors), 1)


class TestCheckRawLines(unittest.TestCase):
    def _run(self, content: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "debloat_list.txt"
            config.write_text(content, encoding="utf-8")
            with mock.patch.object(validate_debloat, "CONFIG_FILE", config):
                return validate_debloat.check_raw_lines()

    def test_clean_file_has_no_errors(self):
        self.assertEqual(self._run("# Games\n*Xbox*\n\n"), 0)

    def test_invalid_and_protected_lines_are_counted(self):
        self.assertEqual(self._run("*Xbox*\nbad pattern!\n*Store*\n"), 2)


class TestLoggingHasOneHome(unittest.TestCase):
    def test_logging_modules_support_redirected_stdout(self) -> None:
        class RedirectedStream:
            encoding = "cp1252"

        for module in ("pyutils.py", "win_utils.py"):
            with (
                self.subTest(module=module),
                mock.patch.object(sys, "stdout", RedirectedStream()),
            ):
                runpy.run_path(str(SCRIPTS / module))

    def test_logging_modules_reconfigure_text_stdout(self) -> None:
        for module in ("pyutils.py", "win_utils.py"):
            with (
                self.subTest(module=module),
                io.TextIOWrapper(io.BytesIO(), encoding="cp1252") as stream,
            ):
                with mock.patch.object(sys, "stdout", stream):
                    runpy.run_path(str(SCRIPTS / module))
                self.assertEqual(stream.encoding, "utf-8")
                self.assertEqual(stream.errors, "replace")

    def test_no_script_redefines_pyutils_log_helpers(self):
        for script in SCRIPTS.glob("*.py"):
            if script.name == "pyutils.py":
                continue
            text = script.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(
                    r"^def log_(info|success|warn|error|debug)\(", text, re.MULTILINE
                ),
                script.name,
            )


if __name__ == "__main__":
    unittest.main()
