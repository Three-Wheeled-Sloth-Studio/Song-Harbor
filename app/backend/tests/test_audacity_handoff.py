"""Portable, safe six-track Audacity handoff without scripting-pipe modules."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audacity_handoff
import server
from fastapi.testclient import TestClient


class AudacityHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ident = "abcdef012345"
        self.directory = self.root / "jobs" / self.ident / "exports" / "Audacity"
        self.directory.mkdir(parents=True)
        self.tracks = []
        for i, name in enumerate(audacity_handoff.STEM_ORDER, start=1):
            basename = f"{i:02d} - {name}.wav"
            (self.directory / basename).write_bytes(name.encode())
            self.tracks.append({"name": name, "file": basename, "start_seconds": 0.0, "gain": 1.0})
        self.manifest = {
            "target": "audacity", "source_project_id": self.ident,
            "track_count": 6, "tracks": self.tracks
        }
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_lof_creates_one_window_and_six_ordered_tracks_at_zero(self):
        lof = audacity_handoff.make_lof(self.directory)
        lines = lof.read_text(encoding="utf-8").splitlines()
        self.assertEqual("window", lines[1])
        self.assertEqual(8, len(lines))
        for track, line in zip(self.tracks, lines[2:]):
            path = self.directory / track["file"]
            self.assertEqual(f'file "{path.name}" offset 0', line)
        for track in self.tracks:
            self.assertEqual(track["name"].encode(),
                             (self.directory / track["file"]).read_bytes())

    def test_rejects_missing_or_escaping_stem(self):
        (self.directory / self.tracks[0]["file"]).unlink()
        with self.assertRaises(ValueError):
            audacity_handoff.make_lof(self.directory)
        (self.directory / self.tracks[0]["file"]).write_bytes(b"fixed")
        self.tracks[1]["file"] = "../escape.wav"
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            audacity_handoff.make_lof(self.directory)

    def test_launch_passes_single_lof_argument_and_requests_focus(self):
        executable = self.root / "Audacity4.exe"
        executable.write_bytes(b"test-executable")
        with patch.object(audacity_handoff.subprocess, "Popen", return_value=SimpleNamespace(pid=111)) as launch, \
             patch.object(audacity_handoff.threading, "Thread") as focus:
            result = audacity_handoff.launch_audacity(str(executable), self.directory)
        args = launch.call_args.args[0]
        self.assertEqual(str(executable.resolve()), args[0])
        self.assertTrue(args[1].endswith(".lof"))
        self.assertEqual(2, len(args))
        self.assertEqual("started", result["status"])
        self.assertTrue(result["import_requested"])
        self.assertEqual("_foreground_audacity", focus.call_args.kwargs["target"].__name__)
        self.assertEqual(111, focus.call_args.kwargs["args"][1])
        focus.return_value.start.assert_called_once()

    def test_api_rejects_other_song_or_mismatched_da_w(self):
        client = TestClient(server.app)
        job = {"id": self.ident, "status": "complete"}
        with patch.object(server, "DATA_ROOT", self.root), \
             patch.object(server, "get_job", return_value=job), \
             patch.object(server.daw, "resolve", return_value=str(self.root / "Audacity4.exe")), \
             patch.object(server.audacity_handoff, "launch_audacity", return_value={"status": "started"}) as launched:
            result = client.post(f"/api/projects/{self.ident}/daw/launch",
                                 json={"target": "audacity", "directory": str(self.directory)})
            self.assertEqual(200, result.status_code, result.text)
            launched.assert_called_once()
            wrong = client.post(f"/api/projects/{self.ident}/daw/launch",
                                json={"target": "waveform", "directory": str(self.directory)})
            self.assertEqual(400, wrong.status_code)
            outside = client.post(f"/api/projects/{self.ident}/daw/launch",
                                  json={"target": "audacity", "directory": str(self.root)})
            self.assertEqual(400, outside.status_code)


if __name__ == "__main__":
    unittest.main()
