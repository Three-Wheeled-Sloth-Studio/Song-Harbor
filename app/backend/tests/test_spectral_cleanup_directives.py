"""Regression: Sound Cleanup EQ repair must parse as a standard section EQ."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_production


class SpectralCleanupDirectiveTests(unittest.TestCase):
    def test_surgical_section_cut_is_valid_persisted_eq(self):
        result=section_production.parse_block(
            "{Vocals.eq3:3500,2.0,-3.0@1.5s:smooth}")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["kind"],"eq")
        self.assertEqual(result[0]["track"],"Vocals")
        self.assertEqual(result[0]["band"],3)
        self.assertEqual(result[0]["frequency"],3500)
        self.assertEqual(result[0]["gain_db"],-3)
        self.assertEqual(result[0]["transition_seconds"],1.5)

    def test_duplicate_band_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate|conflicting"):
            section_production.parse_block(
                "{Vocals.eq3:3500,2.0,-3.0@1.5s:smooth "
                "Vocals.eq3:4700,2.0,-2.0@1.5s:smooth}")

    def test_other_existing_eq_bands_are_independent(self):
        parsed=section_production.parse_block(
            "{Other.eq1:380,0.9,1.1@3s:smooth "
            "Other.eq3:3400,2.0,-2.5@3s:smooth}")
        self.assertEqual([x["band"] for x in parsed],[1,3])


if __name__=="__main__":
    unittest.main()
