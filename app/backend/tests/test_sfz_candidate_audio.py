"""Shared SFZ Preview rendering tests; sfizz and FFmpeg are mocked."""
from __future__ import annotations
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sfz_candidate_audio


class SFZCandidateAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sfz=self.root/"Growlybass.sfz"
        self.sfz.write_text("<region> sample=example.wav")
        self.output=self.root/"candidate"/"bowed-preview.wav"

    def _write_wav(self, filename:Path, rate:int=48000, frames:int=48000):
        with wave.open(str(filename),"wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            audio.writeframes(b"\x00\x00\x00\x00"*frames)

    def test_success_creates_candidate_not_original_audio(self):
        original=self.root/"bass.wav"
        original.write_bytes(b"original stem")
        def sfizz(midi,sfz,raw,**kwargs):
            self.assertTrue(midi.read_bytes().startswith(b"MThd"))
            self.assertEqual(sfz,self.sfz)
            self._write_wav(raw)
        def ffmpeg(args,**kwargs):
            self.assertIn("apad,atrim=duration=1.000",args)
            self._write_wav(Path(args[-1]))
            return type("Result",(),{"returncode":0})()
        with patch.object(sfz_candidate_audio.sfz_render_adapter,"render_sfz",side_effect=sfizz), \
             patch.object(sfz_candidate_audio.subprocess,"run",side_effect=ffmpeg):
            sfz_candidate_audio.render_candidate(
                b"MThd"+b"\x00"*16,self.sfz,self.output,1.0,"ffmpeg",self.root)
        self.assertTrue(self.output.exists())
        self.assertEqual(original.read_bytes(),b"original stem")

    def test_bad_alignment_keeps_old_candidate(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"previous good candidate")
        def sfizz(midi,sfz,raw,**kwargs):
            self._write_wav(raw)
        def ffmpeg(args,**kwargs):
            self._write_wav(Path(args[-1]),rate=44100)
            return type("Result",(),{"returncode":0})()
        with patch.object(sfz_candidate_audio.sfz_render_adapter,"render_sfz",side_effect=sfizz), \
             patch.object(sfz_candidate_audio.subprocess,"run",side_effect=ffmpeg):
            with self.assertRaisesRegex(ValueError,"aligned 48-kHz"):
                sfz_candidate_audio.render_candidate(
                    b"MThd"+b"\x00"*16,self.sfz,self.output,1.0,"ffmpeg",self.root)
        self.assertEqual(self.output.read_bytes(),b"previous good candidate")

    def test_reject_non_midi(self):
        with self.assertRaisesRegex(ValueError,"MIDI header"):
            sfz_candidate_audio.render_candidate(
                b"not midi",self.sfz,self.output,1.0,"ffmpeg",self.root)


if __name__=="__main__":
    unittest.main()
