import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import,track_lifecycle

FILES=["01 (Vocals).wav","02 (Cello_Accent).wav","03 (Drums).wav"]
class TrackLifecycleTests(unittest.TestCase):
    def sample(self):
        project={"files":list(FILES),"source_duration_seconds":20,"source_tracks":[
            {"track_id":"trk0001","stem_alias":"Vocals","display_name":"Vocals","working_filename":FILES[0]},
            {"track_id":"trk0002","stem_alias":"Cello_Accent","display_name":"Cello","working_filename":FILES[1]},
            {"track_id":"trk0003","stem_alias":"Drums","display_name":"Drums","working_filename":FILES[2]}]}
        changed=section_import.apply(project,
            "[Verse 0:00-0:10]\n{Cello_Accent.pan:right.25@2s:smooth Cello_Accent.gain:+1.5 "
            "Cello_Accent.reverb:20 Cello_Accent.eq1:1000,1,+1}\nA cello phrase\n"
            "[Chorus 0:10-0:20]\n{all.reverb:10 Cello_Accent.width:115}\n",
            "replace",20)
        project.update(changed)
        return project

    def test_rename_updates_directives_but_never_source_identity(self):
        original=self.sample()
        before=copy.deepcopy(original)
        renamed=track_lifecycle.rename(original,"trk0002","CounterCello","Counter Cello")
        self.assertEqual(original,before)
        self.assertEqual(renamed["files"],FILES)
        source=next(x for x in renamed["source_tracks"] if x["track_id"]=="trk0002")
        self.assertEqual(source["working_filename"],FILES[1])
        self.assertEqual(source["stem_alias"],"CounterCello")
        text=section_import.render_tags(renamed)
        self.assertIn("CounterCello.pan:",text)
        self.assertIn("CounterCello.gain:",text)
        self.assertIn("CounterCello.reverb:",text)
        self.assertIn("CounterCello.eq1:",text)
        self.assertIn("CounterCello.width:",text)
        self.assertNotIn("Cello_Accent.",text)
        self.assertIn("A cello phrase",text)
        for key in ("section_pan_automation","section_gain_automation",
                    "section_reverb_automation","section_eq_automation",
                    "section_width_automation"):
            self.assertTrue(any(x["source_key"]==FILES[1] for x in renamed[key]),key)

    def test_alias_collisions_and_bad_name_fail_closed(self):
        before=self.sample()
        for alias in ("Vocals","vocals","auto","Master","all","bad name","1Cello","bad.alias"):
            with self.subTest(alias=alias),self.assertRaises(ValueError):
                track_lifecycle.rename(before,"trk0002",alias,"New cello")
        self.assertTrue(any(d["track"]=="Cello_Accent"
                            for ds in before["section_production"].values() for d in ds))
        with self.assertRaises(ValueError):
            track_lifecycle.rename(before,"not-a-track","CelloNew","Cello")

    def test_replacement_lifecycle_preserves_script_and_restores_region(self):
        project=self.sample()
        clip="trk_replace (CelloTake).wav"
        project["files"].append(clip)
        project.setdefault("stems",[]).append({"filename":clip,"gain":1,"mute":False,"solo":False})
        project["source_tracks"].append({"track_id":"trk_replace","stem_alias":"CelloTake",
            "display_name":"Cello take","working_filename":clip,"original_filename":"trk_take.wav",
            "imported":True,"start_seconds":6.0,"duration_seconds":4.0})
        project["replacement_masks"]=[{
            "replacement_track_id":"trk_replace","source_track_id":"trk0002",
            "source_filename":FILES[1],"start_seconds":6.0,"end_seconds":10.0,"fade_seconds":.05}]
        original=copy.deepcopy(project)
        with self.assertRaisesRegex(ValueError,"replacement"):
            track_lifecycle.position(project,"trk_replace",8,20)
        moved=track_lifecycle.rename(project,"trk0002","OrchestraCello","Orchestra Cello")
        self.assertEqual(moved["replacement_masks"],original["replacement_masks"])
        self.assertEqual(project,original)
        removed,_=track_lifecycle.remove(project,"trk_replace")
        self.assertEqual(removed["replacement_masks"],[])
        self.assertEqual(project,original)
        self.assertEqual(removed["section_gain_automation"],original["section_gain_automation"])
        self.assertEqual(removed["section_pan_automation"],original["section_pan_automation"])

    def test_stable_id_legacy_backfill(self):
        project={"files":FILES}
        first=track_lifecycle.ensure_identities(project)
        self.assertEqual(len(first),3)
        self.assertEqual({x["stem_alias"] for x in first},{"Vocals","Drums","Cello_Accent"})
        self.assertEqual(len({x["track_id"] for x in first}),3)

    def test_position_and_remove_apply_only_to_imported_clips(self):
        project=self.sample()
        clip="trk_clip (CelloTake).wav"
        project["files"].append(clip)
        project.setdefault("stems",[]).append({"filename":clip,"gain":1,"mute":False,"solo":False})
        project["source_tracks"].append({"track_id":"trk_clip","stem_alias":"CelloTake",
            "display_name":"Cello take","working_filename":clip,"original_filename":"trk_clip_take.wav",
            "imported":True,"start_seconds":0,"duration_seconds":4.25})
        moved=track_lifecycle.position(project,"trk_clip",11.719,20)
        self.assertEqual(11.719,next(x for x in moved["source_tracks"] if x["track_id"]=="trk_clip")["start_seconds"])
        with self.assertRaises(ValueError):track_lifecycle.position(project,"trk_clip",18,20)
        with self.assertRaises(ValueError):track_lifecycle.position(project,"trk0001",1,20)
        removed,identity=track_lifecycle.remove(moved,"trk_clip")
        self.assertEqual("CelloTake",identity["stem_alias"])
        self.assertNotIn(clip,removed["files"])
        self.assertFalse(any(x.get("track_id")=="trk_clip" for x in removed["source_tracks"]))
        with self.assertRaises(ValueError):track_lifecycle.remove(project,"trk0001")

if __name__=="__main__":
    unittest.main()
