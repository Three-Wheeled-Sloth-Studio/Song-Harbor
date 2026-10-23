"""Managed ACE service safety tests, no ACE installation or GPU needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ace_service import AceServiceManager, AceServiceError


class ManagedAceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "ace"
        (self.root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")).mkdir(parents=True)
        (self.root / "acestep").mkdir()
        executable = self.root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        executable.write_bytes(b"mock executable")
        (self.root / "acestep" / "api_server.py").write_text("pass")
        self.client = MagicMock()
        self.client.discover.return_value = {"status": "stopped_or_unavailable"}
        self.manager = AceServiceManager(self.root, client=self.client,
                                         log_directory=Path(self.tmp.name) / "logs")
        self.addCleanup(self.manager.cleanup)

    def test_installed_but_stopped(self):
        value = self.manager.status()
        self.assertEqual(value["state"], "installed_stopped")
        self.assertTrue(value["can_start"])
        self.assertFalse(value["can_stop"])

    def test_start_hidden_exact_pid_then_stop(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 1234
        with patch("ace_service.subprocess.Popen", return_value=proc) as launch:
            status = self.manager.start()
            self.assertTrue(status["owned"])
            args = launch.call_args.args[0]
            self.assertEqual(args[-5:], ["--host", "127.0.0.1", "--port", "8001", "--no-init"])
            self.assertFalse(launch.call_args.kwargs["shell"])
            self.assertEqual(launch.call_args.kwargs["env"]["ACESTEP_ON_DEMAND_MODEL_LOAD"], "false")
            self.assertEqual(launch.call_args.kwargs["env"]["ACESTEP_NO_INIT"], "true")
        self.assertTrue(self.manager.stop()["can_start"])
        proc.terminate.assert_called_once()
        proc.wait.assert_called()

    def test_never_stop_external_ace(self):
        self.client.discover.return_value = {"status": "connected", "ready": False}
        self.assertFalse(self.manager.start()["owned"])
        with self.assertRaises(AceServiceError):
            self.manager.stop()

    def test_nonexistent_install_cannot_start(self):
        self.root.joinpath("acestep", "api_server.py").unlink()
        with self.assertRaises(AceServiceError):
            self.manager.start()

    def test_never_initialize_noninstalled_model(self):
        self.client.discover.return_value = {"status": "connected", "ready": False}
        with self.assertRaises(AceServiceError):
            self.manager.initialize_model("acestep-v15-base")
        self.client.request.assert_not_called()

    def test_guard_initialization_before_calling_ace(self):
        self.client.discover.return_value = {"status": "connected", "ready": False}
        with self.assertRaises(AceServiceError):
            self.manager.initialize_model("acestep-v15-turbo")
        self.client.request.assert_not_called()

    def test_verified_model_initialization(self):
        checkpoint = self.root / "checkpoints" / "acestep-v15-turbo"
        checkpoint.mkdir(parents=True)
        (checkpoint / "config.json").write_text(json.dumps({"is_turbo": True}))
        self.client.discover.side_effect = [
            {"status": "connected", "ready": False},
            {"status": "connected", "ready": True, "loaded_model": "acestep-v15-turbo"},
            {"status": "connected", "ready": True, "loaded_model": "acestep-v15-turbo"},
        ]
        self.client.request.side_effect = [
            {"code": 200, "data": {"models": [{"name": "acestep-v15-turbo"}]}},
            {"code": 200, "data": {"status": "initialized"}},
        ]
        status = self.manager.initialize_model("acestep-v15-turbo")
        self.assertEqual(status["state"], "running_ready")
        self.assertEqual(self.client.request.call_args_list[1].args[0], "/v1/init")


if __name__ == "__main__":
    unittest.main()
