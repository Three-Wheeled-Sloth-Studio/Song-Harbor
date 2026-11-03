"""Regression tests for durable MIDI assets and future LLM edit transactions."""
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements as midi

class ArrangementTests(unittest.TestCase):
    def sample(self):
        return midi.create("track-bass",12.5,8,[{"start":0.1,"end":1.2,"pitch":45,"velocity":90},
                                                {"start":0.8,"end":2.1,"pitch":52,"velocity":80}],"stem transcription")
    def test_create_polyphonic_stable_ids(self):
        asset=self.sample()
        self.assertEqual(len(asset["notes"]),2)
        self.assertNotEqual(asset["notes"][0]["id"],asset["notes"][1]["id"])
        self.assertEqual(asset["source"]["start_sample"],600000)
        self.assertEqual(asset["revision"],0)
    def test_atomic_patch_and_stale_revision(self):
        asset=self.sample()
        ident=asset["notes"][0]["id"]
        updated=midi.apply_patch(asset,0,[{"op":"update","id":ident,"changes":{"pitch":46}}])
        self.assertEqual(updated["revision"],1)
        self.assertEqual(asset["revision"],0)
        self.assertEqual(next(n for n in updated["notes"] if n["id"]==ident)["pitch"],46)
        with self.assertRaisesRegex(ValueError,"Stale"):
            midi.apply_patch(updated,0,[{"op":"remove","id":ident}])
        with self.assertRaises(ValueError):
            midi.apply_patch(asset,0,[{"op":"update","id":ident,"changes":{"pitch":500}}])
        self.assertEqual(asset["notes"][0]["pitch"],45)
    def test_add_remove_and_overlaps(self):
        asset=self.sample()
        ident=uuid.uuid4().hex
        extra={"id":ident,"start_sample":1000,"end_sample":4000,"pitch":60,"velocity":64,"channel":9}
        newer=midi.apply_patch(asset,0,[{"op":"add","note":extra}])
        self.assertEqual(len(newer["notes"]),3)
        self.assertEqual(len(midi.apply_patch(newer,1,[{"op":"remove","id":ident}])["notes"]),2)
    def test_persistent_roundtrip_and_invalid_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            asset=self.sample()
            midi.save(root,asset)
            self.assertEqual(midi.read(root,asset["asset_id"]),asset)
            self.assertEqual(len(midi.list_assets(root)),1)
            with self.assertRaises(ValueError):midi.read(root,"../escape")
    def test_reject_schema_duplicates_and_nonintegers(self):
        asset=self.sample()
        bad={**asset,"notes":[asset["notes"][0],asset["notes"][0]]}
        with self.assertRaises(ValueError):midi.validate(bad)
        bad={**asset,"notes":[{**asset["notes"][0],"pitch":44.0}]}
        with self.assertRaises(ValueError):midi.validate(bad)
        with self.assertRaises(ValueError):midi.apply_patch(asset,0,[{"op":"execute","code":"bad"}])
    def test_group_edit_persists_ids_and_remains_atomic(self):
        original = self.sample()
        first, second = original["notes"]
        third_id = uuid.uuid4().hex
        new_note = {"id": third_id, "start_sample": 4000, "end_sample": 9600,
                    "pitch": 60, "velocity": 72, "channel": 0}
        operations = [
            {"op": "update", "id": first["id"],
             "changes": {"start_sample": first["start_sample"] + 2400,
                         "end_sample": first["end_sample"] + 2400}},
            {"op": "update", "id": second["id"],
             "changes": {"velocity": 97}},
            {"op": "add", "note": new_note},
        ]
        saved = midi.apply_patch(original, 0, operations)
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(len(saved["notes"]), 3)
        self.assertEqual({n["id"] for n in saved["notes"]},
                         {first["id"], second["id"], third_id})
        self.assertEqual(original["revision"], 0)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            midi.save(root, saved)
            self.assertEqual(midi.read(root, saved["asset_id"]), saved)
        invalid = operations + [{"op": "update", "id": second["id"],
                                 "changes": {"velocity": 0}}]
        with self.assertRaises(ValueError):
            midi.apply_patch(original, 0, invalid)
        self.assertEqual(original["notes"][0], first)
        self.assertEqual(original["notes"][1], second)

    def test_no_implicit_quantization(self):
        asset=midi.create("drums",0,3,[{"start":.137,"end":.291,"pitch":38}])
        self.assertEqual(asset["notes"][0]["start_sample"],6576)

if __name__=="__main__":unittest.main()
