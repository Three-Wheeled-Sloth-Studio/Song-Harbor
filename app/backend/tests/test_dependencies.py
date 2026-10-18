"""FFmpeg configuration/recovery tests without downloading or executing software."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dependencies


class DependencyRecoveryTests(unittest.TestCase):
    def test_missing_config_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual({}, dependencies.load_config(Path(d)))

    def test_saves_selected_location_atomically(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "tools" / "ffmpeg" / "bin"
            folder.mkdir(parents=True)
            for binary in ("ffmpeg.exe", "ffprobe.exe"):
                (folder / binary).write_bytes(b"test")
            completed = type("Result", (), {"returncode": 0, "stdout": "ffmpeg version 7.0"})()
            with patch.object(dependencies.subprocess, "run", return_value=completed):
                result = dependencies.save_binary(root, folder)
            self.assertEqual(folder.resolve(), result["directory"])
            saved = json.loads((root / "config" / "settings.json").read_text())
            self.assertEqual(str(folder.resolve()), saved["ffmpeg"]["bin_directory"])

    def test_rejects_missing_ffprobe(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "tools"
            folder.mkdir()
            (folder / "ffmpeg.exe").write_bytes(b"test")
            with self.assertRaises(ValueError):
                dependencies.save_binary(root, folder)

    def test_explicit_location_reuse_does_not_install(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "tools" / "bin"
            folder.mkdir(parents=True)
            for binary in ("ffmpeg.exe", "ffprobe.exe"):
                (folder / binary).write_bytes(b"test")
            completed = type("Result", (), {"returncode": 0, "stdout": "ffprobe version 7.0"})()
            with patch.object(dependencies.subprocess, "run", return_value=completed):
                dependencies.save_binary(root, folder)
                found = dependencies.resolve(root)
            self.assertEqual(str(folder.resolve()), found["directory"])


if __name__ == "__main__":
    unittest.main()
