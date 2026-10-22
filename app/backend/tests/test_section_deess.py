"""Contract tests: de-esser instructions survive the authoritative script importer."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_production as production
import section_import

FILES=["01 (Vocals).wav","02 (Drums).wav","03 (Bass).wav",
       "04 (Guitar).wav","05 (Piano).wav","06 (Other).wav"]

class DeEssScriptTests(unittest.TestCase):
    def test_parse_roundtrip_and_bounds(self):
        script="{Vocals.deess:6500,2,-34,6@2s:smooth}"
        parsed=production.parse_block(script)
        self.assertEqual(parsed[0]["kind"],"deess")
        self.assertEqual(parsed[0]["frequency"],6500)
        self.assertEqual(production.parse_block(production.render_block(parsed)),parsed)
        for bad in ("Vocals.deess:12000,2,-34,6",
                    "Vocals.deess:6500,2,-90,6",
                    "Vocals.deess:6500,2,-34,18",
                    "Vocals.deess:6500,0,-34,6",
                    "NoStem.deess:6500,2,-34,6"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                production.parse_block("{"+bad+"}")
    def test_section_import_persists_target_and_reset(self):
        content=("[Verse 0:00-0:10]\n"
                 "{Vocals.deess:6500,2,-34,6@2s:smooth}\n"
                 "Original lyric stays\n\n"
                 "[Outro 0:10-0:20]\n"
                 "{Vocals.reset@1s:smooth Master.fade:2s:smooth}\n")
        result=section_import.apply({"files":FILES,"sections":[]},content,"replace",20)
        targets=[item for item in result["section_dynamics_automation"] if item["kind"]=="deess"]
        self.assertEqual(len(targets),2)
        self.assertEqual(targets[0]["source_key"],FILES[0])
        self.assertEqual(targets[0]["max_reduction_db"],6)
        self.assertEqual(targets[-1]["max_reduction_db"],0)
        self.assertIn("Original lyric stays",section_import.render_tags({
          **result,"source_duration_seconds":20}))
    def test_reset_and_specific_deess_conflict(self):
        with self.assertRaises(ValueError):
            production.parse_block("{Vocals.reset@1s:smooth Vocals.deess:6500,2,-34,6@2s:smooth}")

if __name__=="__main__":unittest.main()
