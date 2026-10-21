import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import
import section_production

FILES=[f"song ({name}).wav" for name in section_production.ALIASES]

class SectionDynamicsTests(unittest.TestCase):
    def test_script_roundtrip_and_reset(self):
        script=("[Verse 0:00-0:10]\n"
                "{Other.comp:-18,2@2s:smooth Guitar.duck:4@1s:linear}\n"
                "[Chorus 0:10-0:20]\n{Other.comp:-24,2.5@2s:smooth}\n"
                "[Outro 0:20-0:30]\n{all.reset@2s:smooth Master.fade:4s:smooth Master.tail:3s}\n")
        project={"files":FILES,"sections":[]}
        changed=section_import.apply(project,script,"replace",30)
        dynamics=changed["section_dynamics_automation"]
        other=[x for x in dynamics if "(Other)" in x["source_key"] and x["kind"]=="comp"]
        self.assertEqual([x["ratio"] for x in other],[2,2.5,1])
        guitar=[x for x in dynamics if "(Guitar)" in x["source_key"] and x["kind"]=="duck"]
        self.assertEqual([x["depth_db"] for x in guitar],[4,0])
        self.assertEqual(changed["section_ending"]["tail_seconds"],3)
        restored=section_import.apply({"files":FILES,**changed},section_import.render_tags({"files":FILES,**changed}),"replace",30)
        self.assertEqual(restored["section_dynamics_automation"],dynamics)

    def test_reject_bad_settings(self):
        for token in ("Vocals.duck:2","Other.duck:13","Other.duck:-1",
                      "Other.comp:-70,2","Other.comp:-18,5","Other.comp:-18",
                      "Other.comp:-18,2 Other.comp:-15,2"):
            with self.subTest(token=token),self.assertRaises(ValueError):
                section_production.parse_block("{"+token+"}")

    def test_outro_broad_reset_conflicts_with_spatial_settings(self):
        bad=("{Other.reset@2s:smooth Guitar.duck:0@1s:smooth "
             "Other.pan:right.4@3s:smooth Other.width:95@3s:smooth "
             "Other.space:18@3s:smooth Master.fade:4s:smooth Master.tail:3s}")
        with self.assertRaisesRegex(ValueError, r"Other\.reset conflicts"):
            section_production.parse_block(bad)
        repaired=bad.replace("Other.reset@2s:smooth","Other.comp:-18,1@2s:smooth")
        parsed=section_production.parse_block(repaired)
        self.assertEqual(len(parsed),7)
        self.assertEqual([d["kind"] for d in parsed],
                         ["comp","duck","pan","width","space","fade","tail"])
        script=("[Verse 0:00-0:10]\n{Other.comp:-18,2@2s:smooth}\n"
                "[Outro 0:10-0:20]\n"+repaired+"\n")
        result=section_import.apply({"files":FILES,"sections":[]},script,"replace",20)
        other=[t for t in result["section_dynamics_automation"]
               if "(Other)" in t["source_key"] and t["kind"]=="comp"]
        self.assertEqual([t["ratio"] for t in other],[2,1])
        self.assertEqual(result["section_ending"]["tail_seconds"],3)
        self.assertEqual([t["width"] for t in result["section_width_automation"]
                          if "(Other)" in t["source_key"]],[95])

    def test_legacy_sheet_has_no_dynamics(self):
        changed=section_import.apply({"files":FILES,"sections":[]},
            "[Verse 0:00-0:10]\n{Other.pan:left.40}\n", "replace",10)
        self.assertEqual(changed["section_dynamics_automation"],[])

if __name__=="__main__":
    unittest.main()
