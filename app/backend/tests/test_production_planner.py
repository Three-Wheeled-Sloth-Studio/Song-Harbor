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

    def sources(self):
        return [{"filename":"Other.wav","balanceDb":0.2,"widthDb":-28,
                 "correlation":.88,"hardPan":0,"channels":2},
                {"filename":"Guitar.wav","balanceDb":0.0,"widthDb":-60,
                 "correlation":1,"hardPan":0,"channels":2}]

    def test_draft_preserves_lyrics_id_timing_and_original_directives(self):
        project=self.project()
        original=copy.deepcopy(project)
        result=planner.generate(project,self.metrics(project),stereo_sources=self.sources())
        self.assertEqual(project,original)
        self.assertGreaterEqual(len(result["suggestions"]),1)
        self.assertIn("The signal begins",result["content"])
        self.assertIn("Now the chorus comes",result["content"])
        self.assertIn("Vocals.pan:left.30",result["content"])
        self.assertIn("Other.pan:right.35",result["content"])
        self.assertIn("Other.width:130",result["content"])
        processed=section_import.apply(project,result["content"],"replace",28)
        self.assertEqual(processed["sections"],project["sections"])
        self.assertEqual(processed["section_lyrics"],project["section_lyrics"])

    def test_authored_effects_are_protected_across_sections(self):
        project=self.project()
        # The Chorus explicitly establishes a width. Planner must not
        # insert a competing width in the Intro or later section.
        result=planner.generate(project,self.metrics(project),stereo_sources=[
            {"filename":"Other.wav","balanceDb":0.1,"widthDb":-17,
             "correlation":.8,"hardPan":0,"channels":2}])
        self.assertEqual(result["content"].count("Other.width:"),1)
        self.assertIn("Other.width:130",result["content"])
        self.assertEqual(result["content"].count("Other.pan:"),1)

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
        self.assertNotIn("Other.pan:left.",intro)
        self.assertNotIn("Other.pan:right.",intro.split("Other.pan:right.35")[0])

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
        self.assertIn("Other.space:",result["content"])
        self.assertIn("spatial reflections", " ".join(row["note"] for row in result["notes"]))

    def test_silent_section_metrics_are_valid(self):
        project=self.project()
        rows=self.metrics(project)
        rows[0].update({"rmsDbfs":-200,"peakDbfs":-200,"widthDb":-200})
        result=planner.generate(project,rows)
        self.assertIn("Quiet passage preserved", " ".join(row["note"] for row in result["notes"]))

    def test_distinct_mono_backing_sources_create_complementary_pan(self):
        project=self.project()
        project["files"].append("Guitar.wav")
        project["source_tracks"].append({"working_filename":"Guitar.wav","stem_alias":"Guitar"})
        # Remove explicit author controls only in this fixture.
        project["section_production"]={}
        sources=[{"filename":name,"balanceDb":0,"widthDb":-180,
                  "correlation":1,"hardPan":0,"channels":1}
                 for name in ("Other.wav","Guitar.wav")]
        result=planner.generate(project,self.metrics(project),stereo_sources=sources,
                                direction="movement",spatial=85,dynamics=75)
        self.assertIn("Other.pan:",result["content"])
        self.assertIn("Guitar.pan:",result["content"])
        self.assertIn("Other.space:",result["content"])
        self.assertIn("Guitar.space:",result["content"])
        self.assertIn("Other.duck:",result["content"])
        self.assertNotIn("Other.width:",result["content"])
        parsed=section_import.apply(project,result["content"],"replace",28)
        self.assertEqual(parsed["section_lyrics"],project["section_lyrics"])

    def test_existing_authored_pan_and_split_are_never_replaced(self):
        project=self.project()
        project["channel_children"]={"Other.wav":{"export":"some-file"}}
        result=planner.generate(project,self.metrics(project),stereo_sources=self.sources(),
                                direction="movement",spatial=100)
        self.assertEqual(result["content"].count("Other.pan:"),1)

    def test_silent_stem_not_spatialized(self):
        project=self.project()
        project["section_production"]={}
        source={"filename":"Other.wav","balanceDb":0,"widthDb":-180,
                "correlation":1,"hardPan":0,"channels":1,"rmsDbfs":-85}
        result=planner.generate(project,self.metrics(project),stereo_sources=[source],
                                direction="movement",spatial=100)
        self.assertNotIn("Other.pan:",result["content"])
        self.assertNotIn("Other.space:",result["content"])

    def test_section_stem_presence_controls_effects(self):
        project=self.project()
        project["section_production"]={}
        rows=self.metrics(project)
        ids=[row["id"] for row in project["sections"]]
        source={"filename":"Other.wav","balanceDb":0,"widthDb":-55,
                "correlation":1,"hardPan":0,"channels":2,"rmsDbfs":-20}
        observations=[
            {"sectionId":ids[0],"filename":"Other.wav","rmsDbfs":-92,
             "balanceDb":0,"widthDb":-55,"correlation":1,"coverage":1},
            {"sectionId":ids[1],"filename":"Other.wav","rmsDbfs":-16,
             "balanceDb":0,"widthDb":-55,"correlation":1,"coverage":1},
            {"sectionId":ids[1],"filename":"Vocals.wav","rmsDbfs":-19,
             "balanceDb":0,"widthDb":-35,"correlation":1,"coverage":1}
        ]
        result=planner.generate(project,rows,stereo_sources=[source],
                                section_stems=observations,direction="movement",
                                spatial=85,dynamics=80)
        intro=result["content"].split("[Chorus")[0]
        chorus=result["content"].split("[Chorus")[1]
        self.assertNotIn("Other.pan:",intro)
        self.assertIn("Other.pan:",chorus)
        self.assertIn("Other.space:",chorus)

    def test_missing_vocal_section_does_not_invent_ducking(self):
        project=self.project()
        project["section_production"]={}
        ids=[row["id"] for row in project["sections"]]
        source={"filename":"Other.wav","balanceDb":0,"widthDb":-60,
                "correlation":1,"hardPan":0,"channels":2,"rmsDbfs":-20}
        observations=[]
        for ident in ids:
            for filename,level in (("Other.wav",-20),("Vocals.wav",-100)):
                observations.append({"sectionId":ident,"filename":filename,
                   "rmsDbfs":level,"balanceDb":0,"widthDb":-60,
                   "correlation":1,"coverage":1})
        result=planner.generate(project,self.metrics(project),
                                stereo_sources=[source],section_stems=observations,
                                spatial=80,dynamics=85)
        self.assertNotIn("Other.duck:",result["content"])

    def test_split_child_duplicate_lanes_do_not_break_preview(self):
        project=self.project()
        project["section_production"]={}
        first=project["sections"][0]["id"]
        source={"filename":"Other.wav","balanceDb":0,"widthDb":-60,
                "correlation":1,"hardPan":0,"channels":2,"rmsDbfs":-18}
        row={"sectionId":first,"filename":"Other.wav","rmsDbfs":-18,
             "balanceDb":0,"widthDb":-55,"correlation":1,"coverage":1}
        result=planner.generate(project,self.metrics(project),
                                stereo_sources=[source],section_stems=[row,dict(row)])
        self.assertEqual(result["section_stem_count"],1)

    def test_authored_direction_from_explicit_notes_only(self):
        project=self.project()
        project["section_lyrics"][project["sections"][0]["id"]] = (
            "(female lead, intimate and restrained)\n" +
            "Lyrics say explosive, but that is not a stage direction"
        )
        result=planner.generate(project,self.metrics(project),spatial=70,
                                stereo_sources=self.sources())
        self.assertIn("Authored performance direction: intimate",
                      " ".join(item["note"] for item in result["notes"]))
        self.assertNotIn("Authored performance direction: expansive",
                         " ".join(item["note"] for item in result["notes"]))

    def test_reviewed_direction_is_explicit_and_preserves_lyrics(self):
        project=self.project()
        project["section_production"]={}
        ident=project["sections"][0]["id"]
        source={"filename":"Other.wav","balanceDb":0,"widthDb":-60,
                "correlation":1,"hardPan":0,"channels":2,"rmsDbfs":-22}
        original=copy.deepcopy(project)
        neutral=planner.generate(project,self.metrics(project),
                                 stereo_sources=[source],spatial=80)
        reviewed=planner.generate(project,self.metrics(project),
                                  stereo_sources=[source],spatial=80,
                                  reviewed_context={ident:{"tone":"ominous",
                                    "origin":"author","note":"Low and threatening"}})
        self.assertEqual(project,original)
        self.assertIn("Human-reviewed direction: ominous",
                      " ".join(row["note"] for row in reviewed["notes"]))
        self.assertNotIn("Human-reviewed direction:", 
                         " ".join(row["note"] for row in neutral["notes"]))
        self.assertEqual(reviewed["reviewed_sections"],1)
        self.assertEqual(section_import.apply(project,reviewed["content"],"replace",28)["section_lyrics"],
                         project["section_lyrics"])

    def test_unreviewed_model_claims_not_accepted(self):
        project=self.project()
        with self.assertRaisesRegex(ValueError,"Invalid reviewed direction"):
            planner.generate(project,self.metrics(project),reviewed_context={
                project["sections"][0]["id"]:{"tone":"guitar in A minor", "origin":"model"}})

    def test_role_aware_vocals_drums_bass_with_headroom_and_presence(self):
        project=self.project()
        project["files"].append("Drums.wav")
        project["source_tracks"].append({"working_filename":"Drums.wav","stem_alias":"Drums"})
        project["section_production"]={}
        rows=self.metrics(project)
        rows[1]["peakDbfs"]=-4.5
        sources=[
            {"filename":name,"balanceDb":0,"widthDb":-55,"correlation":1,
             "hardPan":0,"channels":2,"rmsDbfs":-18}
            for name in ("Other.wav","Vocals.wav","Bass.wav","Drums.wav")
        ]
        result=planner.generate(project,rows,stereo_sources=sources,
                                spatial=85,dynamics=85,direction="ominous")
        content=result["content"]
        self.assertIn("Vocals.reverb:",content)
        self.assertIn("Drums.comp:",content)
        self.assertIn("Bass.space:",content)
        self.assertNotIn("Vocals.pan:",content)
        self.assertNotIn("Bass.pan:",content)
        self.assertNotIn("Drums.pan:",content)
        self.assertEqual(section_import.apply(project,content,"replace",28)["section_lyrics"],
                         project["section_lyrics"])

    def test_silent_roles_and_authored_vocal_reverb_are_protected(self):
        project=self.project()
        project["files"].append("Drums.wav")
        project["source_tracks"].append({"working_filename":"Drums.wav","stem_alias":"Drums"})
        project["section_production"]={
            project["sections"][0]["id"]:
                section_production.parse_block("{Vocals.reverb:25@4s:smooth}")
        }
        sections=[x["id"] for x in project["sections"]]
        sources=[
            {"filename":name,"balanceDb":0,"widthDb":-55,"correlation":1,
             "hardPan":0,"channels":2,"rmsDbfs":-20}
            for name in ("Other.wav","Vocals.wav","Bass.wav","Drums.wav")
        ]
        evidence=[]
        for sid in sections:
            for name in ("Other.wav","Vocals.wav","Bass.wav","Drums.wav"):
                evidence.append({"sectionId":sid,"filename":name,"rmsDbfs":-85 if name=="Drums.wav" else -20,
                                 "balanceDb":0,"widthDb":-55,"correlation":1,"coverage":1})
        result=planner.generate(project,self.metrics(project),stereo_sources=sources,
                                section_stems=evidence,spatial=80,dynamics=80)
        self.assertEqual(result["content"].count("Vocals.reverb:"),1)
        self.assertNotIn("Drums.comp:",result["content"])
        self.assertNotIn("Drums.space:",result["content"])

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
        result=planner.generate(project,self.metrics(project),spatial=0,dynamics=0,stereo_sources=self.sources())
        self.assertEqual(result["suggestions"],[])
        self.assertEqual(section_import.render_tags(project),result["content"])


if __name__=="__main__":
    unittest.main()
