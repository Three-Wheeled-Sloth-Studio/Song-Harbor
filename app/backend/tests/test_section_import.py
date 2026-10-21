"""Timed section import, atomic rejection and retained spatial intentions."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import


class SectionImportTests(unittest.TestCase):
    def setUp(self):
        self.project={"sections":[],"section_spatial_proposals":{}}

    def test_readable_tags_and_spatial_metadata(self):
        text=(
            "[Verse 0:15-0:45]\n"
            "[Chorus 0:45-1:15 Vocal1:Expansive-Left Drums:Narrow-Right Bass:Moderate]"
        )
        data=section_import.apply(self.project,text,"replace",duration=130)
        self.assertEqual(2,data["imported_count"])
        self.assertEqual("Chorus",data["sections"][1]["kind"])
        chorus=data["sections"][1]["id"]
        self.assertEqual("expansive",data["section_spatial_proposals"][chorus][0]["width"])
        self.project.update({k:v for k,v in data.items() if k!="imported_count"})
        exported=section_import.render_tags(self.project)
        self.assertIn("Vocal1:Expansive-Left",exported)
        self.assertIn("Bass:Moderate",exported)

    def test_import_json_and_reimport_as_text(self):
        text='[Verse 1 0:05-0:20 Vocal1:Moderate]'
        data=section_import.apply(self.project,text,"replace",duration=60)
        self.project.update({k:v for k,v in data.items() if k!="imported_count"})
        serialized=json.dumps({"sections":data["sections"]})
        loaded=section_import.apply(self.project,serialized,"replace",duration=60)
        self.assertEqual(data["sections"],loaded["sections"])
        self.assertEqual(data["section_spatial_proposals"],loaded["section_spatial_proposals"])

    def test_append_only_adjacent_and_reject_overlap(self):
        first=section_import.apply(self.project,"[Verse 0:00-0:15]","replace",60)
        self.project.update({k:v for k,v in first.items() if k!="imported_count"})
        good=section_import.apply(self.project,"[Chorus 0:15-0:45]","append",60)
        self.assertEqual(2,len(good["sections"]))
        original=copy.deepcopy(self.project)
        for invalid in (
            "[Chorus 0:10-0:25]",
            "[Verse 0:50-1:30]",
            "[Chorus 0:20-0:10]",
            "[Chorus 0:20-0:40 Guitars:Expansive-Nowhere]",
            "[Verse]",
            "[Chorus 0:15-0:45] extra text",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    section_import.apply(self.project,invalid,"append",60)
                self.assertEqual(original,self.project)

    def test_validate_json_spatial(self):
        raw=json.dumps([{
            "kind":"Intro","start_seconds":0,"end_seconds":5,
            "spatial":[{"track_alias":"Vocals","width":"expansive","bias":"left"}]
        }])
        result=section_import.apply(self.project,raw,"replace",10)
        self.assertEqual(1,len(result["section_spatial_proposals"]))
        bad=raw.replace("expansive","expand")
        with self.assertRaises(ValueError):
            section_import.apply(self.project,bad,"replace",10)


if __name__=="__main__":
    unittest.main()
