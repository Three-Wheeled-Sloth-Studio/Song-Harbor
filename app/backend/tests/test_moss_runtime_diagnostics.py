"""MOSS loader failure diagnostics are truthful and bounded."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import moss_runtime


class MossRuntimeDiagnosticsTests(unittest.TestCase):
    def test_wsl_error_reports_correct_path_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logfile = moss_runtime._runtime_log(root, "wsl")
            logfile.parent.mkdir(parents=True)
            logfile.write_text("Loading model\nRuntimeError: CUDA out of memory\n")
            proc = Mock()
            proc.poll.return_value = 1
            with patch.dict(moss_runtime._ACTIVE, {"process": proc, "id": "test",
                    "error": "", "log": logfile.open("ab"), "kind": "wsl"}, clear=False):
                with patch.object(moss_runtime, "_LOG_PATH", logfile):
                    result = moss_runtime.status()
                    self.assertEqual(result["status"], "failed")
                    self.assertIn(str(logfile), result["error"])
                    self.assertIn("CUDA out of memory", result["error"])
                    self.assertEqual(moss_runtime.status()["status"], "failed")
                    self.assertIn("CUDA out of memory", moss_runtime.diagnostics()["log_tail"])

    def test_diagnostics_are_read_only_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "moss-wsl.log"
            path.write_text("first\n" + "x" * 10000 + "\nlast")
            self.assertLessEqual(len(moss_runtime._tail(path, 5000)), 5000)
            self.assertTrue(path.read_text().endswith("last"))


if __name__ == "__main__":
    unittest.main()
