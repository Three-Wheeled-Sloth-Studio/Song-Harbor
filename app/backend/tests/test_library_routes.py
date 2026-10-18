"""Exercise actual HTTP methods, not just SQLite helper functions.

Regression: Library displayed correctly but Remove/Combine returned HTTP 404 because a
stale backend remained bound to the local API port. This test catches missing routes;
the Windows launcher separately detects an out-of-date backend instance token.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import library
import projects
import server
from fastapi.testclient import TestClient


class LibraryRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = TestClient(server.app)
        self.root_patch = patch.object(server, "DATA_ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        for ident, payload in (("abcdef012345", b"same exact source"),
                               ("123456abcdef", b"same exact source")):
            folder = self.root / "jobs" / ident
            stems = folder / "stems"
            stems.mkdir(parents=True)
            source = folder / "Raise the Neon Black.wav"
            source.write_bytes(payload)
            files = []
            for label in projects.ORDER:
                name = f"Raise the Neon Black_({label})_htdemucs_6s.wav"
                (stems / name).write_bytes(label.encode())
                files.append(name)
            projects.write_project(self.root, {
                "version": 1, "id": ident, "title": "Raise the Neon Black",
                "filename": source.name, "source_filename": source.name,
                "files": files, "stems": projects.default_settings(files),
                "created_at": 1 if ident == "abcdef012345" else 2,
                "model": "htdemucs_6s.yaml",
            })

    def test_routes_exist_and_identical_bytes_group(self):
        response = self.client.get("/api/library")
        self.assertEqual(200, response.status_code, response.text)
        songs = response.json()["songs"]
        self.assertEqual(1, len(songs))
        self.assertEqual(2, songs[0]["variant_count"])
        self.assertEqual(12, len(songs[0]["fingerprint"]))
        ident = songs[0]["id"]
        removed = self.client.post(f"/api/library/songs/{ident}/remove")
        self.assertEqual(200, removed.status_code, removed.text)
        self.assertEqual([], self.client.get("/api/library").json()["songs"])
        trash = self.client.get("/api/library/trash")
        self.assertEqual(200, trash.status_code, trash.text)
        self.assertEqual(1, len(trash.json()["songs"]))
        restored = self.client.post(f"/api/library/songs/{ident}/restore")
        self.assertEqual(200, restored.status_code, restored.text)
        self.assertEqual(1, len(self.client.get("/api/library").json()["songs"]))
        self.assertTrue((self.root / "jobs" / "abcdef012345" / "Raise the Neon Black.wav").is_file())

    def test_combine_endpoint_preserves_distinct_files(self):
        # A second source variant can be linked even if its decoded/source bytes differ.
        second = self.root / "jobs" / "123456abcdef" / "Raise the Neon Black.wav"
        second.write_bytes(b"distinct metadata or edit")
        response = self.client.get("/api/library")
        self.assertEqual(2, len(response.json()["songs"]))
        songs = response.json()["songs"]
        target, parent = songs[0]["id"], songs[1]["id"]
        result = self.client.post(f"/api/library/songs/{target}/combine",
                                  json={"parent_song_id": parent})
        self.assertEqual(200, result.status_code, result.text)
        self.assertEqual(1, len(self.client.get("/api/library").json()["songs"]))
        self.assertEqual(2, self.client.get("/api/library").json()["songs"][0]["variant_count"])


if __name__ == "__main__":
    unittest.main()
