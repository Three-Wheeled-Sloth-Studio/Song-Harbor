"""Offline mock provider must be deterministic, bounded and nonmutating."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements
import midi_proposal_mock
import midi_proposal_preview

SECTIONS=[{"id":"verse","start_seconds":0,"end_seconds":2},
          {"id":"chorus","start_seconds":2,"end_seconds":4}]
LIBRARY={"instruments":[]}

class MockProviderTests(unittest.TestCase):
    def setUp(self):
        self.asset=midi_arrangements.create("bass-source",0,4,[
            {"start":0.25,"end":0.5,"pitch":40,"velocity":100},
            {"start":2.25,"end":2.5,"pitch":42,"velocity":125},
            {"start":1.75,"end":2.25,"pitch":44,"velocity":80}])

    def test_mock_changes_only_contained_notes(self):
        before=midi_arrangements.validate(self.asset)
        result=midi_proposal_mock.propose(self.asset,SECTIONS,["verse","chorus"],"Bass",5)
        self.assertEqual(result["base_revision"],0)
        self.assertEqual(len(result["operations"]),2)
        self.assertEqual([operation["changes"]["velocity"] for operation in result["operations"]],[105,127])
        review=midi_proposal_preview.preview(self.asset,result,SECTIONS,LIBRARY)
        self.assertEqual(len(review["note_diff"]["changed"]),2)
        self.assertFalse(review["mutated"])
        self.assertEqual(self.asset,before)
        self.assertEqual(result,midi_proposal_mock.propose(self.asset,SECTIONS,["verse","chorus"],"Bass",5))

    def test_scope_and_velocity_bounds(self):
        with self.assertRaisesRegex(ValueError,"Unknown"):
            midi_proposal_mock.propose(self.asset,SECTIONS,["missing"],"Bass",5)
        with self.assertRaisesRegex(ValueError,"distinct"):
            midi_proposal_mock.propose(self.asset,SECTIONS,["verse","verse"],"Bass",5)
        with self.assertRaisesRegex(ValueError,"adjustment"):
            midi_proposal_mock.propose(self.asset,SECTIONS,["verse"],"Bass",0)
        with self.assertRaisesRegex(ValueError,"adjustment"):
            midi_proposal_mock.propose(self.asset,SECTIONS,["verse"],"Bass",99)

    def test_only_boundary_crossing_notes_not_edited(self):
        asset=midi_arrangements.create("bass-source",0,4,[
            {"start":1.8,"end":2.2,"pitch":40,"velocity":80}])
        with self.assertRaisesRegex(ValueError,"No eligible"):
            midi_proposal_mock.propose(asset,SECTIONS,["verse","chorus"],"Bass",5)

if __name__=="__main__":
    unittest.main()
