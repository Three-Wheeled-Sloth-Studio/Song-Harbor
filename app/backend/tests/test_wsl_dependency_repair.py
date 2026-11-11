"""Safety and path tests for opt-in Ubuntu libnuma1 repair."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_logs
import wsl_model_bridge
import wsl_dependency_repair


class DependencyRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        wsl_dependency_repair._JOB.update({
            "process": None, "log": None, "state": "idle", "distro": None, "error": ""
        })

    def test_app_logs_are_near_root_and_named_allowlist(self):
        self.assertEqual(app_logs.log_path(self.root, "moss-wsl.log"), self.root / "logs" / "moss-wsl.log")
        with self.assertRaises(ValueError):
            app_logs.log_path(self.root, "../data/track.wav")

    def test_probe_recognizes_only_missing_libnuma(self):
        with patch.object(wsl_model_bridge, "validate_distro", return_value="Ubuntu"), \
             patch.object(wsl_model_bridge, "_run", return_value=Mock(returncode=1, stdout="",
                 stderr="OSError: libnuma.so.1: cannot open shared object file: No such file or directory")):
            result = wsl_model_bridge.libnuma_status("Ubuntu")
            self.assertEqual(result["missing_package"], "libnuma1")
            self.assertFalse(result["ready"])
        with patch.object(wsl_model_bridge, "validate_distro", return_value="Ubuntu"), \
             patch.object(wsl_model_bridge, "_run", return_value=Mock(returncode=1, stdout="",
                 stderr="python3: command not found")):
            result = wsl_model_bridge.libnuma_status("Ubuntu")
            self.assertIsNone(result["missing_package"])

    def test_never_installs_without_approval(self):
        with patch.object(wsl_dependency_repair.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "Approval"):
                wsl_dependency_repair.start(self.root, "Ubuntu", False)
            spawn.assert_not_called()

    def test_only_known_missing_library_allows_repair(self):
        with patch.object(wsl_dependency_repair.wsl_model_bridge, "validate_distro"), \
             patch.object(wsl_dependency_repair.wsl_model_bridge, "libnuma_status",
                          return_value={"ready": False, "missing_package": None}):
            with patch.object(wsl_dependency_repair.subprocess, "Popen") as spawn:
                with self.assertRaisesRegex(ValueError, "not confirmed"):
                    wsl_dependency_repair.start(self.root, "Ubuntu", True)
                spawn.assert_not_called()

    def test_explicit_repair_uses_fixed_package_command_and_central_log(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(wsl_dependency_repair.wsl_model_bridge, "validate_distro"), \
             patch.object(wsl_dependency_repair.wsl_model_bridge, "libnuma_status",
                          return_value={"ready": False, "missing_package": "libnuma1"}), \
             patch.object(wsl_dependency_repair.subprocess, "Popen", return_value=process) as spawn:
            state = wsl_dependency_repair.start(self.root, "Ubuntu", True)
            self.assertEqual(state["state"], "running")
            self.assertEqual(spawn.call_args.args[0], [
                "wsl.exe", "-d", "Ubuntu", "-u", "root", "--exec",
                "/usr/bin/apt-get", "install", "-y", "libnuma1"
            ])
            self.assertTrue((self.root / "logs" / "moss-repair.log").is_file())
        handle = wsl_dependency_repair._JOB["log"]
        if handle:
            handle.close()
        wsl_dependency_repair._JOB["process"] = None


if __name__ == "__main__":
    unittest.main()
