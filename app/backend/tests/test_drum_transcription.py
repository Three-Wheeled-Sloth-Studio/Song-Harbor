"""No-network, CPU drum onset estimator smoke/regression tests."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import drum_transcription as drum

class DrumTranscriptionTests(unittest.TestCase):
    def test_silence_has_no_hits(self):
        self.assertEqual(drum.classify(np.zeros(drum.RATE,dtype=np.float32)),[])

    def test_two_separated_percussive_attacks_generate_editable_hits(self):
        samples=np.zeros(drum.RATE*2,dtype=np.float32)
        attack=np.random.default_rng(2).normal(0,.55,512).astype(np.float32)
        samples[round(.3*drum.RATE):round(.3*drum.RATE)+512]=attack
        samples[round(1.2*drum.RATE):round(1.2*drum.RATE)+512]=attack
        notes=drum.classify(samples)
        self.assertGreaterEqual(len(notes),2)
        self.assertTrue(any(abs(n["start"]-.3)<.08 for n in notes))
        self.assertTrue(any(abs(n["start"]-1.2)<.08 for n in notes))
        for n in notes:
            self.assertIn(n["pitch"],drum.LANES)
            self.assertGreater(n["end"],n["start"])
            self.assertTrue(1<=n["velocity"]<=127)

    def test_invalid_pcm_is_rejected(self):
        with self.assertRaises(ValueError):
            drum.classify(np.array([float("nan")],dtype=np.float32))

if __name__=="__main__":
    unittest.main()
