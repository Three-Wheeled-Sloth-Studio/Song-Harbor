"""Regression checks for full-song output duration validation."""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SPEC = importlib.util.spec_from_file_location("song_harbor_server", Path(__file__).resolve().parents[1] / "server.py")
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class DurationValidationTests(unittest.TestCase):
    def test_six_matching_stems_pass(self):
        durations = {name: 301.0 for name in ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")}
        self.assertEqual([], server.validate_stem_lengths(301.0, durations))

    def test_four_minute_truncation_rejected(self):
        durations = {name: 240.0 for name in ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")}
        problems = server.validate_stem_lengths(312.0, durations)
        self.assertEqual(6, len(problems))
        self.assertIn("240.00s vs source 312.00s", problems[0])

    def test_small_codec_container_difference_tolerated(self):
        self.assertEqual([], server.validate_stem_lengths(299.999, {"Vocals": 300.012}))


if __name__ == "__main__":
    unittest.main()
