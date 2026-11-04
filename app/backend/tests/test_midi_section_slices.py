"""Section slicing must not mute, render or rewrite unselected song regions."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements
import midi_section_slices as slices

RATE=midi_arrangements.RATE


class SectionSliceTests(unittest.TestCase):
    def setUp(self):
        self.asset=midi_arrangements.create("trk_bass",10,12,[
            {"pitch":40,"start":0.0,"end":3.5,"velocity":88},
            {"pitch":43,"start":3.5,"end":6.5,"velocity":92},
            {"pitch":45,"start":7.0,"end":12.0,"velocity":96},
        ])
        self.sections=[
            {"id":"v1","kind":"Verse","start_seconds":10,"end_seconds":14},
            {"id":"c1","kind":"Chorus","start_seconds":14,"end_seconds":18},
            {"id":"v2","kind":"Verse","start_seconds":18,"end_seconds":22},
        ]

    def test_nonadjacent_sections_become_independently_positioned_candidates(self):
        original_notes=[dict(n) for n in self.asset["notes"]]
        pieces=slices.select_sections(self.asset,self.sections,["v2","v1"])
        self.assertEqual([p["section_id"] for p in pieces],["v1","v2"])
        self.assertEqual([p["start_seconds"] for p in pieces],[10,18])
        self.assertEqual([p["duration_seconds"] for p in pieces],[4,4])
        self.assertEqual(pieces[0]["arrangement"]["notes"][0]["end_sample"],int(3.5*RATE))
        self.assertEqual(pieces[1]["arrangement"]["notes"][0]["start_sample"],0)
        self.assertEqual(self.asset["notes"],original_notes)

    def test_note_crossing_section_boundary_is_clipped_to_slice(self):
        pieces=slices.select_sections(self.asset,self.sections,["c1"])
        note=next(n for n in pieces[0]["arrangement"]["notes"] if n["pitch"]==43)
        self.assertEqual(note["start_sample"],0)
        self.assertEqual(note["end_sample"],int(2.5*RATE))
        self.assertEqual(pieces[0]["arrangement"]["source"]["start_sample"],14*RATE)

    def test_overlapping_sections_are_rejected(self):
        rows=[dict(self.sections[0]),dict(self.sections[1])]
        rows[1]["start_seconds"]=13.5
        with self.assertRaisesRegex(ValueError,"overlap"):
            slices.select_sections(self.asset,rows,["v1","c1"])

    def test_out_of_bounds_section_rejected(self):
        rows=[{"id":"external","start_seconds":9.9,"end_seconds":12}]
        with self.assertRaisesRegex(ValueError,"outside"):
            slices.select_sections(self.asset,rows,["external"])

    def test_empty_section_refuses_silent_candidate(self):
        asset=midi_arrangements.create("trk_bass",0,8,[
            {"pitch":40,"start":0.5,"end":1.5,"velocity":80}])
        sections=[{"id":"silent","start_seconds":4,"end_seconds":8}]
        with self.assertRaisesRegex(ValueError,"no MIDI notes"):
            slices.select_sections(asset,sections,["silent"])

    def test_global_arrangement_start_offsets_section_timestamps(self):
        part=slices.select_sections(self.asset,self.sections,["c1"])[0]
        self.assertEqual(part["start_seconds"],14)
        self.assertEqual(part["arrangement"]["source"]["start_sample"],14*RATE)
        self.assertEqual(part["arrangement"]["duration_samples"],4*RATE)

    def test_missing_repeated_and_too_many_selections(self):
        with self.assertRaisesRegex(ValueError,"distinct"):
            slices.select_sections(self.asset,self.sections,["v1","v1"])
        with self.assertRaisesRegex(ValueError,"no longer exists"):
            slices.select_sections(self.asset,self.sections,["not-there"])
        with self.assertRaisesRegex(ValueError,"distinct"):
            slices.select_sections(self.asset,self.sections,["v1"]*9)


if __name__=="__main__":
    unittest.main()
