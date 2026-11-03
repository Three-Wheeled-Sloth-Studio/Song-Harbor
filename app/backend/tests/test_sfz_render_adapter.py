"""Isolated regression tests for the optional sfizz subprocess adapter."""
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sfz_render_adapter as sfz


class SFZAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.midi = root / "score.mid"
        self.instrument = root / "cello.sfz"
        self.exe = root / "sfizz_render.exe"
        self.output = root / "candidate.wav"
        for path in (self.midi, self.instrument, self.exe):
            path.write_bytes(b"fixture")

    def write_wav(self, rate=48000, channels=2):
        with wave.open(str(self.output), "wb") as f:
            f.setnchannels(channels)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(b"\x00\x00" * channels * 20)

    def test_missing_renderer(self):
        with self.assertRaisesRegex(sfz.SFZRenderError, "does not exist"):
            sfz.locate_renderer(str(self.output))

    def test_render_and_no_overwrite(self):
        def invoke(args, **kwargs):
            self.assertEqual(args[0], str(self.exe))
            self.assertIn("--samplerate", args)
            self.assertFalse(kwargs["shell"])
            self.write_wav()
            return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        with patch.object(sfz.subprocess, "run", side_effect=invoke):
            self.assertEqual(sfz.render_sfz(self.midi, self.instrument, self.output,
                                             renderer=str(self.exe)), self.output)
        with self.assertRaisesRegex(sfz.SFZRenderError, "overwrite"):
            sfz.render_sfz(self.midi, self.instrument, self.output, renderer=str(self.exe))

    def test_bad_rate_cleans_output(self):
        def invoke(*_args, **_kwargs):
            self.write_wav(rate=44100)
            return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        with patch.object(sfz.subprocess, "run", side_effect=invoke):
            with self.assertRaisesRegex(sfz.SFZRenderError, "48-kHz"):
                sfz.render_sfz(self.midi, self.instrument, self.output, renderer=str(self.exe))
        self.assertFalse(self.output.exists())

    def test_nonzero_exit_cleans_even_valid_wav(self):
        def invoke(*_args, **_kwargs):
            self.write_wav()
            return type("Result", (), {"returncode": 2, "stderr": "bad sample", "stdout": ""})()
        with patch.object(sfz.subprocess, "run", side_effect=invoke):
            with self.assertRaisesRegex(sfz.SFZRenderError, "bad sample"):
                sfz.render_sfz(self.midi, self.instrument, self.output, renderer=str(self.exe))
        self.assertFalse(self.output.exists())

    def test_timeout_bounds(self):
        with self.assertRaisesRegex(sfz.SFZRenderError, "timeout"):
            sfz.render_sfz(self.midi, self.instrument, self.output,
                           renderer=str(self.exe), timeout_seconds=601)


if __name__ == "__main__":
    unittest.main()
