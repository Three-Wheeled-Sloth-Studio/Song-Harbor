"""Candidate loudness QA: preserve dynamics and avoid source mutations."""
from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from midi_candidate_level import level_candidate_wav


class MidiCandidateLevelTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path=Path(self.temporary.name)/"candidate.wav"

    def write(self, samples):
        samples=np.asarray(samples,dtype="<i2")
        with wave.open(str(self.path),"wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(48000)
            output.writeframes(samples.tobytes())

    def read(self):
        with wave.open(str(self.path),"rb") as audio:
            self.assertEqual(audio.getnchannels(),2)
            self.assertEqual(audio.getframerate(),48000)
            return np.frombuffer(audio.readframes(audio.getnframes()),dtype="<i2").copy()

    def test_quiet_render_lift_preserves_relative_dynamics_and_length(self):
        original=np.tile(np.array([500,1000,-1000,-2000],dtype="<i2"),200)
        self.write(original)
        gain=level_candidate_wav(self.path)
        result=self.read()
        self.assertGreater(gain,0)
        self.assertLessEqual(gain,12.05)
        self.assertEqual(result.size,original.size)
        self.assertAlmostEqual(float(result[1])/float(result[0]),2.0,places=2)
        self.assertLessEqual(int(np.max(np.abs(result.astype(np.int32)))),16385)

    def test_loud_render_is_not_reduced_or_reencoded(self):
        original=np.array([20000,-21000,16000,12000],dtype="<i2")
        self.write(original)
        before=self.path.read_bytes()
        self.assertEqual(level_candidate_wav(self.path),0)
        self.assertEqual(self.path.read_bytes(),before)

    def test_silent_render_does_not_inflate_noise(self):
        self.write(np.array([0,128,-128,0],dtype="<i2"))
        before=self.path.read_bytes()
        self.assertEqual(level_candidate_wav(self.path),0)
        self.assertEqual(self.path.read_bytes(),before)

    def test_second_pass_is_bounded(self):
        self.write(np.array([1000,-2000,1000,-2000],dtype="<i2"))
        level_candidate_wav(self.path)
        level_candidate_wav(self.path)
        self.assertLessEqual(int(np.max(np.abs(self.read().astype(np.int32)))),16385)


if __name__=="__main__":
    unittest.main()
