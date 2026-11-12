"""Shared model configuration safety checks. No model inference or downloads."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shared_model_settings
import workspace_settings


class SharedModelSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "runtime"
        self.root.mkdir()
        self.target = Path(self.tmp.name) / "models-external"

    def test_save_is_non_destructive_and_preserves_settings(self):
        original = self.root / "data" / "track.wav"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"approved")
        cfg = workspace_settings.settings_path(self.root)
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"ffmpeg": {"bin_directory": "D:/ffmpeg"}}))
        shared_model_settings.save(self.root, str(self.target))
        self.assertEqual(original.read_bytes(), b"approved")
        self.assertFalse(self.target.exists())
        self.assertEqual(shared_model_settings.configured_root(self.root), self.target.resolve())
        self.assertEqual(workspace_settings.read(self.root)["ffmpeg"]["bin_directory"], "D:/ffmpeg")

    def test_rejects_unsafe_locations_without_writing(self):
        for value in ["relative", str(self.root), str(self.root / "data"), str(self.root / "models"), str(Path.home()), str(Path(self.root.anchor))]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    shared_model_settings.save(self.root, value)
        self.assertFalse(workspace_settings.settings_path(self.root).exists())

    def test_status_does_not_claim_loaded_or_download(self):
        status = shared_model_settings.status(self.root, self.root / "models")
        self.assertFalse(status["downloads_enabled"])
        self.assertFalse(status["models_loaded"])
        self.assertFalse(status["restart_required"])

    def test_runtime_python_setting_preserves_other_preferences(self):
        candidate = Path(sys.executable)
        if candidate.name.lower() not in ("python", "python.exe", "python3.exe"):
            self.skipTest("Test runner does not use a standard Python executable")
        config = workspace_settings.settings_path(self.root)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({"working_files_directory": str(self.target)}))
        saved = shared_model_settings.save_runtime_python(self.root, str(candidate))
        self.assertEqual(saved, shared_model_settings.configured_runtime_python(self.root))
        self.assertEqual(str(self.target), workspace_settings.read(self.root)["working_files_directory"])

    def test_missing_runtime_python_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Runtime not saved"):
            shared_model_settings.save_runtime_python(self.root, str(self.target / "python.exe"))
        self.assertEqual("", shared_model_settings.configured_runtime_python(self.root))


if __name__ == "__main__":
    unittest.main()
