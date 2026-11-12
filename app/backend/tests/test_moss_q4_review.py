"""Offline regression checks for bounded, unverified Q4 listening output."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import moss_q4_experiment as q4


class Q4ReviewTests(unittest.TestCase):
    def test_separates_human_answer_from_diagnostics(self):
        log = (
            "crispasr: audio: 3801600 samples (237.6 s) @ 16000 Hz\n"
            "crispasr: processing 9 slice(s)\n"
            "moss_audio: generated 20 tokens: \"This is a test\"\n"
            "crispasr: transcribed 237.6s audio in 45.40s (5.2x realtime)\n"
            "This is the final text, not an instrument measurement.\n"
        )
        review = q4._review_output(log)
        self.assertEqual(review["slices"], 9)
        self.assertEqual(review["duration_seconds"], 237.6)
        self.assertEqual(review["answer"], "This is the final text, not an instrument measurement.")
        self.assertFalse(review["validated"])
        self.assertFalse(review["aligned"])
        self.assertTrue(any("9" in warning for warning in review["warnings"]))

    def test_missing_delimiter_never_exposes_debug_as_answer(self):
        review = q4._review_output("moss_audio: generated 12 tokens: \"A guitar\"")
        self.assertEqual(review["answer"], "")
        self.assertTrue(review["warnings"])

    def test_repeated_chords_are_flagged(self):
        review = q4._review_output(
            "crispasr: transcribed 20s audio in 2.0s\n"
            + "C, F, " * 30 + "and 111 BPM"
        )
        self.assertTrue(any("chord" in w.lower() for w in review["warnings"]))
        self.assertTrue(any("tempo" in w.lower() for w in review["warnings"]))


if __name__ == "__main__":
    unittest.main()
