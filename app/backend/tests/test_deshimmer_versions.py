"""Versioned Deshimmer accept must not rename primary stems or rewrite automation."""
from __future__ import annotations
import copy
import sys
import tempfile
import unittest
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import deshimmer_versions as versions

def wav(path:Path,amplitude:int):
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(48000)
        frame=int(amplitude).to_bytes(2,"little",signed=True)*2
        f.writeframes(frame*4800)

class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.project={
            "id":"abcdef123456",
            "files":["song (Vocals).wav"],
            "source_tracks":[{"track_id":"trk_vocals","working_filename":"song (Vocals).wav",
                "original_filename":"song (Vocals).wav","stem_alias":"Vocals",
                "display_name":"Vocals","imported":False}],
            "stems":[{"filename":"song (Vocals).wav","gain":0.74,"mute":False,"solo":False}],
            "section_production":{"abc":[{"track":"Vocals","kind":"width","value":120}]},
            "replacement_masks":[]
        }
        self.source=self.root/"jobs"/self.project["id"]/"stems"/self.project["files"][0]
        self.candidate=self.root/"candidate.wav"
        wav(self.source,1000)
        wav(self.candidate,2000)
        self.original_hash=versions.digest(self.source)
        self.saved=None
    def save(self,project):
        self.saved=copy.deepcopy(project)
    def test_accept_retains_alias_script_gain_and_file_count(self):
        result=versions.adopt(self.root,self.project,self.project["files"][0],
                              self.candidate,self.original_hash,"cand_a",self.save)
        self.assertEqual(result["source_tracks"],self.project["source_tracks"])
        self.assertEqual(result["stems"],self.project["stems"])
        self.assertEqual(result["files"],self.project["files"])
        self.assertEqual(result["section_production"],self.project["section_production"])
        self.assertEqual(result["replacement_masks"],[])
        self.assertEqual(versions.digest(self.source),versions.digest(self.candidate))
        self.assertEqual(len(result["stem_cleanup_versions"]),1)
        self.assertEqual(result,self.saved)
    def test_undo_restores_original_and_script(self):
        result=versions.adopt(self.root,self.project,self.project["files"][0],
                              self.candidate,self.original_hash,"cand_a",self.save)
        restored=versions.undo(self.root,result,self.project["files"][0],self.save)
        self.assertEqual(versions.digest(self.source),self.original_hash)
        self.assertEqual(restored["source_tracks"],self.project["source_tracks"])
        self.assertEqual(restored["section_production"],self.project["section_production"])
        self.assertFalse(restored["stem_cleanup_versions"])
    def test_accept_save_failure_rolls_back_audio(self):
        def fail(_):raise RuntimeError("manifest refused")
        with self.assertRaisesRegex(RuntimeError,"manifest refused"):
            versions.adopt(self.root,self.project,self.project["files"][0],
                           self.candidate,self.original_hash,"cand_a",fail)
        self.assertEqual(versions.digest(self.source),self.original_hash)
    def test_rejects_split_active_and_existing_replacement(self):
        x=copy.deepcopy(self.project)
        x["channel_children"]={self.project["files"][0]:{"active":True}}
        with self.assertRaisesRegex(ValueError,"split"):
            versions.adopt(self.root,x,x["files"][0],self.candidate,self.original_hash,"a",self.save)
        x=copy.deepcopy(self.project)
        x["replacement_masks"]=[{"source_filename":x["files"][0]}]
        with self.assertRaisesRegex(ValueError,"replacement"):
            versions.adopt(self.root,x,x["files"][0],self.candidate,self.original_hash,"a",self.save)
    def test_stale_source_rejected(self):
        wav(self.source,3500)
        with self.assertRaisesRegex(ValueError,"changed"):
            versions.adopt(self.root,self.project,self.project["files"][0],
                           self.candidate,self.original_hash,"a",self.save)
    def test_undo_save_failure_restores_accepted_audio(self):
        result=versions.adopt(self.root,self.project,self.project["files"][0],
                              self.candidate,self.original_hash,"cand_a",self.save)
        accepted_hash=versions.digest(self.source)
        def fail(_):raise RuntimeError("manifest refused")
        with self.assertRaisesRegex(RuntimeError,"manifest refused"):
            versions.undo(self.root,result,self.project["files"][0],fail)
        self.assertEqual(versions.digest(self.source),accepted_hash)

if __name__=="__main__":unittest.main()
