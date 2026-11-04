"""Drum keymap and explicit percussion MIDI integration checks."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drum_keymaps
import midi_arrangements
import polyphonic_midi


class DrumKeymapTests(unittest.TestCase):
    def score(self):
        asset = midi_arrangements.create("drums", 0, 2, [
            {"pitch": 36, "start": 0, "end": .1, "velocity": 120},
            {"pitch": 38, "start": 0, "end": .1, "velocity": 90},
            {"pitch": 42, "start": .25, "end": .35, "velocity": 65},
        ])
        for note in asset["notes"]:
            note["channel"] = 9
        return asset

    def test_gm_map_contains_standard_drum_lanes(self):
        mapping = drum_keymaps.default_keymap()
        self.assertEqual(mapping, drum_keymaps.validate_keymap(mapping))
        self.assertEqual(drum_keymaps.label_for_pitch(mapping, 36), "Bass Drum 1")
        self.assertEqual(drum_keymaps.label_for_pitch(mapping, 42), "Closed Hi-Hat")
        drum_keymaps.verify_notes(self.score(), mapping)

    def test_explicit_custom_map_for_non_gm_sfz_pack(self):
        mapping = {"schema_version": 1, "mapping_kind": "custom", "lanes": [
            {"pitch": 36, "name": "Industrial Kick"},
            {"pitch": 38, "name": "Rust Snare"},
            {"pitch": 42, "name": "Metal Hat", "choke_group": "hat"}
        ]}
        validated = drum_keymaps.validate_keymap(mapping)
        self.assertEqual(validated["lanes"][-1]["choke_group"], "hat")
        drum_keymaps.verify_notes(self.score(), mapping)
        blob = polyphonic_midi.to_midi(self.score(), 0, percussion=True)
        self.assertTrue(blob.startswith(b"MThd"))

    def test_unmapped_pitch_fails_closed(self):
        mapping = {"schema_version": 1, "mapping_kind": "custom", "lanes": [
            {"pitch": 36, "name": "Kick"}]}
        with self.assertRaisesRegex(ValueError, "38, 42"):
            drum_keymaps.verify_notes(self.score(), mapping)

    def test_invalid_and_duplicate_keymap_lanes_fail(self):
        base = {"schema_version": 1, "mapping_kind": "custom"}
        for lanes in (
            [], [{"pitch": 36, "name": "Kick"}, {"pitch": 36, "name": "Snare"}],
            [{"pitch": -1, "name": "Kick"}],
            [{"pitch": True, "name": "Kick"}],
            [{"pitch": 36, "name": ""}],
            [{"pitch": 36, "name": "Kick", "choke_group": "../invalid"}],
        ):
            with self.subTest(lanes=lanes), self.assertRaises(ValueError):
                drum_keymaps.validate_keymap({**base, "lanes": lanes})

    def test_nonstandard_lane_cannot_claim_gm_mapping(self):
        mapping = {"schema_version": 1, "mapping_kind": "gm",
                   "lanes": [{"pitch": 36, "name": "Dirty Kick"}]}
        with self.assertRaisesRegex(ValueError, "custom mapping"):
            drum_keymaps.validate_keymap(mapping)

    def test_note_validation_is_nonmutating(self):
        score = self.score()
        original = [dict(note) for note in score["notes"]]
        drum_keymaps.verify_notes(score, drum_keymaps.default_keymap())
        self.assertEqual(score["notes"], original)


if __name__ == "__main__":
    unittest.main()
