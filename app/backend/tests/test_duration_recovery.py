"""Legacy song duration hydration for sections, without relying on the browser."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import projects
import server


class DurationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ident = "abcdef012345"
        self.folder = self.root / "jobs" / self.ident
        (self.folder / "stems").mkdir(parents=True)
        self.source = self.folder / "song.wav"
        self.source.write_bytes(b"test source")
        self.files = []
        for name in projects.ORDER:
            filename = f"song_({name})_htdemucs_6s.wav"
            (self.folder / "stems" / filename).write_bytes(b"test stem")
            self.files.append(filename)
        self.record = {
            "version": 1, "id": self.ident, "title": "Song",
            "filename": self.source.name, "source_filename": self.source.name,
            "files": self.files, "stems": projects.default_settings(self.files),
            "source_duration_seconds": None
        }
        projects.write_project(self.root, self.record)
        self.job = {"status": "complete", "source_duration_seconds": None}

    def test_recovers_from_source_and_persists(self):
        with patch.object(server, "DATA_ROOT", self.root), \
             patch.object(server, "probe_duration", return_value=183.125) as probe:
            result = server.resolved_song_duration(self.record, self.job)
            self.assertEqual(result, 183.125)
            self.assertEqual(self.source, probe.call_args.args[0])
            self.assertEqual(183.125, self.job["source_duration_seconds"])
        saved = projects.read_project(self.root, self.ident)
        self.assertEqual(183.125, saved["source_duration_seconds"])

    def test_falls_back_to_stem_if_original_missing(self):
        self.source.unlink()
        with patch.object(server, "DATA_ROOT", self.root), \
             patch.object(server, "probe_duration", return_value=130.5):
            result = server.resolved_song_duration(self.record, self.job)
        self.assertEqual(130.5, result)
        self.assertEqual(130.5, projects.read_project(self.root, self.ident)["source_duration_seconds"])

    def test_already_known_duration_does_not_probe(self):
        self.record["source_duration_seconds"] = 99
        with patch.object(server, "DATA_ROOT", self.root), \
             patch.object(server, "probe_duration", side_effect=AssertionError("Should not probe")):
            self.assertEqual(99, server.resolved_song_duration(self.record, self.job))

    def test_probes_only_existing_files(self):
        self.source.unlink()
        for name in self.files:
            (self.folder / "stems" / name).unlink()
        with patch.object(server, "DATA_ROOT", self.root), \
             patch.object(server, "probe_duration", side_effect=AssertionError("No file to probe")):
            with self.assertRaisesRegex(ValueError, "Could not read"):
                server.resolved_song_duration(self.record, self.job)


if __name__ == "__main__":
    unittest.main()
