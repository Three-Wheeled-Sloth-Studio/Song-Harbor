"""Regression for near-copy Lego output (source leakage) without ACE/GPU."""
from array import array
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ace_isolation as checker


class IsolationTests(unittest.TestCase):
    @staticmethod
    def wave(phase=0):
        return array("f",(math.sin(i*.07+phase) for i in range(checker.SAMPLE_RATE*5)))

    def test_correlation_detects_source_shadow(self):
        reference=self.wave()
        generated=array("f",(0.82*v+0.1*math.sin(i*.43) for i,v in enumerate(reference)))
        self.assertGreater(checker.correlation(reference,generated),0.90)

    def test_unrelated_instrument_is_not_automatically_rejected(self):
        self.assertLess(abs(checker.correlation(self.wave(),self.wave(1.570796))),0.1)

    def test_two_of_three_matching_windows_require_review(self):
        with patch("ace_isolation._mono_excerpt",side_effect=[
            self.wave(),self.wave(),self.wave(),self.wave(1.570796),
            self.wave(),self.wave()
        ]):
            result=checker.assess_context_leakage("ffmpeg",Path("a.wav"),Path("b.wav"),50)
        self.assertEqual(result["status"],"suspected_source_leakage")
        self.assertEqual(result["matching_windows"],2)

    def test_short_audio_unknown_is_not_approved(self):
        result=checker.assess_context_leakage("ffmpeg",Path("a.wav"),Path("b.wav"),4)
        self.assertEqual(result["status"],"unknown")


if __name__=="__main__":
    unittest.main()
