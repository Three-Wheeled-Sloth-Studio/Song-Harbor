"""De-click manifests remain local, reversible, and never modify WAV bytes."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import declick_recipes


class DeclickRecipeTests(unittest.TestCase):
    def test_round_trip_accept_undo_keeps_source_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            wav=folder/"Vocals.wav"
            wav.write_bytes(b"existing source must not be edited")
            before=wav.read_bytes()
            recipe={"id":"click-1","filename":"Vocals.wav","source_key":"Vocals.wav",
                    "time_seconds":21.35,"half_window_ms":1.0,"source_sha256":"a"*64}
            saved=declick_recipes.append(folder,recipe,{"Vocals.wav"})
            self.assertEqual(saved,[recipe])
            self.assertEqual(declick_recipes.read(folder),saved)
            self.assertEqual(wav.read_bytes(),before)
            self.assertEqual(declick_recipes.remove(folder,"click-1"),[])
            self.assertEqual(declick_recipes.read(folder),[])
            self.assertEqual(wav.read_bytes(),before)

    def test_duplicate_and_missing_sources_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            repair={"id":"same","filename":"Other.wav","source_key":"Other.wav",
                    "time_seconds":3.0,"half_window_ms":.5,"source_sha256":"b"*64}
            with self.assertRaisesRegex(ValueError,"not an active"):
                declick_recipes.append(folder,repair,{"Vocals.wav"})
            declick_recipes.append(folder,repair,{"Other.wav"})
            with self.assertRaisesRegex(ValueError,"already exists"):
                declick_recipes.append(folder,repair,{"Other.wav"})
            with self.assertRaisesRegex(ValueError,"not found"):
                declick_recipes.remove(folder,"other")

    def test_nan_and_oversized_repair_windows_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            repair={"id":"test","filename":"A.wav","source_key":"A.wav",
                    "time_seconds":float("nan"),"half_window_ms":1,"source_sha256":"c"*64}
            with self.assertRaisesRegex(ValueError,"time"):
                declick_recipes.append(folder,repair,{"A.wav"})
            repair["time_seconds"]=1
            repair["half_window_ms"]=4
            with self.assertRaisesRegex(ValueError,"window"):
                declick_recipes.append(folder,repair,{"A.wav"})


if __name__=="__main__":
    unittest.main()
