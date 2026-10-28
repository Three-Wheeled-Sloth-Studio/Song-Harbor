import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lyric_captions import render_srt, validate_srt

class LyricCaptionTests(unittest.TestCase):
    def test_even_spacing_section_boundary_and_chunking(self):
        project={
          "sections":[
            {"id":"a","kind":"Verse","start_seconds":0,"end_seconds":8},
            {"id":"b","kind":"Chorus","start_seconds":8,"end_seconds":12}
          ],
          "section_lyrics":{
            "a":"(whispered)\nFirst lyric line\nSecond lyric line\nThird lyric line\nFourth lyric line",
            "b":"Short one\nShort two\nShort three\n"
          }
        }
        result=render_srt(project)
        self.assertEqual(result["excluded_directions"],1)
        self.assertEqual(result["cue_count"],3)
        self.assertIn("00:00:00,000 --> 00:00:04,000\nFirst lyric line\nSecond lyric line",result["content"])
        self.assertIn("00:00:04,000 --> 00:00:08,000\nThird lyric line\nFourth lyric line",result["content"])
        self.assertIn("00:00:08,000 --> 00:00:12,000\nShort one\nShort two\nShort three",result["content"])

    def test_long_line_gets_own_caption_and_empty_sections_skipped(self):
        very_long="This is an intentionally extensive lyric that cannot fit with another line inside a single cue"
        result=render_srt({"sections":[
            {"id":"a","kind":"Intro","start_seconds":0,"end_seconds":3},
            {"id":"b","kind":"Verse","start_seconds":3,"end_seconds":9}
          ],"section_lyrics":{"a":"(instrumental)","b":very_long+"\nAnd another line"}})
        self.assertEqual(result["cue_count"],2)
        self.assertIn("00:00:03,000 --> 00:00:06,000",result["content"])
        self.assertIn("00:00:06,000 --> 00:00:09,000",result["content"])

    def test_raises_on_missing_lyrics(self):
        with self.assertRaises(ValueError):
            render_srt({"sections":[{"id":"a","kind":"Intro","start_seconds":0,"end_seconds":5}],
                        "section_lyrics":{"a":"(instrumental)"}})

    def test_export_is_deterministic_and_does_not_mutate_project(self):
        project={"sections":[{"id":"a","kind":"Outro","start_seconds":60.25,"end_seconds":66.25}],
                 "section_lyrics":{"a":"One\nTwo"}}
        before=repr(project)
        first=render_srt(project)
        self.assertEqual(first,render_srt(project))
        self.assertEqual(before,repr(project))
        self.assertIn("00:01:00,250",first["content"])
    def test_persisted_manual_alignment_is_exported_unchanged(self):
        saved = "1\\n00:00:01,250 --> 00:00:02,800\\nHello\\nThere\\n"
        project = {"source_duration_seconds": 10, "lyric_srt_override": saved,
                   "sections": [], "section_lyrics": {}}
        validate_srt(saved, 10)
        result = render_srt(project)
        self.assertEqual(result["content"], saved)
        self.assertEqual(result["cue_count"], 1)

    def test_invalid_manual_timing_rejected(self):
        first = "1\\n00:00:01,000 --> 00:00:03,000\\nHello\\n"
        for extra in (
            "2\\n00:00:02,500 --> 00:00:04,000\\nOverlap",
            "2\\n00:00:04,000 --> 00:00:11,000\\nToo late",
            "2\\n00:00:04,000 --> 00:00:05,000\\nOne\\nTwo\\nThree\\nFour",
        ):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_srt(first + "\\n" + extra, 10)

if __name__=="__main__":
    unittest.main()
