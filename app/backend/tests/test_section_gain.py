"""Regression coverage for gain relative to saved stem faders."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import
import section_production

FILES=["song (Vocals).wav","song (Drums).wav"]

class SectionGainTests(unittest.TestCase):
    def test_import_round_trip_inheritance_reset(self):
        sheet=("[Verse 0:00-0:10]\n{Drums.gain:+0.75@2s:smooth}\n"
               "[Chorus 0:10-0:20]\n"
               "[Outro 0:20-0:30]\n{all.reset@3s:linear}\n")
        initial={"sections":[],"files":FILES}
        changed=section_import.apply(initial,sheet,"replace",30)
        targets=changed["section_gain_automation"]
        self.assertEqual([(x["gain_db"],x["curve"]) for x in targets
                          if "(Drums)" in x["source_key"]],[(0.75,"smooth"),(0.0,"linear")])
        self.assertEqual(len(targets),3)
        restored=section_import.apply({**initial,**changed},
                                      section_import.render_tags({**initial,**changed}),"replace",30)
        self.assertEqual(targets,restored["section_gain_automation"])

    def test_limits_and_duplicates(self):
        for block in ("{Drums.gain:+13}","{Drums.gain:-25}","{Drums.gain:+1@40s}",
                      "{Drums.gain:+1 Drums.gain:+2}",
                      "{Drums.gain:+1 all.reset}","{auto.gain:0}"):
            with self.subTest(block=block),self.assertRaises(ValueError):
                section_production.parse_block(block,("Vocals","Drums"))
        self.assertEqual(section_production.parse_block("{Vocals.gain:-2.5}")[0]["gain_db"],-2.5)

    def test_unmentioned_stems_are_not_materialized(self):
        changed=section_import.apply({"sections":[],"files":FILES},
            "[Verse 0:00-0:10]\n{Drums.gain:+.75}","replace",10)
        self.assertEqual(len(changed["section_gain_automation"]),1)

if __name__=="__main__":
    unittest.main()
