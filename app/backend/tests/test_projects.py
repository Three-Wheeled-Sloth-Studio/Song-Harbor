"""Persistent song workbench and Waveform handoff tests (no audio processing needed)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import projects


class SongProjectsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ident = "abcdef012345"
        self.job = self.root / "jobs" / self.ident
        (self.job / "stems").mkdir(parents=True)
        self.source = self.job / "song.wav"
        self.source.write_bytes(b"original source")
        self.files = []
        for label in projects.ORDER:
            filename = "song_(" + label + ")_htdemucs_6s.wav"
            (self.job / "stems" / filename).write_bytes(label.encode("ascii"))
            self.files.append(filename)

    def test_legacy_job_recovered_without_reseparation(self):
        record = projects.read_project(self.root, self.ident)
        self.assertIsNotNone(record)
        self.assertEqual(self.files, record["files"])
        self.assertTrue(record["recovered"])
        self.assertEqual("song", record["title"])
        self.assertEqual(1, len(projects.list_projects(self.root)))

    def test_save_and_reload_mixer_settings(self):
        record = projects.read_project(self.root, self.ident)
        record["title"] = "Salt in the Circuit"
        record["stems"][0]["gain"] = 0.25
        record["stems"][0]["mute"] = True
        projects.write_project(self.root, record)
        loaded = projects.read_project(self.root, self.ident)
        self.assertEqual("Salt in the Circuit", loaded["title"])
        self.assertEqual(0.25, loaded["stems"][0]["gain"])
        self.assertTrue(loaded["stems"][0]["mute"])
        self.assertEqual("Salt in the Circuit", projects.list_projects(self.root)[0]["title"])

    def test_waveform_export_is_portable_and_non_destructive(self):
        record = projects.read_project(self.root, self.ident)
        record["title"] = "Salt in the Circuit"
        record["stems"][0]["gain"] = 0.5
        before = {p.name: p.read_bytes() for p in (self.job / "stems").iterdir()}
        first = projects.export_waveform(self.root, record)
        self.assertTrue((first / "IMPORT-IN-WAVEFORM.txt").is_file())
        manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(6, manifest["track_count"])
        self.assertEqual([0.0] * 6, [track["start_seconds"] for track in manifest["tracks"]])
        self.assertEqual(list(projects.ORDER), [track["name"] for track in manifest["tracks"]])
        self.assertEqual(0.5, manifest["tracks"][0]["gain"])
        for index, label in enumerate(projects.ORDER, start=1):
            self.assertEqual(label.encode("ascii"), (first / f"{index:02d} - {label}.wav").read_bytes())
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.job / "stems").iterdir()})
        second = projects.export_waveform(self.root, record)
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_dir())
        self.assertTrue(second.is_dir())

    def test_missing_stem_rejects_export(self):
        (self.job / "stems" / self.files[-1]).unlink()
        self.assertEqual([], projects.files_for_project(self.job))
        with self.assertRaises(ValueError):
            projects.export_waveform(self.root, {"id": self.ident, "files": self.files, "stems": []})

    def test_invalid_project_identifier_rejected(self):
        with self.assertRaises(ValueError):
            projects.project_path(self.root, "../etc")


if __name__ == "__main__":
    unittest.main()
