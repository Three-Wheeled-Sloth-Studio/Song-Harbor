"""Review-only proposal contract protects scores from provider output."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements
import midi_proposal_preview

CATALOGUE={"instruments":[
    {"pack_id":"growly","id":"dirty","engine":"sfz"},
    {"pack_id":"growly","id":"angry","engine":"sfz"},
    {"pack_id":"growly","id":"shifty","engine":"sfz"}]}
SECTIONS=[{"id":"verse","start_seconds":0,"end_seconds":2},
          {"id":"chorus","start_seconds":2,"end_seconds":4}]


class ProposalPreviewTests(unittest.TestCase):
    def setUp(self):
        self.asset=midi_arrangements.create("track-bass",0,4,[
            {"pitch":36,"start":0,"end":1,"velocity":90},
            {"pitch":38,"start":2,"end":3,"velocity":95}])
        self.recipe={"schema_version":1,
                     "default":{"pack_id":"growly","instrument_id":"dirty"},
                     "section_ids":["verse","chorus"],
                     "overrides":[{"section_id":"chorus","pack_id":"growly","instrument_id":"angry"}]}
        self.proposal={
            "schema_version":1,"base_revision":0,"source_track_id":"track-bass",
            "target_stem":"Bass",
            "sections":[{"section_id":"verse","intent":"Maintain groove"},
                        {"section_id":"chorus","intent":"Increase intensity"}],
            "operations":[{"op":"update","id":self.asset["notes"][0]["id"],
                           "changes":{"velocity":105}}],
            "instrument_sections":self.recipe,
        }

    def test_read_only_diff_with_installed_section_variants(self):
        before=midi_arrangements.validate(self.asset)
        output=midi_proposal_preview.preview(self.asset,self.proposal,SECTIONS,CATALOGUE)
        self.assertEqual(output["status"],"review_only")
        self.assertEqual(len(output["note_diff"]["changed"]),1)
        self.assertEqual(output["instrument_after"]["default"]["instrument_id"],"dirty")
        self.assertFalse(output["mutated"])
        self.assertEqual(self.asset,before)

    def test_reject_stale_revision_and_missing_instrument(self):
        stale={**self.proposal,"base_revision":9}
        with self.assertRaisesRegex(ValueError,"Stale"):
            midi_proposal_preview.preview(self.asset,stale,SECTIONS,CATALOGUE)
        missing={**self.recipe,"overrides":[
            {"section_id":"chorus","pack_id":"growly","instrument_id":"not-installed"}]}
        with self.assertRaisesRegex(ValueError,"not installed"):
            midi_proposal_preview.preview(self.asset,{
                **self.proposal,"instrument_sections":missing},SECTIONS,CATALOGUE)

    def test_reject_vocal_target_and_wrong_source(self):
        with self.assertRaisesRegex(ValueError,"target"):
            midi_proposal_preview.preview(self.asset,{
                **self.proposal,"target_stem":"Vocals"},SECTIONS,CATALOGUE)
        with self.assertRaisesRegex(ValueError,"source track"):
            midi_proposal_preview.preview(self.asset,{
                **self.proposal,"source_track_id":"different"},SECTIONS,CATALOGUE)

    def test_reject_invalid_note_and_section(self):
        with self.assertRaisesRegex(ValueError,"velocity"):
            midi_proposal_preview.preview(self.asset,{
                **self.proposal,"operations":[{"op":"update","id":self.asset["notes"][0]["id"],
                                               "changes":{"velocity":200}}]},SECTIONS,CATALOGUE)
        with self.assertRaisesRegex(ValueError,"Unknown"):
            midi_proposal_preview.preview(self.asset,{
                **self.proposal,"sections":[{"section_id":"unknown","intent":"Loud"}]},SECTIONS,CATALOGUE)


if __name__=="__main__":
    unittest.main()
