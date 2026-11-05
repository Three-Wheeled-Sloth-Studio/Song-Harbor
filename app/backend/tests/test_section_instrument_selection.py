"""Per-section preset routing validates actual installed instruments, not names."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_instrument_selection as choice

LIBRARY={
 "instruments":[
  {"pack_id":"pack-growly","id":"dirty","name":"growlybass_dirty","engine":"sfz"},
  {"pack_id":"pack-growly","id":"angry","name":"growlybass_angry","engine":"sfz"},
  {"pack_id":"pack-growly","id":"shifty","name":"growlybass_shifty","engine":"sfz"},
  {"pack_id":"pack-core","id":"plucked","engine":"synthetic"}]}
SECTIONS=["intro","verse","chorus","bridge"]

class SectionInstrumentSelectionTests(unittest.TestCase):
 def test_one_instrument_part_with_section_variants(self):
  selected=choice.resolve(SECTIONS,[
   {"section_id":"chorus","pack_id":"pack-growly","instrument_id":"angry"},
   {"section_id":"bridge","pack_id":"pack-growly","instrument_id":"shifty"}
  ],"pack-growly","dirty",LIBRARY)
  self.assertEqual(len(selected),4)
  self.assertEqual([selected[s]["instrument_id"] for s in SECTIONS],
                   ["dirty","dirty","angry","shifty"])

 def test_duplicate_and_unselected_override_rejected(self):
  for overrides in (
   [{"section_id":"chorus","pack_id":"pack-growly","instrument_id":"angry"}]*2,
   [{"section_id":"not_selected","pack_id":"pack-growly","instrument_id":"angry"}]
  ):
   with self.subTest(overrides=overrides),self.assertRaises(ValueError):
    choice.resolve(SECTIONS,overrides,"pack-growly","dirty",LIBRARY)

 def test_absent_and_synthetic_presets_rejected(self):
  for pack,instrument in [("pack-growly","not_installed"),("pack-core","plucked")]:
   with self.subTest(instrument=instrument),self.assertRaises(ValueError):
    choice.resolve(SECTIONS,[{"section_id":"chorus","pack_id":pack,"instrument_id":instrument}],
                   "pack-growly","dirty",LIBRARY)

 def test_missing_default_and_oversized_selection_rejected(self):
  with self.assertRaises(ValueError):
   choice.resolve(SECTIONS,[],"pack-growly","not-installed",LIBRARY)
  with self.assertRaises(ValueError):
   choice.resolve(["intro"]*2,[],"pack-growly","dirty",LIBRARY)
  with self.assertRaises(ValueError):
   choice.resolve([str(n) for n in range(9)],[],"pack-growly","dirty",LIBRARY)

 def test_pure_no_mutation(self):
  overrides=[{"section_id":"chorus","pack_id":"pack-growly","instrument_id":"angry"}]
  before=[dict(row) for row in overrides]
  choice.resolve(SECTIONS,overrides,"pack-growly","dirty",LIBRARY)
  self.assertEqual(overrides,before)

if __name__=="__main__":
 unittest.main()
