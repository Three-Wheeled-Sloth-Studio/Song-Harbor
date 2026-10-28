"""Lego intent tests do not need ACE, models, or source audio."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from instrument_generation import validate_intent, require_native_lego, normalize_lego_track

class InstrumentGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tracks = [{"track_id":"trk_bass", "working_filename":"Bass.wav"},
                       {"track_id":"trk_drums", "working_filename":"Drums.wav"}]

    def test_add_strings_uses_family_not_cello_class(self):
        intent=validate_intent("add","strings","Bowed violin counterpoint",None,self.tracks)
        self.assertEqual(intent.instrument,"strings")
        self.assertIsNone(intent.target_track_id)

    def test_replacement_requires_existing_track(self):
        intent=validate_intent("replace","bass","New bass meshing with drums","trk_bass",self.tracks)
        self.assertEqual(intent.target_track_id,"trk_bass")
        for bad in (None,"trk_missing"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_intent("replace","bass","Groove",bad,self.tracks)

    def test_vocals_not_valid_in_instrumental_workflows(self):
        for instrument in ("vocals","backing_vocals","cello","violin"):
            with self.subTest(instrument=instrument), self.assertRaises(ValueError):
                validate_intent("add",instrument,"Something",None,self.tracks)

    def test_experimental_vocal_target_is_separate_from_instrument_intents(self):
        self.assertEqual(normalize_lego_track("backing_vocals"),"backing_vocals")
        with self.assertRaises(ValueError):
            validate_intent("add","backing_vocals","Hum",None,self.tracks)

    def test_add_cannot_accidentally_replace(self):
        with self.assertRaises(ValueError):
            validate_intent("add","bass","Groove","trk_bass",self.tracks)

    def test_checkpoint_requires_explicit_verified_lego(self):
        for model in (None,{"name":"acestep-v15-turbo","loaded":True},
                      {"name":"acestep-v15-base","loaded":True},
                      {"name":"acestep-v15-base","loaded":False,"verified_native_lego":True}):
            with self.subTest(model=model), self.assertRaises(ValueError):
                require_native_lego(model)
        require_native_lego({"name":"acestep-v15-base","loaded":True,"verified_native_lego":True})

if __name__ == "__main__":
    unittest.main()
