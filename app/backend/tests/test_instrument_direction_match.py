"""Deterministic installed-pack instrument interpretation tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import instrument_direction_match as matching

CATALOGUE={
 "packs":[{"id":"sfz-1234","name":"Karoryfer Growlybass","curated_id":"growlybass"},
          {"id":"sfz-7777","name":"Karoryfer Big Rusty Drums","curated_id":"big-rusty-drums"}],
 "instruments":[
  {"id":"sfz-0","pack_id":"sfz-1234","name":"growlybass_dirty"},
  {"id":"sfz-1","pack_id":"sfz-1234","name":"growlybass_angry"},
  {"id":"sfz-2","pack_id":"sfz-1234","name":"growlybass_shifty"},
  {"id":"sfz-3","pack_id":"sfz-1234","name":"growlybass_clean"},
  {"id":"sfz-0","pack_id":"sfz-7777","name":"big_rusty_drums_kit"}]}

class InstrumentMatchTests(unittest.TestCase):
 def test_pack_then_variant_then_unmatched_style(self):
  instruction="Rebuild bass with Growlybass Dirty as default, angry for choruses, shifty for bridges, maintain and enhance industrial elements."
  result=matching.resolve(instruction,CATALOGUE)
  self.assertEqual(result["status"],"matched")
  self.assertEqual(result["family"]["pack_id"],"sfz-1234")
  assignments={row["section"]:row["instrument_name"] for row in result["assignments"]}
  self.assertEqual(assignments,{"default":"growlybass_dirty","chorus":"growlybass_angry","bridge":"growlybass_shifty"})
  self.assertIn("industrial",result["unresolved_text"])
  self.assertNotIn("industrial",[r["variant"] for r in result["assignments"]])

 def test_missing_pack_is_not_invented(self):
  result=matching.resolve("Use noninstalled rubberbass nasty on the chorus.",CATALOGUE)
  self.assertEqual(result["status"],"no_family_match")
  self.assertEqual(result["assignments"],[])

 def test_no_unverified_variant(self):
  result=matching.resolve("Use Growlybass industrial for choruses.",CATALOGUE)
  self.assertEqual(result["family"]["pack_id"],"sfz-1234")
  self.assertEqual(result["assignments"],[])
  self.assertIn("industrial",result["unresolved_text"])

 def test_multiple_pack_matches_require_review(self):
  result=matching.resolve("Use Growlybass and Big Rusty Drums.",CATALOGUE)
  self.assertEqual(result["status"],"ambiguous")
  self.assertEqual(len(result["families"]),2)
  self.assertEqual(result["assignments"],[])

 def test_same_section_multiple_variants_require_review(self):
  result=matching.resolve("Growlybass dirty and clean in choruses.",CATALOGUE)
  self.assertEqual(result["status"],"ambiguous")
  self.assertTrue(result["conflicts"])

 def test_request_is_bounded(self):
  with self.assertRaises(ValueError):matching.resolve("",CATALOGUE)
  with self.assertRaises(ValueError):matching.resolve("x"*3001,CATALOGUE)

if __name__=="__main__":
 unittest.main()
