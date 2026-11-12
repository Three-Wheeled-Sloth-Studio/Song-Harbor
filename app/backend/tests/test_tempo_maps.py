"""Provider-neutral tempo-map schema and revision checks, offline only."""
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempo_maps as tm


def anchor(sample=0, bpm=111, transition="step"):
    return {"id": uuid.uuid4().hex, "sample": sample, "bpm": bpm,
            "transition": transition, "origin": "author", "meter": [4, 4]}


class TempoMapTests(unittest.TestCase):
    def test_initially_unknown_not_fabricated(self):
        asset = tm.create(48000 * 20)
        self.assertEqual(asset["anchors"], [])
        self.assertEqual(asset["observations"], [])
        self.assertIsNone(tm.bpm_at(asset, 0))

    def test_variable_tempo_and_ramp(self):
        asset = tm.create(48000 * 20)
        revised = tm.revise(asset, 0, anchors=[
            anchor(0, 111, "linear"), anchor(48000 * 10, 90),
            anchor(48000 * 15, 130)])
        self.assertEqual(tm.bpm_at(revised, 0), 111)
        self.assertAlmostEqual(tm.bpm_at(revised, 48000 * 5), 100.5)
        self.assertEqual(tm.bpm_at(revised, 48000 * 11), 90)
        self.assertEqual(tm.bpm_at(revised, 48000 * 16), 130)
        self.assertEqual(asset["revision"], 0)
        self.assertEqual(revised["revision"], 1)

    def test_uncertain_candidates_do_not_change_accepted_tempo(self):
        asset = tm.create(48000 * 8)
        guess = {"id": uuid.uuid4().hex, "start_sample": 0, "end_sample": 48000 * 8,
                 "method": "moss-audio-q4", "bpm": 111,
                 "alternatives": [55.5, 222], "status": "unverified",
                 "source_sha256": "abc", "confidence": None}
        updated = tm.revise(asset, 0, observations=[guess])
        self.assertIsNone(tm.bpm_at(updated, 48000))
        self.assertEqual(updated["observations"][0]["alternatives"], [55.5, 222.0])

    def test_reject_duplicate_anchor_or_stale_revision(self):
        asset = tm.create(48000 * 8)
        with self.assertRaisesRegex(ValueError, "one sample"):
            tm.revise(asset, 0, anchors=[anchor(0), anchor(0)])
        revised = tm.revise(asset, 0, anchors=[anchor(0)])
        with self.assertRaisesRegex(ValueError, "Stale"):
            tm.revise(revised, 0, anchors=[anchor(0)])
        late = tm.revise(asset, 0, anchors=[anchor(48000)])
        self.assertIsNone(tm.bpm_at(late, 0))
        self.assertEqual(tm.bpm_at(late, 48000), 111)

    def test_atomic_roundtrip_and_cas(self):
        asset = tm.create(48000 * 6)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tm.save(root, asset, expected_revision=None)
            revised = tm.revise(asset, 0, anchors=[anchor(0, 105)])
            tm.save(root, revised, expected_revision=0)
            self.assertEqual(tm.read(root), revised)
            with self.assertRaisesRegex(ValueError, "Stale"):
                tm.save(root, asset, expected_revision=0)


if __name__ == "__main__":
    unittest.main()
