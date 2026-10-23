"""Menacing spatial macro preserves intent and resolves existing DSP automation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import section_import
import section_production

FILE="01 (Other).wav"
def song(split=False):
    return {"files":[FILE],"source_duration_seconds":40,"source_tracks":[{
        "working_filename":FILE,"stem_alias":"Other",
        "track_id":"test-other","display_name":"Other"}],
        "channel_children":{FILE:{"export":"Channels-test","active":True}} if split else {}}

class EvolutionMacroTests(unittest.TestCase):
    def test_roundtrip_intent_and_parent_effects(self):
        doc="[Intro 0:00-0:20]\n{Other.evolve:menacing@20s:smooth}\n[Chorus 0:20-0:40]\n"
        result=section_import.apply(song(),doc,"replace",40)
        self.assertEqual(result["section_production"][result["sections"][0]["id"]][0]["kind"],"evolve")
        self.assertIn("Other.evolve:menacing@20s:smooth",section_import.render_tags(
            {**song(),**result}))
        self.assertTrue(any(t["source_key"]==FILE and t["wet"]==.16
                            and t["transition_seconds"]==20
                            for t in result["section_reverb_automation"]))
        self.assertTrue(any(t["source_key"]==FILE and t["width"]==125
                            for t in result["section_width_automation"]))
        self.assertTrue(any(t["source_key"]==FILE for t in result["section_space_automation"]))

    def test_child_spatial_asymmetry_and_explicit_override(self):
        doc=("[Intro 0:00-0:20]\n"
             "{Other.evolve:menacing@20s:smooth Other-right.reverb:18@2s:smooth "
             "Other.eq1:400,1,+0.5@2s:smooth}\n[Chorus 0:20-0:40]\n")
        result=section_import.apply(song(True),doc,"replace",40)
        reverb=result["section_reverb_automation"]
        self.assertTrue(any(t["source_key"]==FILE+":left" and t["wet"]==.11 for t in reverb))
        self.assertTrue(any(t["source_key"]==FILE+":right" and t["wet"]==.18 for t in reverb))
        self.assertFalse(any(t["source_key"]==FILE+":right" and t["wet"]==.23 for t in reverb))
        parent_eq1=[t for t in result["section_eq_automation"] if t["source_key"]==FILE and t["band"]==1]
        self.assertEqual(len(parent_eq1),1)
        self.assertEqual(parent_eq1[0]["frequency"],400)
        self.assertTrue(any(t["source_key"]==FILE+":right" and t["band"]==2
                            for t in result["section_eq_automation"]))

    def test_fail_closed(self):
        for value in ("Other.evolve:menacing@35s:smooth",
                      "Ghost.evolve:menacing@20s:smooth",
                      "Other.evolve:cheerful@20s:smooth"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    section_import.apply(song(),f"[Intro 0:00-0:40]\n{{{value}}}\n",
                                         "replace",40)

if __name__=="__main__":unittest.main()
