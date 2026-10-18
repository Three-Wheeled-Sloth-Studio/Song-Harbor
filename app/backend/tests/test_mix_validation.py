"""Mix requests must never escape the six source stems or silently overwrite them."""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SPEC = importlib.util.spec_from_file_location(
    "song_harbor_server", Path(__file__).resolve().parents[1] / "server.py"
)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)
NAMES = ["a_(Vocals).wav", "a_(Drums).wav", "a_(Bass).wav",
         "a_(Guitar).wav", "a_(Piano).wav", "a_(Other).wav"]


class MixValidationTests(unittest.TestCase):
    def settings(self):
        return [server.StemMixSetting(filename=n, gain=1.0) for n in NAMES]

    def test_all_stems_at_unity(self):
        self.assertEqual([(n, 1.0) for n in NAMES],
                         server.validate_mix({"files": NAMES}, self.settings()))

    def test_solo_mute_and_gain(self):
        values = self.settings()
        values[0].solo = True
        values[1].solo = True
        values[1].mute = True
        values[0].gain = 0.35
        levels = dict(server.validate_mix({"files": NAMES}, values))
        self.assertEqual(0.35, levels[NAMES[0]])
        self.assertEqual(0, levels[NAMES[1]])
        self.assertEqual(0, levels[NAMES[2]])

    def test_duplicate_stems_rejected(self):
        values = self.settings()
        values[5].filename = values[0].filename
        with self.assertRaises(ValueError):
            server.validate_mix({"files": NAMES}, values)

    def test_other_file_rejected(self):
        values = self.settings()
        values[0].filename = "../../private.wav"
        with self.assertRaises(ValueError):
            server.validate_mix({"files": NAMES}, values)

    def test_gain_restricted_to_zero_through_two(self):
        with self.assertRaises(Exception):
            server.StemMixSetting(filename=NAMES[0], gain=-1)
        with self.assertRaises(Exception):
            server.StemMixSetting(filename=NAMES[0], gain=3)


if __name__ == "__main__":
    unittest.main()
