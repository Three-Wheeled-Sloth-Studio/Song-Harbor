"""Derived stereo child routing is exclusive, persistent and tamper-resistant."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import projects
import track_routing

class Setting:
    def __init__(self,filename,gain=1.0,mute=False,solo=False):
        self.filename=filename;self.gain=gain;self.mute=mute;self.solo=solo

class TrackRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ident="abcdef012345"
        self.folder=self.root/"jobs"/self.ident
        stems=self.folder/"stems"
        stems.mkdir(parents=True)
        self.files=[]
        for name in projects.ORDER:
            filename="source_("+name+")_htdemucs_6s.wav"
            (stems/filename).write_bytes(name.encode())
            self.files.append(filename)
        self.song={"version":1,"id":self.ident,"files":self.files,
                   "title":"Song","filename":"source.wav","source_filename":"source.wav",
                   "stems":projects.default_settings(self.files)}
        projects.write_project(self.root,self.song)
        self.recording={p.name:p.read_bytes() for p in stems.iterdir()}
        self.export=self.folder/"exports"/"Channels-test"
        self.export.mkdir(parents=True)
        self.track=self.files[0]
        self.export.joinpath("01 - Vocals - Left.wav").write_bytes(b"left")
        self.export.joinpath("01 - Vocals - Right.wav").write_bytes(b"right")
        self.export.joinpath("manifest.json").write_text(json.dumps({
            "source_project_id":self.ident,
            "tracks":[
                {"source":self.track,"channel":"left","file":"01 - Vocals - Left.wav"},
                {"source":self.track,"channel":"right","file":"01 - Vocals - Right.wav"}
            ]
        }))

    def test_route_replaces_parent_and_restores(self):
        chosen=track_routing.attach(self.root,self.song,self.export,[self.track])
        self.assertTrue(chosen[self.track]["active"])
        settings=[Setting(x) for x in self.files]
        mixed=track_routing.audio_inputs(self.root,self.song,settings)
        self.assertEqual(7,len(mixed))
        self.assertNotIn(self.folder/"stems"/self.track,[path for path,_,_ in mixed])
        self.assertEqual(["left","right"],[channel for _,_,channel in mixed[:2]])
        self.assertEqual([1.0,1.0],[gain for _,gain,_ in mixed[:2]])
        reopened=projects.read_project(self.root,self.ident)
        self.assertTrue(track_routing.valid_children(self.root,reopened)[self.track]["active"])
        track_routing.switch(self.root,reopened,self.track,False)
        restored=projects.read_project(self.root,self.ident)
        self.assertEqual(6,len(track_routing.audio_inputs(self.root,restored,settings)))
        self.assertEqual("stereo",track_routing.audio_inputs(self.root,restored,settings)[0][2])
        self.assertEqual(self.recording,{p.name:p.read_bytes() for p in (self.folder/"stems").iterdir()})

    def test_muted_parent_mutes_children_together(self):
        track_routing.attach(self.root,self.song,self.export,[self.track])
        settings=[Setting(x,mute=(x==self.track)) for x in self.files]
        routed=track_routing.audio_inputs(self.root,self.song,settings)
        self.assertEqual([0.0,0.0],[gain for _,gain,_ in routed[:2]])

    def test_missing_or_tampered_export_is_not_active(self):
        track_routing.attach(self.root,self.song,self.export,[self.track])
        self.export.joinpath("01 - Vocals - Left.wav").unlink()
        self.assertNotIn(self.track,track_routing.valid_children(self.root,self.song))
        routed=track_routing.audio_inputs(self.root,self.song,[Setting(x) for x in self.files])
        self.assertEqual(6,len(routed))
        self.assertEqual("stereo",routed[0][2])
        self.assertRaises(ValueError,track_routing.child_path,self.root,self.song,self.track,"left")

    def test_reject_invalid_source_or_export(self):
        with self.assertRaises(ValueError):
            track_routing.attach(self.root,self.song,self.export,["not-a-stem.wav"])
        with self.assertRaises(ValueError):
            track_routing.switch(self.root,self.song,"../hidden.wav",True)
        with self.assertRaises(ValueError):
            track_routing.attach(self.root,self.song,self.root, [self.track])

if __name__=="__main__":
    unittest.main()
