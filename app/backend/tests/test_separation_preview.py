from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import separation_preview


class SpecialistSeparationTests(unittest.TestCase):
    def test_models_are_local_bounded_and_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "htdemucs_6s.yaml").write_text("a")
            (root / "voice.onnx").write_bytes(b"weights")
            (root / "bad.exe").write_bytes(b"no")
            found = separation_preview.available_models(root)
            self.assertEqual([m["id"] for m in found], ["htdemucs_6s.yaml", "voice.onnx"])
            self.assertTrue(all(m["installed"] for m in found))

    def test_unknown_model_refused_before_starting_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "model").mkdir()
            (root / "separator.exe").write_bytes(b"exe")
            project = {"id": "abcdef123456"}
            with patch.object(separation_preview, "_validated_source", return_value=(root / "source.wav", {"start_seconds": 0, "duration_seconds": 30})):
                with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                    separation_preview.submit(root, project, "trk", 0, 20, "../foreign.onnx",
                                              root / "model", "ffmpeg", str(root / "separator.exe"))

    def test_region_restrictions_precede_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "0.5 to 60"):
                separation_preview.submit(root, {"id": "abcdef123456"}, "trk", 0, 120,
                                          "model.onnx", root, "ffmpeg", "separator")
            self.assertFalse((root / "jobs").exists())

    def test_audio_lookup_requires_completed_owned_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = {"id": "a", "project_id": "abcdef123456", "status": "complete",
                     "files": ["voice.wav"], "folder": str(root)}
            (root / "voice.wav").write_bytes(b"wav")
            with patch.dict(separation_preview._JOBS, {"a": entry}, clear=True):
                self.assertEqual(separation_preview.audio_path("abcdef123456", "a", "voice.wav"), root / "voice.wav")
                with self.assertRaisesRegex(ValueError, "Unknown candidate"):
                    separation_preview.audio_path("abcdef123456", "a", "../voice.wav")
                with self.assertRaisesRegex(ValueError, "not ready"):
                    separation_preview.audio_path("other", "a", "voice.wav")


if __name__ == "__main__":
    unittest.main()
