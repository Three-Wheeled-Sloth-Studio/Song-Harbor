"""Planner preserves author intent and refuses ungrounded or stale proposals."""
import copy
import sys
import unittest
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import production_planner as planner
import section_import
import section_production


class ProductionPlannerTests(unittest.TestCase):
    def project(self):
        a,b=(uuid.uuid4().hex for _ in range(2))
        p={"sections":[
             {"id":a,"kind":"Intro","number":None,"start_seconds":0,"end_seconds":12},
             {"id":b,"kind":"Chorus","number":None,"start_seconds":12,"end_seconds":28}],
           "files":["Vocals.wav","Bass.wav","Other.wav"],
           "source_tracks":[
             {"working_filename":"Vocals.wav","stem_alias":"Vocals"},
             {"working_filename":"Bass.wav","stem_alias":"Bass"},
             {"working_filename":"Other.wav","stem_alias":"Other"}],
           "section_production":{
             a:section_production.parse_block("{Vocals.pan:left.30@4s:smooth Other.pan:right.35@5s:smooth}"),
             b:section_production.parse_block("{Other.width:130@6s:smooth}")},
           "section_lyrics":{a:"(distant voice)\nThe signal begins",b:"Now the chorus comes"}}
        return p

    def metrics(self,project,wide=False):
        return [{"sectionId":s["id"],"rmsDbfs":-19,"peakDbfs":-3,
                 "balanceDb":0.2,"widthDb":-4 if wide else -18,
                 "intensity":.5} for s in project["sections"]]

    def test_draft_preserves_lyrics_id_timing_and_original_directives(self):
        project=self.project()
        original=copy.deepcopy(project)
        result=planner.generate(project,self.metrics(project))
        self.assertEqual(project,original)
        self.assertEqual(len(result["suggestions"]),1)
        self.assertIn("The signal begins",result["content"])
        self.assertIn("Now the chorus comes",result["content"])
        self.assertIn("Vocals.pan:left.30",result["content"])
        self.assertIn("Other.pan:right.35",result["content"])
        self.assertIn("Other.width:130",result["content"])
        processed=section_import.apply(project,result["content"],"replace",28)
        self.assertEqual(processed["sections"],project["sections"])
        self.assertEqual(processed["section_lyrics"],project["section_lyrics"])

    def test_wide_mix_is_not_widened_more(self):
        project=self.project()
        result=planner.generate(project,self.metrics(project,wide=True))
        self.assertNotIn("Other.width:1",result["content"].split("[Chorus")[0])

    def test_protect_existing_stereo_source_differentiation(self):
        project=self.project()
        sources=[{"filename":"Other.wav","balanceDb":4.2,
                  "widthDb":-4.3,"correlation":.68,"hardPan":0}]
        result=planner.generate(project,self.metrics(project),stereo_sources=sources)
        intro=result["content"].split("[Chorus")[0]
        self.assertNotIn("Other.width:1",intro)
        self.assertIn("Existing stereo/channel separation protected",
                      " ".join(row["note"] for row in result["notes"]))

    def test_invalid_stereo_metrics_rejected(self):
        project=self.project()
        with self.assertRaisesRegex(ValueError,"Invalid source stereo"):
            planner.generate(project,self.metrics(project),stereo_sources=[
                {"filename":"Other.wav","balanceDb":float("nan"),
                 "widthDb":0,"correlation":0,"hardPan":0}])

    def test_near_mono_source_does_not_get_fake_width(self):
        project=self.project()
        sources=[{"filename":"Other.wav","balanceDb":0,
                  "widthDb":-200,"correlation":1,"hardPan":0,"channels":2}]
        result=planner.generate(project,self.metrics(project),stereo_sources=sources)
        self.assertNotIn("Other.width:1",result["content"])
        self.assertIn("Near-mono source", " ".join(row["note"] for row in result["notes"]))

    def test_silent_section_metrics_are_valid(self):
        project=self.project()
        rows=self.metrics(project)
        rows[0].update({"rmsDbfs":-200,"peakDbfs":-200,"widthDb":-200})
        result=planner.generate(project,rows)
        self.assertIn("Quiet passage preserved", " ".join(row["note"] for row in result["notes"]))

    def test_bad_metric_set_rejected(self):
        project=self.project()
        with self.assertRaisesRegex(ValueError,"every saved section"):
            planner.generate(project,self.metrics(project)[:1])
        with self.assertRaisesRegex(ValueError,"Invalid measured"):
            broken=self.metrics(project)
            broken[0]["rmsDbfs"]=float("nan")
            planner.generate(project,broken)

    def test_lyrics_preserved_with_empty_profile(self):
        project=self.project()
        result=planner.generate(project,self.metrics(project),spatial=0,dynamics=0)
        self.assertEqual(result["suggestions"],[])
        self.assertEqual(section_import.render_tags(project),result["content"])


if __name__=="__main__":
    unittest.main()
