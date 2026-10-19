"""Section marker contract: labels are annotations, not destructive waveform edits."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sections
import projects


class SectionsTests(unittest.TestCase):
    def fixture(self, kind="Chorus", start=75, end=105):
        return {"kind":kind, "number":None, "start_seconds":start,"end_seconds":end}

    def test_timed_tag_roundtrip(self):
        item = sections.parse_tag("[Chorus 1:15-1:45]")
        self.assertEqual(75.0, item["start_seconds"])
        self.assertEqual("[Chorus 1:15-1:45]", sections.display_tag(item))

    def test_numbered_verse_and_fractional_times(self):
        item = sections.parse_tag("[Verse 2 0:10.25-0:35.5]")
        self.assertEqual(2, item["number"])
        self.assertEqual("[Verse 2 0:10.25-0:35.5]", sections.display_tag(item))

    def test_plain_header_does_not_guess_timeline(self):
        with self.assertRaisesRegex(ValueError, "timed section"):
            sections.parse_tag("[Chorus]")

    def test_adjacent_sections_are_valid(self):
        ordered = sections.validate_sections([self.fixture("Chorus", 75, 105),
                                               self.fixture("Verse", 0, 75)], duration=105)
        self.assertEqual(["Verse", "Chorus"], [s["kind"] for s in ordered])

    def test_overlap_and_invalid_range_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            sections.validate_sections([self.fixture("Verse", 0, 80),
                                        self.fixture("Chorus", 75, 105)])
        for start,end in [(-1,20), (20,20), (30,20), (0,float("inf"))]:
            with self.subTest(start=start,end=end):
                with self.assertRaises(ValueError):
                    sections.validate_sections([self.fixture(start=start,end=end)])

    def test_duration_and_wrong_tag_rejected(self):
        with self.assertRaisesRegex(ValueError, "source duration"):
            sections.validate_sections([self.fixture()], duration=100)
        with self.assertRaises(ValueError):
            sections.parse_tag("[Chorus dramatic soprano 1:15-1:45]")
        with self.assertRaises(ValueError):
            sections.parse_tag("[Verse 1:75-2:15]")

    def test_section_metadata_does_not_change_source_or_stems(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ident = "abcdef012345"
            folder = root / "jobs" / ident
            (folder / "stems").mkdir(parents=True)
            (folder / "song.wav").write_bytes(b"source unchanged")
            filenames = []
            for kind in projects.ORDER:
                filename = f"song_({kind})_htdemucs_6s.wav"
                filenames.append(filename)
                (folder / "stems" / filename).write_bytes(kind.encode())
            project = projects.read_project(root, ident)
            project["sections"] = sections.validate_sections([self.fixture()], duration=120)
            projects.write_project(root, project)
            reopened = projects.read_project(root, ident)
            self.assertEqual(project["sections"], reopened["sections"])
            self.assertEqual(b"source unchanged", (folder / "song.wav").read_bytes())
            for filename, kind in zip(filenames, projects.ORDER):
                self.assertEqual(kind.encode(), (folder / "stems" / filename).read_bytes())


if __name__ == "__main__":
    unittest.main()
