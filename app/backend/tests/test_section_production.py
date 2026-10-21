import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import section_import
import section_production

FILES = [f"song ({name}).wav" for name in section_production.ALIASES]

class ProductionNotationTests(unittest.TestCase):
    def test_round_trip_and_inheritance(self):
        script = ("[Verse 1 0:00-0:10]\n{Other.pan:left.60@2s:smooth}\n"
                  "[Chorus 0:10-0:20]\n{Other.pan:right.60@2s:smooth}\n"
                  "[Verse 2 0:20-0:30]\n"
                  "[Bridge 0:30-0:40]\n{all.reset@2s:smooth}\n")
        project = {"sections": [], "files": FILES}
        result = section_import.apply(project, script, "replace", 40)
        self.assertEqual(len(result["section_pan_automation"]), 8)
        pan = [x["pan"] for x in result["section_pan_automation"] if "(Other)" in x["source_key"]]
        self.assertEqual(pan, [-0.6, 0.6, 0.0])
        project.update(result)
        rendered = section_import.render_tags(project)
        self.assertIn("{all.reset@2s:smooth}", rendered)
        self.assertEqual(section_import.apply(project, rendered, "replace", 40)["section_pan_automation"],
                         result["section_pan_automation"])

    def test_reverb_send_and_reset_round_trip(self):
        script = ("[Verse 0:00-0:10]\\n{Vocals.pan:left.30@2s:smooth Vocals.reverb:25@3s:smooth}\\n"
                  "[Chorus 0:10-0:20]\\n{Vocals.reverb:40@2s:smooth}\\n"
                  "[Outro 0:20-0:30]\\n{all.reset@2s:smooth}\\n")
        project = {"sections": [], "files": FILES}
        result = section_import.apply(project, script, "replace", 30)
        vocal = [item["wet"] for item in result["section_reverb_automation"]
                 if "(Vocals)" in item["source_key"]]
        self.assertEqual(vocal, [0.25, 0.4, 0.0])
        self.assertEqual(len(result["section_reverb_automation"]), 8)
        project.update(result)
        self.assertEqual(section_import.apply(project, section_import.render_tags(project),
                          "replace", 30)["section_reverb_automation"],
                         result["section_reverb_automation"])

    def test_fail_closed(self):
        with self.assertRaises(ValueError):
            section_production.parse_block("{Vocals.width:120@4s:smooth}")
        with self.assertRaises(ValueError):
            section_production.parse_block("{Other.pan:right.150}")
        with self.assertRaises(ValueError):
            section_production.parse_block("{Other.pan:center Other.pan:left.30}")

    def test_replace_clears_removed_instruction(self):
        project = {"sections": [], "files": FILES}
        project.update(section_import.apply(project, "[Chorus 0:00-0:10]\n{Other.pan:left.50}", "replace", 10))
        updated = section_import.apply(project, "[Chorus 0:00-0:10]", "replace", 10)
        self.assertFalse(updated["section_production"])
        self.assertFalse(updated["section_pan_automation"])

if __name__ == "__main__":
    unittest.main()
