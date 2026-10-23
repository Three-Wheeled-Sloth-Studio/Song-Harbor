"""Independent channel automation under stable parent stem identity."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import
import section_production
import track_lifecycle

FILES=["01 (Drums).wav","02 (Vocals).wav"]
def project():
    return {"files":FILES,"source_duration_seconds":20,
            "channel_children":{FILES[0]:{"export":"Channels-test","active":True}},
            "source_tracks":[{"working_filename":FILES[0],"stem_alias":"Drums",
                              "track_id":"trk1","display_name":"Drums"},
                             {"working_filename":FILES[1],"stem_alias":"Vocals",
                              "track_id":"trk2","display_name":"Vocals"}]}

class ChildChannelAutomationTests(unittest.TestCase):
    def test_independent_child_effects_and_parent_broadcast(self):
        original=project()
        script=("[Verse 0:00-0:10]\n"
                "{all.reverb:10@2s:smooth Drums-right.reverb:18@2s:smooth "
                "Drums-left.gain:-0.75@2s:smooth Drums-right.eq1:1000,1,-2 "
                "Drums-left.pan:left.80@2s:smooth}\n"
                "[Chorus 0:10-0:20]\n{Drums.reverb:20@2s:smooth}\n")
        changed=section_import.apply(original,script,"replace",20)
        self.assertEqual(original,project())
        targets=changed["section_reverb_automation"]
        self.assertTrue(any(t["source_key"]==FILES[0]+":right" and t["wet"]==.18 for t in targets))
        self.assertTrue(any(t["source_key"]==FILES[0] and t["wet"]==.1 for t in targets))
        self.assertFalse(any(t["source_key"]==FILES[0]+":left" for t in targets))
        self.assertTrue(any(t["source_key"]==FILES[0]+":left" for t in changed["section_gain_automation"]))
        self.assertTrue(any(t["source_key"]==FILES[0]+":right" for t in changed["section_eq_automation"]))
        self.assertTrue(any(t["source_key"]==FILES[0]+":left" for t in changed["section_pan_automation"]))
        self.assertFalse(any(t["source_key"].startswith(FILES[1]+":") for t in targets))

    def test_child_target_requires_split_and_rejects_unsupported_processors(self):
        base=project()
        base["channel_children"]={}
        with self.assertRaisesRegex(ValueError,"Unknown stem"):
            section_import.apply(base,"[Verse 0:00-0:20]\n{Drums-right.reverb:18}\n",
                                 "replace",20)
        base=project()
        with self.assertRaisesRegex(ValueError,"Child split channels currently support"):
            section_import.apply(base,"[Verse 0:00-0:20]\n{Drums-right.width:120}\n",
                                 "replace",20)

    def test_parent_rename_updates_child_aliases_and_keeps_source_keys(self):
        base=project()
        base["sections"]=[]
        changed=section_import.apply(base,
           "[Verse 0:00-0:20]\n{Drums-left.gain:-1 Drums-right.reverb:18 Drums.pan:center}\n",
           "replace",20)
        base.update(changed)
        renamed=track_lifecycle.rename(base,"trk1","Percussion","Percussion")
        text=section_import.render_tags(renamed)
        self.assertIn("Percussion-left.gain:",text)
        self.assertIn("Percussion-right.reverb:",text)
        self.assertNotIn("Drums-right.",text)
        self.assertTrue(any(t["source_key"]==FILES[0]+":right"
                            for t in renamed["section_reverb_automation"]))
        self.assertEqual(renamed["files"],FILES)

if __name__=="__main__":
    unittest.main()
