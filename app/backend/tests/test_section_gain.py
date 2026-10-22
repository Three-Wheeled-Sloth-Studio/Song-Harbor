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

    def test_broadcast_gain_explicit_override_and_round_trip(self):
        sheet=("[Verse 0:00-0:10]\n"
               "{all.gain:-1@2s:smooth Drums.gain:+0.75@3s:linear}\n"
               "[Chorus 0:10-0:20]\n{all.gain:0@1s:smooth}\n")
        initial={"sections":[],"files":FILES}
        changed=section_import.apply(initial,sheet,"replace",20)
        targets=changed["section_gain_automation"]
        first=changed["sections"][0]["id"]
        verse=[x for x in targets if x["section_id"]==first]
        self.assertEqual(len(verse),2)
        self.assertEqual(next(x["gain_db"] for x in verse if "(Vocals)" in x["source_key"]),-1)
        self.assertEqual(next(x["gain_db"] for x in verse if "(Drums)" in x["source_key"]),.75)
        rendered=section_import.render_tags({**initial,**changed})
        self.assertIn("all.gain:-1",rendered)
        restored=section_import.apply({**initial,**changed},rendered,"replace",20)
        self.assertEqual(targets,restored["section_gain_automation"])

    def test_broadcast_pan_width_reverb_space_eq_precedence(self):
        sheet=("[Verse 0:00-0:10]\n"
               "{all.pan:right.20 Vocals.pan:left.50 all.width:110 "
               "Drums.width:125 all.reverb:15 Vocals.reverb:40 "
               "all.space:10 Drums.space:25 all.eq1:1000,1,+1 "
               "Vocals.eq1:800,1,-2}\n")
        result=section_import.apply({"sections":[],"files":FILES},sheet,"replace",10)
        sid=result["sections"][0]["id"]
        cases=(("section_pan_automation","pan",-0.5,0.2),
               ("section_width_automation","width",110,125),
               ("section_reverb_automation","wet",.4,.15),
               ("section_space_automation","amount",10,25))
        for field,value,vocal,drums in cases:
            targets=[x for x in result[field] if x["section_id"]==sid]
            self.assertEqual(len(targets),2,field)
            self.assertEqual(next(x[value] for x in targets if "(Vocals)" in x["source_key"]),vocal)
            self.assertEqual(next(x[value] for x in targets if "(Drums)" in x["source_key"]),drums)
        eq=result["section_eq_automation"]
        self.assertEqual(len(eq),2)
        self.assertEqual(next(x["gain_db"] for x in eq if "(Vocals)" in x["source_key"]),-2)
        self.assertEqual(next(x["gain_db"] for x in eq if "(Drums)" in x["source_key"]),1)

    def test_duplicate_broadcast_rejected(self):
        for block in ("{all.gain:+1 all.gain:+2}","{all.pan:center all.pan:left.20}",
                      "{all.reset all.gain:+1}","{all.gain:+1 all.reset}",
                      "{all.eq1:1000,1,+1 all.eq1:2000,1,+2}"):
            with self.subTest(block=block),self.assertRaises(ValueError):
                section_production.parse_block(block,("Vocals","Drums"))

    def test_unmentioned_stems_are_not_materialized(self):
        changed=section_import.apply({"sections":[],"files":FILES},
            "[Verse 0:00-0:10]\n{Drums.gain:+.75}","replace",10)
        self.assertEqual(len(changed["section_gain_automation"]),1)

if __name__=="__main__":
    unittest.main()
