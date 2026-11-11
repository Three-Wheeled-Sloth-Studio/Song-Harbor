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
            self.assertEqual(logfile, root / "logs" / "moss-wsl.log")
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

    def test_timeout_attempts_cleanup_before_failed_status(self):
        process = Mock()
        process.poll.return_value = None
        with patch.dict(moss_runtime._ACTIVE, {
            "process": process, "id": "model", "started_at": 1.0,
            "model_name": "songharbor-moss-model", "kind": "wsl",
            "log": None, "error": "", "ready_at": None
        }), patch.object(moss_runtime, "_probe", return_value=False), \
             patch.object(moss_runtime, "_stop_process") as stop, \
             patch.object(moss_runtime.time, "time", return_value=1000):
            result = moss_runtime.status()
            self.assertEqual(result["status"], "failed")
            self.assertIn("15 minutes", result["error"])
            stop.assert_called_once_with(process)

    def test_startup_reports_elapsed_and_real_phase(self):
        process = Mock()
        process.poll.return_value = None
        with patch.dict(moss_runtime._ACTIVE, {
            "process": process, "id": "model", "started_at": 100.0,
            "model_name": "songharbor-moss-model", "kind": "wsl",
            "log": None, "error": "", "ready_at": None
        }), patch.object(moss_runtime, "_probe", return_value=False), \
             patch.object(moss_runtime.time, "time", return_value=150), \
             patch.object(moss_runtime, "_startup_phase", return_value="Initializing runtime"):
            result = moss_runtime.status()
            self.assertEqual(result["status"], "starting")
            self.assertEqual(result["elapsed_seconds"], 50)
            self.assertEqual(result["startup_timeout_seconds"], 900)
            self.assertEqual(result["phase"], "Initializing runtime")

    def test_refuses_oversized_weights_before_starting_wsl(self):
        from unittest.mock import patch as mock_patch
        with mock_patch.object(moss_runtime.model_registry, "list_models", return_value={
            "registered": [{"id": "big", "status": "present-unverified",
                            "bytes_present": 17 * 1024**3, "path": "/tmp/big"}]
        }), mock_patch.object(moss_runtime.wsl_model_bridge, "libnuma_status",
                              return_value={"ready": True}), \
             mock_patch.object(moss_runtime.wsl_model_bridge, "gpu_memory",
                               return_value={"verified": True, "total_mib": 12288, "free_mib": 12288}), \
             mock_patch.object(moss_runtime.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "Checkpoint weights alone"):
                moss_runtime.load_wsl(Path("/tmp"), Path("/tmp"), "big", "Ubuntu", "/bin/python", True)
            spawn.assert_not_called()

    def test_orphan_recovery_never_runs_without_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(moss_runtime.subprocess, "run") as execute:
                with self.assertRaisesRegex(ValueError, "Approve"):
                    moss_runtime.release_orphan(Path(tmp), False)
                execute.assert_not_called()

    def test_idle_release_is_not_extended_by_status_poll(self):
        process = Mock()
        process.poll.return_value = None
        with patch.dict(moss_runtime._ACTIVE, {
            "process": process, "id": "model", "started_at": 1.0,
            "model_name": "songharbor-moss-model", "kind": "wsl",
            "log": None, "error": "", "ready_at": 2.0, "last_used": 2.0
        }), patch.object(moss_runtime, "_probe", return_value=True), \
             patch.object(moss_runtime.time, "time", return_value=2000), \
             patch.object(moss_runtime.time, "monotonic", return_value=100):
            self.assertEqual(moss_runtime.status()["status"], "ready")
            self.assertEqual(moss_runtime._ACTIVE["last_used"], 2.0)

    def test_diagnostics_are_read_only_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "moss-wsl.log"
            path.write_text("first\n" + "x" * 10000 + "\nlast")
            self.assertLessEqual(len(moss_runtime._tail(path, 5000)), 5000)
            self.assertTrue(path.read_text().endswith("last"))


if __name__ == "__main__":
    unittest.main()
