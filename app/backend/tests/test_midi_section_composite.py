"""Consolidated MIDI section WAV and multi-mask regression tests.

These use tiny synthetic PCM fixtures, no sfizz, FFmpeg or cloud assets.
"""
from __future__ import annotations
import sys
import tempfile
import unittest
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_section_composite
import section_import
import track_lifecycle

RATE=48000

def wav(path:Path,frames:int,amplitude:int=1000):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE)
        payload=amplitude.to_bytes(2,"little",signed=True)*2
        for _ in range(0,frames,4096):
            w.writeframesraw(payload*min(4096,frames-_))
        w.writeframes(b"")


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)

    def test_disjoint_sections_become_one_stereo_file_with_silent_gap(self):
        first=self.root/"a.wav";second=self.root/"b.wav"
        wav(first,RATE//2,1000);wav(second,RATE//2,-1000)
        start,regions=midi_section_composite.compose([
            (second,12,0.5),(first,10,0.5)],self.root/"combined.wav")
        self.assertEqual(start,10)
        self.assertEqual(len(regions),2)
        with wave.open(str(self.root/"combined.wav"),"rb") as w:
            self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(2,2,RATE))
            self.assertEqual(w.getnframes(),int(2.5*RATE))
            self.assertNotEqual(w.readframes(1),b"\x00"*4)
            w.setpos(RATE)
            self.assertEqual(w.readframes(1),b"\x00"*4)
            w.setpos(2*RATE)
            self.assertNotEqual(w.readframes(1),b"\x00"*4)

    def test_overlap_rejected_without_publishing_audio(self):
        a=self.root/"a.wav";b=self.root/"b.wav";wav(a,RATE);wav(b,RATE)
        target=self.root/"combined.wav"
        with self.assertRaisesRegex(ValueError,"overlap"):
            midi_section_composite.compose([(a,0,1),(b,.5,1)],target)
        self.assertFalse(target.exists())

    def test_reject_mismatched_audio_frames(self):
        path=self.root/"bad.wav";wav(path,RATE)
        with self.assertRaisesRegex(ValueError,"mismatches"):
            midi_section_composite.compose([(path,0,2)],self.root/"combined.wav")

    def test_removing_one_composite_stem_clears_all_its_masks(self):
        source="01 (Bass).wav";derived="trk_revoice (BassCello).wav"
        project={"files":[source,derived],"source_tracks":[
            {"track_id":"trk_source","stem_alias":"Bass","display_name":"Bass",
             "working_filename":source},
            {"track_id":"trk_revoice","stem_alias":"BassCello","display_name":"BassCello",
             "working_filename":derived,"original_filename":"revoice.wav","imported":True,
             "start_seconds":0,"duration_seconds":20}],
             "replacement_masks":[
                {"replacement_track_id":"trk_revoice","source_track_id":"trk_source",
                 "source_filename":source,"start_seconds":0,"end_seconds":4,
                 "original_gain":0.1,"fade_seconds":.05},
                {"replacement_track_id":"trk_revoice","source_track_id":"trk_source",
                 "source_filename":source,"start_seconds":12,"end_seconds":16,
                 "original_gain":0.1,"fade_seconds":.05}]}
        removed,_=track_lifecycle.remove(project,"trk_revoice")
        self.assertFalse(removed["replacement_masks"])
        self.assertEqual(removed["files"],[source])

    def test_volume_annotation_is_roundtrippable(self):
        source="01 (Bass).wav";derived="trk_revoice (BassCello).wav"
        sections=[{"id":"v1","kind":"Verse","number":1,"start_seconds":0,"end_seconds":4},
                  {"id":"v2","kind":"Verse","number":2,"start_seconds":12,"end_seconds":16}]
        project={"files":[source,derived],"source_duration_seconds":20,
                 "sections":sections,"source_tracks":[
                 {"track_id":"trk_source","stem_alias":"Bass","display_name":"Bass","working_filename":source},
                 {"track_id":"trk_revoice","stem_alias":"BassCello","display_name":"BassCello",
                  "working_filename":derived,"imported":True,"start_seconds":0,"duration_seconds":20}],
                 "replacement_masks":[
                    {"replacement_track_id":"trk_revoice","source_track_id":"trk_source",
                     "source_filename":source,"start_seconds":0,"end_seconds":4,"original_gain":.1},
                    {"replacement_track_id":"trk_revoice","source_track_id":"trk_source",
                     "source_filename":source,"start_seconds":12,"end_seconds":16,"original_gain":.1}]}
        written=section_import.render_tags(project)
        self.assertIn("Bass.volume:10%@0.000-4.000#trk_revoice",written)
        self.assertIn("Bass.volume:10%@12.000-16.000#trk_revoice",written)
        self.assertNotIn("Bass.original",written)
        restored=section_import.apply(project,written,"replace",20)
        self.assertEqual(len(restored["replacement_masks"]),2)


if __name__=="__main__":
    unittest.main()
