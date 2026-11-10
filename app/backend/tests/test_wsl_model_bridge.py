"""WSL discovery and explicit installer safety checks (no actual WSL execution)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wsl_model_bridge as bridge
import wsl_model_install as installer


class WslModelBridgeTests(unittest.TestCase):
    def test_utf16_distro_discovery(self):
        output = "Ubuntu\r\nUbuntu-24.04\r\n".encode("utf-16-le")
        with patch.object(bridge.os, "name", "nt"), patch.object(bridge.shutil, "which", return_value="C:/Windows/System32/wsl.exe"), patch.object(bridge.subprocess, "run", return_value=Mock(stdout=output, returncode=0)):
            result = bridge.distros()
        self.assertTrue(result["available"])
        self.assertEqual(result["distros"], ["Ubuntu", "Ubuntu-24.04"])

    def test_no_wsl_does_not_install(self):
        with patch.object(bridge.os, "name", "posix"):
            self.assertFalse(bridge.distros()["available"])

    def test_rejects_unrecognized_distro(self):
        with patch.object(bridge, "distros", return_value={"distros": ["Ubuntu"], "available": True}):
            with self.assertRaisesRegex(ValueError, "not found"):
                bridge.validate_distro("Other")

    def test_python_preflight_requires_linux_path(self):
        with patch.object(bridge, "validate_distro", return_value="Ubuntu"):
            with self.assertRaisesRegex(ValueError, "absolute Linux"):
                bridge.preflight("Ubuntu", "C:/python.exe")

    def test_install_requires_approval_before_any_process(self):
        with patch.object(installer.subprocess, "Popen") as process:
            with self.assertRaisesRegex(ValueError, "Approve"):
                installer.install(Path("/tmp/shared-models"), "Ubuntu", "D:\\WSL\\NewUbuntu", False)
            process.assert_not_called()

    def test_installer_rejects_system_drive_and_root(self):
        for bad in ["C:\\WSL\\Ubuntu", "D:\\", "relative"]:
            with self.subTest(path=bad), self.assertRaises(ValueError):
                installer._destination(bad)


if __name__ == "__main__":
    unittest.main()
