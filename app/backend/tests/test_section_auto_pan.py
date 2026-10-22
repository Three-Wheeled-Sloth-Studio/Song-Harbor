import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import,section_production

FILES=["song (Vocals).wav","song (Drums).wav","song (Other).wav"]

class AutoPanNotationTests(unittest.TestCase):
    def test_import_roundtrip_and_inherited_protection(self):
        sheet=("[Intro 0:00-0:10]\n{Vocals.pan:left.35 auto.pan:center@6s:smooth}\n"
               "[Verse 0:10-0:20]\n{Drums.gain:+0.75 auto.pan:center}\n"
               "[Outro 0:20-0:30]\n{all.reset}\n")
        project={"sections":[],"files":FILES}
        result=section_import.apply(project,sheet,"replace",30)
        requests=result["section_auto_pan"]
        self.assertEqual(len(requests),2)
        self.assertEqual(requests[0]["transition_seconds"],6)
        self.assertEqual(requests[0]["protected_sources"],["song (Vocals).wav"])
        self.assertEqual(requests[1]["protected_sources"],["song (Vocals).wav"])
        self.assertEqual(len(result["section_pan_automation"]),4)
        restored=section_import.apply({**project,**result},
            section_import.render_tags({**project,**result}),"replace",30)
        self.assertEqual(requests,restored["section_auto_pan"])

    def test_all_pan_protects_everything(self):
        result=section_import.apply({"sections":[],"files":FILES},
            "[Verse 0:00-0:10]\n{all.pan:center auto.pan:center}\n","replace",10)
        self.assertEqual(set(result["section_auto_pan"][0]["protected_sources"]),set(FILES))

    def test_fail_closed(self):
        for token in ("auto.pan:left.20","auto.pan:right","auto.gain:0",
                      "auto.pan:center@40s","auto.pan:center auto.pan:center",
                      "all.reset auto.pan:center"):
            with self.subTest(token=token),self.assertRaises(ValueError):
                section_production.parse_block("{"+token+"}")

if __name__=="__main__":
    unittest.main()
