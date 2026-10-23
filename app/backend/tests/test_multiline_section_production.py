"""Multiline/CRLF production scripting remains compatible with single-line sheets."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import
import section_production

FILES=["track (Other).wav","track (Vocals).wav"]
SHEET=("[Intro 0:00-0:10]\n"
       "{Other.pan:right.30@2s:smooth Other.reverb:18@2s:smooth "
       "Other.eq1:380,1,+1@2s:smooth}\n"
       "Original lyric line\n"
       "[Chorus 0:10-0:20]\n"
       "{Other.evolve:menacing@5s:smooth Vocals.width:80@2s:smooth}\n"
       "Second lyric line\n")

class MultilineSectionTests(unittest.TestCase):
    def setUp(self):
        self.project={"files":FILES,"sections":[]}

    def test_equivalent_space_lf_crlf_and_mixed_whitespace(self):
        baseline=section_import.apply(self.project,SHEET,"replace",20)
        for newline in ("\n","\r\n"):
            spaced=(SHEET.replace("{Other.pan:right.30@2s:smooth Other.reverb:18@2s:smooth "
                "Other.eq1:380,1,+1@2s:smooth}",
                "{\nOther.pan:right.30@2s:smooth\n  Other.reverb:18@2s:smooth\n\n"
                "  Other.eq1:380,1,+1@2s:smooth\n}")
                .replace("{Other.evolve:menacing@5s:smooth Vocals.width:80@2s:smooth}",
                         "{ Other.evolve:menacing@5s:smooth\nVocals.width:80@2s:smooth }")
                .replace("\n",newline))
            with self.subTest(newline=repr(newline)):
                actual=section_import.apply(self.project,spaced,"replace",20)
                self.assertEqual(
                    [[{k:v for k,v in d.items() if k!="version"} for d in directives]
                     for directives in actual["section_production"].values()],
                    [[{k:v for k,v in d.items() if k!="version"} for d in directives]
                     for directives in baseline["section_production"].values()])
                self.assertEqual(sorted(actual["section_lyrics"].values()),
                                 sorted(baseline["section_lyrics"].values()))
                self.assertEqual(actual["section_reverb_automation"],
                                 [{**x,"section_id":actual["sections"][0]["id"]}
                                  for x in baseline["section_reverb_automation"]
                                  if x["section_id"]==baseline["sections"][0]["id"]]
                                 + [{**x,"section_id":actual["sections"][1]["id"]}
                                  for x in baseline["section_reverb_automation"]
                                  if x["section_id"]==baseline["sections"][1]["id"]])

    def test_export_stays_multiline_and_reimports_with_same_effects_and_lyrics(self):
        first=section_import.apply(self.project,SHEET,"replace",20)
        saved={**self.project,**first}
        exported=section_import.render_tags(saved)
        self.assertIn("{\n  Other.pan:",exported)
        self.assertIn("\n  Other.reverb:",exported)
        self.assertIn("\n}\nOriginal lyric line",exported)
        again=section_import.apply(saved,exported,"replace",20)
        self.assertEqual(first["section_reverb_automation"],again["section_reverb_automation"])
        self.assertEqual(first["section_eq_automation"],again["section_eq_automation"])
        self.assertEqual(first["section_lyrics"],again["section_lyrics"])
        self.assertEqual(first["section_production"],again["section_production"])

    def test_reject_open_nested_or_duplicate_blocks_without_treating_as_lyrics(self):
        for sheet, line in (
            ("[Intro 0:00-0:20]\n{\n Other.pan:left.20\n[Chorus]",4),
            ("[Intro 0:00-0:20]\n{\n Other.pan:left.20",2),
            ("[Intro 0:00-0:20]\n{\n{Other.pan:left.20}\n}",3),
            ("[Intro 0:00-0:20]\n{Other.pan:left.20}\n}",3),
            ("[Intro 0:00-0:20]\n{Other.pan:left.20}\n{Other.reverb:20}",4),
        ):
            with self.subTest(sheet=sheet):
                with self.assertRaisesRegex(ValueError,rf"Line {line}:"):
                    section_import.apply(self.project,sheet,"replace",20)
                self.assertEqual(self.project,{"files":FILES,"sections":[]})

    def test_clickable_error_location_for_bad_directive(self):
        sheet=("[Intro 0:00-0:20]\n{\nOther.pan:left.20\n"
               "Nonexistent.mystery:99\n}\n")
        with self.assertRaisesRegex(ValueError,r"Line 4: Unsupported production directive"):
            section_import.apply(self.project,sheet,"replace",20)

    def test_single_directive_still_renders_compact(self):
        block=section_production.parse_block("{Vocals.reverb:18@2s:smooth}")
        self.assertEqual(section_production.render_block(block),
                         "{Vocals.reverb:18@2s:smooth}")

if __name__=="__main__":unittest.main()
