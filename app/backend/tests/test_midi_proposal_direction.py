"""Direction-to-recipe routing remains grounded and does not edit source notes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements
import midi_proposal_direction
import midi_proposal_preview

PACKS={
    "packs":[{"id":"pack-growly","name":"Karoryfer Growlybass","curated_id":"growlybass"}],
    "instruments":[
        {"pack_id":"pack-growly","id":"dirty","name":"growlybass_dirty","engine":"sfz"},
        {"pack_id":"pack-growly","id":"angry","name":"growlybass_angry","engine":"sfz"},
        {"pack_id":"pack-growly","id":"shifty","name":"growlybass_shifty","engine":"sfz"}]
}
SECTIONS=[{"id":"intro","kind":"Intro","start_seconds":0,"end_seconds":1},
          {"id":"verse","kind":"Verse","start_seconds":1,"end_seconds":2},
          {"id":"chorus1","kind":"Chorus","start_seconds":2,"end_seconds":3},
          {"id":"bridge","kind":"Bridge","start_seconds":3,"end_seconds":4},
          {"id":"chorus2","kind":"Chorus","start_seconds":4,"end_seconds":5}]
TEXT="Growlybass Dirty as default, Angry for choruses, Shifty for bridges. Maintain industrial elements."

class DirectionProposalTests(unittest.TestCase):
    def setUp(self):
        self.asset=midi_arrangements.create("source",0,5,[
            {"start":1.1,"end":1.3,"pitch":40,"velocity":85}])

    def test_generates_reviewable_preset_recipe_with_multiple_choruses(self):
        before=midi_arrangements.validate(self.asset)
        selected=[s["id"] for s in SECTIONS]
        proposal,match=midi_proposal_direction.propose(
            self.asset,SECTIONS,selected,"Bass",TEXT,PACKS)
        self.assertEqual(match["status"],"matched")
        self.assertEqual(proposal["operations"],[])
        self.assertEqual(proposal["instrument_sections"]["default"]["instrument_id"],"dirty")
        overrides={row["section_id"]:row["instrument_id"]
                   for row in proposal["instrument_sections"]["overrides"]}
        self.assertEqual(overrides,{"chorus1":"angry","chorus2":"angry","bridge":"shifty"})
        review=midi_proposal_preview.preview(self.asset,proposal,SECTIONS,PACKS)
        self.assertFalse(review["mutated"])
        self.assertEqual(review["instrument_after"],proposal["instrument_sections"])
        self.assertEqual(self.asset,before)

    def test_missing_variant_fails_without_fake_preset(self):
        with self.assertRaises(ValueError):
            midi_proposal_direction.propose(self.asset,SECTIONS,
                ["intro","verse"],"Bass","Growlybass noisy for every section",PACKS)

    def test_missing_named_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"No selected sections match"):
            midi_proposal_direction.propose(self.asset,SECTIONS,["verse"],"Bass",TEXT,PACKS)

if __name__=="__main__":
    unittest.main()
