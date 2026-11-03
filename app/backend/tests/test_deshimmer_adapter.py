"""Deshimmer handshake is explicitly independent of sound processing."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deshimmer_adapter as adapter


class HandshakeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.python = Path(self.folder.name) / "python.exe"
        self.python.write_bytes(b"test")

    def test_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(adapter.DeshimmerUnavailable, "Configure"):
                adapter.probe()

    def test_missing_executable(self):
        with self.assertRaisesRegex(adapter.DeshimmerUnavailable, "does not exist"):
            adapter.probe(str(self.python.parent / "missing.exe"))

    def test_api_handshake(self):
        result = {"available": True, "module": "C:/deshimmer/api.py", "python": "3.11.9"}
        def invoke(command, **kwargs):
            self.assertEqual(command[0], str(self.python))
            self.assertEqual(command[1], "-c")
            self.assertFalse(kwargs["shell"])
            return type("Result", (), {"returncode": 0, "stdout": json.dumps(result), "stderr": ""})()
        with patch.object(adapter.subprocess, "run", side_effect=invoke):
            found = adapter.probe(str(self.python))
        self.assertTrue(found["available"])
        self.assertEqual(found["module"], result["module"])

    def test_missing_api(self):
        with patch.object(adapter.subprocess, "run", return_value=type(
                "Result", (), {"returncode": 0,
                               "stdout": '{"available": false, "module": "x"}',
                               "stderr": ""})()):
            with self.assertRaisesRegex(adapter.DeshimmerUnavailable, "not callable"):
                adapter.probe(str(self.python))


if __name__ == "__main__":
    unittest.main()
