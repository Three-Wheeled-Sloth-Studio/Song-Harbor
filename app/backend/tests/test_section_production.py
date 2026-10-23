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

    def test_16_custom_tracks_reverb_and_broadcast(self):
        files=[f"song (Synth_{i:02d}).wav" for i in range(1,17)]
        sheet=("[Verse 0:00-0:10]\\n"
               "{all.reverb:12 Synth_16.reverb:35 Synth_01.pan:right.20 "
               "Synth_15.gain:+1@2s:smooth}\\n"
               "[Outro 0:10-0:20]\\n{all.reset@2s:smooth}\\n")
        project={"sections":[],"files":files}
        changed=section_import.apply(project,sheet,"replace",20)
        sends=[x for x in changed["section_reverb_automation"]
               if x["section_id"]==changed["sections"][0]["id"]]
        self.assertEqual(len(sends),16)
        self.assertEqual(next(x["wet"] for x in sends
                              if "(Synth_16)" in x["source_key"]),.35)
        self.assertEqual(next(x["wet"] for x in sends
                              if "(Synth_01)" in x["source_key"]),.12)
        self.assertEqual(len(changed["section_reverb_automation"]),32)
        restored=section_import.apply({**project,**changed},
            section_import.render_tags({**project,**changed}),"replace",20)
        self.assertEqual(changed["section_reverb_automation"],
                         restored["section_reverb_automation"])

    def test_reverb_send_and_reset_round_trip(self):
        script = ("[Verse 0:00-0:10]\n{Vocals.pan:left.30@2s:smooth Vocals.reverb:25@3s:smooth}\n"
                  "[Chorus 0:10-0:20]\n{Vocals.reverb:40@2s:smooth}\n"
                  "[Outro 0:20-0:30]\n{all.reset@2s:smooth}\n")
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

    def test_final_section_fade_and_tail(self):
        script = ("[Verse 0:00-0:10]\n"
                  "[Outro 0:10-0:20]\n"
                  "{Vocals.reverb:40@2s:smooth Master.fade:6s:smooth Master.tail:3s}\n")
        project = {"sections": [], "files": FILES}
        result = section_import.apply(project, script, "replace", 20)
        self.assertEqual(result["section_ending"], {
            "fade_seconds": 6.0, "tail_seconds": 3.0, "curve": "smooth"})
        project.update(result)
        restored = section_import.apply(project, section_import.render_tags(project), "replace", 20)
        self.assertEqual(restored["section_ending"], result["section_ending"])
        self.assertEqual(len(restored["section_reverb_automation"]), 1)

    def test_ending_rejects_nonterminal_and_excessive_fade(self):
        for script in (
            "[Verse 0:00-0:10]\n{Master.fade:2s:smooth}\n[Outro 0:10-0:20]",
            "[Verse 0:00-0:10]\n[Outro 0:10-0:20]\n{Master.fade:12s:smooth}",
            "[Verse 0:00-0:10]\n[Outro 0:10-0:20]\n{Master.tail:11s}",
        ):
            with self.subTest(script=script), self.assertRaises(ValueError):
                section_import.apply({"sections": [], "files": FILES}, script, "replace", 20)

    def test_width_pan_reverb_inheritance_and_reset_roundtrip(self):
        script = ("[Intro 0:00-0:10]\n"
                  "{Vocals.pan:left.60@2s:smooth Vocals.width:140@2s:smooth Vocals.reverb:20@2s:smooth}\n"
                  "[Verse 0:10-0:20]\n"
                  "[Chorus 0:20-0:30]\n"
                  "{Vocals.width:150@2s:smooth Drums.width:120@2s:smooth}\n"
                  "[Outro 0:30-0:40]\n"
                  "{all.reset@2s:smooth Master.fade:6s:smooth Master.tail:3s}\n")
        project = {"sections": [], "files": FILES}
        result = section_import.apply(project, script, "replace", 40)
        vocal_width = [x["width"] for x in result["section_width_automation"]
                       if "(Vocals)" in x["source_key"]]
        self.assertEqual(vocal_width, [140, 150, 100])
        self.assertEqual(len(result["section_width_automation"]), 9)
        self.assertEqual(result["section_ending"]["tail_seconds"], 3)
        self.assertEqual(len([x for x in result["section_pan_automation"]
                              if "(Vocals)" in x["source_key"]]), 2)
        project.update(result)
        roundtrip = section_import.apply(project, section_import.render_tags(project),
                                         "replace", 40)
        self.assertEqual(roundtrip["section_width_automation"], result["section_width_automation"])

    def test_width_rejects_invalid_targets(self):
        for entry in ("{Vocals.width:151}", "{Vocals.width:-5}", "{Drums.width:wide}",
                      "{Vocals.width:120 Vocals.width:130}", "{Bass.width:200@2s:smooth}"):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                section_production.parse_block(entry)
        self.assertEqual(section_production.parse_block("{Vocals.width:0}")[0]["width"], 0)
        self.assertEqual(section_production.parse_block("{Vocals.width:100}")[0]["width"], 100)

    def test_space_send_inherits_and_resets(self):
        script = ("[Intro 0:00-0:10]\n"
                  "{Vocals.pan:left.40 Vocals.width:130 Vocals.space:20@2s:smooth}\n"
                  "[Chorus 0:10-0:20]\n{Vocals.space:35}\n"
                  "[Outro 0:20-0:30]\n"
                  "{all.reset@2s:smooth Master.fade:4s:smooth Master.tail:3s}\n")
        project={"sections":[],"files":FILES}
        result=section_import.apply(project,script,"replace",30)
        self.assertEqual([t["amount"] for t in result["section_space_automation"]
                          if "(Vocals)" in t["source_key"]],[20,35,0])
        self.assertEqual(len(result["section_space_automation"]),8)
        project.update(result)
        restored=section_import.apply(project,section_import.render_tags(project),"replace",30)
        self.assertEqual(restored["section_space_automation"],result["section_space_automation"])
        for invalid in ("{Vocals.space:41}","{Vocals.space:-1}","{Vocals.space:20 Vocals.space:25}"):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                section_production.parse_block(invalid)

    def test_real_full_spatial_sheet_reloads_with_ending(self):
        source = (Path(__file__).resolve().parents[3] / "docs" /
                  "qa-full-spatial-the-logo-and-the-maw.txt").read_text(encoding="utf-8")
        parsed = section_import.apply({"sections": [], "files": FILES}, source, "replace", 240)
        self.assertEqual(len(parsed["sections"]), 13)
        self.assertEqual(parsed["section_ending"]["fade_seconds"], 4)
        self.assertEqual(parsed["section_ending"]["tail_seconds"], 3)
        self.assertTrue(parsed["section_space_automation"])
        self.assertTrue(parsed["section_width_automation"])
        project = {"files": FILES, **parsed}
        exported = section_import.render_tags(project)
        self.assertIn("Master.fade:4s:smooth", exported)
        self.assertIn("Master.tail:3s", exported)
        restored = section_import.apply(project, exported, "replace", 240)
        self.assertEqual(restored["section_space_automation"], parsed["section_space_automation"])
        self.assertEqual(restored["section_width_automation"], parsed["section_width_automation"])
        self.assertEqual(restored["section_ending"], parsed["section_ending"])
        self.assertEqual(restored["section_lyrics"], parsed["section_lyrics"])

    def test_parametric_eq_multiple_bands_and_round_trip(self):
        sheet=("[Verse 0:00-0:10]\n"
               "{Vocals.eq1:320,1.2,-2@2s:smooth Vocals.eq2:3200,2,+2.5@3s:linear "
               "Vocals.pan:left.20 Vocals.width:125}\n"
               "[Chorus 0:10-0:20]\n{Vocals.eq1:320,1.2,+1}\n"
               "[Outro 0:20-0:30]\n{all.reset Master.fade:4s:smooth Master.tail:3s}\n")
        project={"sections":[],"files":FILES}
        result=section_import.apply(project,sheet,"replace",30)
        gains=[(d["band"],d["gain_db"]) for d in result["section_eq_automation"]
               if "(Vocals)" in d["source_key"]]
        self.assertEqual(gains[:3],[(1,-2.0),(2,2.5),(1,1.0)])
        self.assertEqual(gains[-3:],[(1,0.0),(2,0.0),(3,0.0)])
        self.assertEqual(result["section_ending"]["tail_seconds"],3)
        project.update(result)
        exported=section_import.render_tags(project)
        self.assertIn("Vocals.eq1:320,1.2,-2@2s:smooth",exported)
        self.assertEqual(section_import.apply(project,exported,"replace",30)["section_eq_automation"],
                         result["section_eq_automation"])

    def test_parametric_eq_invalid_values(self):
        for block in ("{Vocals.eq1:20,1,-2}","{Vocals.eq4:1000,1,-2}",
                      "{Vocals.eq1:1000,0.1,-2}","{Vocals.eq1:1000,1,-13}",
                      "{Vocals.eq1:1000,1,+1 Vocals.eq1:2000,1,+2}"):
            with self.subTest(block=block),self.assertRaises(ValueError):
                section_production.parse_block(block)

    def test_fail_closed(self):
        with self.assertRaises(ValueError):
            section_production.parse_block("{Vocals.width:151@4s:smooth}")
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
