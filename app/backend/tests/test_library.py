"""SQLite Library indexing and rename semantics over untouched legacy media."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import library
import projects


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.job_id = "abcdef012345"
        self.job = self.root / "jobs" / self.job_id
        stems = self.job / "stems"
        stems.mkdir(parents=True)
        self.source = self.job / "Salt in the Circuit.wav"
        self.source.write_bytes(b"unchanged original source")
        self.files = []
        for name in projects.ORDER:
            filename = f"Salt in the Circuit_({name})_htdemucs_6s.wav"
            (stems / filename).write_bytes(name.encode())
            self.files.append(filename)
        projects.write_project(self.root, {
            "version": 1, "id": self.job_id,
            "filename": self.source.name,
            "title": "Salt in the Circuit",
            "source_filename": self.source.name,
            "model": "htdemucs_6s.yaml", "files": self.files,
            "stems": projects.default_settings(self.files),
            "created_at": 1.0
        })

    def test_idempotent_adoption_and_media_preservation(self):
        originals = {p.name: p.read_bytes() for p in (self.job / "stems").iterdir()}
        for _ in range(3):
            library.adopt_jobs(self.root)
        with library.connect(self.root) as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0])
            self.assertEqual(6, conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
        self.assertEqual(originals, {p.name:p.read_bytes() for p in (self.job/"stems").iterdir()})
        self.assertEqual(b"unchanged original source", self.source.read_bytes())

    def test_rename_updates_manifest_not_filename(self):
        library.adopt_jobs(self.root)
        song = library.list_songs(self.root)[0]
        library.rename_song(self.root, song["id"], "Circuit of Salt")
        self.assertEqual("Circuit of Salt", library.list_songs(self.root)[0]["title"])
        self.assertEqual("Salt in the Circuit.wav",
                         library.list_songs(self.root)[0]["imported_filename"])
        self.assertEqual("Circuit of Salt", projects.read_project(self.root, self.job_id)["title"])
        self.assertTrue(self.source.is_file())
        library.adopt_jobs(self.root)
        self.assertEqual("Circuit of Salt", library.list_songs(self.root)[0]["title"])

    def test_virtual_collections_do_not_move_audio(self):
        library.adopt_jobs(self.root)
        song = library.list_songs(self.root)[0]
        parent = library.create_collection(self.root, "Infra Choir")
        child = library.create_collection(self.root, "Voices Below the Deck", parent["id"])
        library.assign_song(self.root, song["id"], child["id"])
        library.assign_song(self.root, song["id"], parent["id"])
        self.assertEqual(1, len(library.list_songs(self.root, child["id"])))
        self.assertEqual(1, len(library.list_songs(self.root, parent["id"])))
        self.assertEqual(1, len(library.list_songs(self.root)))
        self.assertTrue(self.source.is_file())
        self.assertEqual(6, len(list((self.job / "stems").glob("*.wav"))))

    def test_unrelated_names_remain_distinct(self):
        library.adopt_jobs(self.root)
        self.assertEqual([], library.list_songs(self.root, query="unknown"))
        self.assertEqual(1, len(library.list_songs(self.root, query="Salt")))


if __name__ == "__main__":
    unittest.main()
