"""Compact spatial production cue grammar: parsing is not execution."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import production_cues


class CueTests(unittest.TestCase):
    def test_user_example(self):
        item=production_cues.parse_cue(
            "[Chorus 1:15-1:45 Vocal1:Expansive-Left Drums:Narrow-Right Bass:Moderate]")
        self.assertEqual("Chorus",item["section"]["kind"])
        self.assertEqual(75.0,item["section"]["start_seconds"])
        self.assertEqual(105.0,item["section"]["end_seconds"])
        self.assertEqual("expansive",item["spatial"][0]["width"])
        self.assertEqual("left",item["spatial"][0]["bias"])
        self.assertEqual("center",item["spatial"][2]["bias"])
        self.assertEqual("proposal",item["status"])

    def test_numbered_verse_and_empty_directives(self):
        item=production_cues.parse_cue("[Verse 2 0:20.25-0:48]")
        self.assertEqual(2,item["section"]["number"])
        self.assertEqual(20.25,item["section"]["start_seconds"])
        self.assertEqual([],item["spatial"])

    def test_unknown_track_and_unsafe_tokens(self):
        with self.assertRaisesRegex(ValueError,"Unknown track"):
            production_cues.compile_cues(
                ["[Chorus 1:15-1:45 Vocal1:Wide]"], known_tracks={"Vocals"})
        for expression in (
            "[Chorus 1:15-1:45 Vocals:IncrediblyWide]",
            "[Chorus 1:15-1:45 Vocals:Wide-Diagonal]",
            "[Chorus 1:15-1:45 Vocals:Wide Vocals:Narrow]",
            "[Chorus 1:45-1:15 Vocals:Wide]",
            "[Chorus 1:75-2:30 Vocals:Wide]",
            "[Chorus 1:15-1:45 Vocals:Wide;rm]",
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    production_cues.parse_cue(expression)


if __name__ == "__main__":
    unittest.main()
