"""DAW adapters: Audacity discovery, preserved Waveform config and portable export."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daw
import projects
import server
from fastapi.testclient import TestClient


class DawAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.audacity = self.root / "Installed" / "Audacity" / "Audacity.exe"
        self.audacity.parent.mkdir(parents=True)
        self.audacity.write_bytes(b"test-fixture")
        self.waveform = self.root / "Installed" / "Waveform" / "Waveform 14.exe"
        self.waveform.parent.mkdir(parents=True)
        self.waveform.write_bytes(b"test-fixture")

    def test_saved_target_paths_independent(self):
        daw.set_location(self.root, str(self.waveform), "waveform")
        daw.set_location(self.root, str(self.audacity), "audacity")
        daw.select_target(self.root, "audacity")
        self.assertEqual("audacity", daw.selected_target(self.root))
        self.assertEqual(str(self.audacity.resolve()), daw.configured(self.root, "audacity"))
        self.assertEqual(str(self.waveform.resolve()), daw.configured(self.root, "waveform"))
        data = json.loads((self.root / "config" / "settings.json").read_text())
        self.assertEqual("audacity", data["selected_daw"])

    def test_auto_detect_registry_candidate_saves_path(self):
        with patch.object(daw, "windows_registry_locations", return_value=[self.audacity.parent]), \
             patch.object(daw, "common_locations", return_value=[]), \
             patch.object(daw.shutil, "which", return_value=None):
            found = daw.resolve(self.root, target_id="audacity")
        self.assertEqual(str(self.audacity.resolve()), found)
        self.assertEqual(found, daw.configured(self.root, "audacity"))

    def test_wrong_executable_rejected(self):
        with self.assertRaises(ValueError):
            daw.set_location(self.root, str(self.waveform), "audacity")
        self.assertIsNone(daw.verify_executable("audacity", self.waveform))

    def test_api_catalog_and_selection(self):
        with patch.object(server, "APP_ROOT", self.root), \
             patch.object(daw, "windows_registry_locations", return_value=[]), \
             patch.object(daw, "common_locations", return_value=[]), \
             patch.object(daw.shutil, "which", return_value=None):
            client = TestClient(server.app)
            result = client.get("/api/daws")
            self.assertEqual(200, result.status_code, result.text)
            self.assertEqual({"audacity", "waveform"},
                             {item["id"] for item in result.json()["targets"]})
            located = client.post("/api/daws/audacity/locate",
                                  json={"path": str(self.audacity)})
            self.assertEqual(200, located.status_code, located.text)
            choice = client.post("/api/daws/select", json={"target": "audacity"})
            self.assertEqual(200, choice.status_code, choice.text)
            result = client.get("/api/daws")
            self.assertEqual("audacity", result.json()["selected"])
            self.assertEqual(str(self.audacity.resolve()),
                             result.json()["installed"]["audacity"])
            self.assertIsNone(result.json()["installed"]["waveform"])
            unknown = client.post("/api/daws/nope/detect")
            self.assertEqual(400, unknown.status_code)

    def test_audacity_export_preserves_all_six_stems(self):
        ident = "abcdef012345"
        folder = self.root / "jobs" / ident
        stem_folder = folder / "stems"
        stem_folder.mkdir(parents=True)
        files = []
        for name in projects.ORDER:
            filename = f"song_({name})_htdemucs_6s.wav"
            (stem_folder / filename).write_bytes(name.encode())
            files.append(filename)
        record = {
            "id": ident, "files": files, "title": "A Song",
            "stems": projects.default_settings(files),
        }
        export = projects.export_daw(self.root, record, "audacity")
        manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("audacity", manifest["target"])
        self.assertTrue((export / "IMPORT-IN-AUDACITY.txt").is_file())
        for idx, name in enumerate(projects.ORDER, 1):
            self.assertEqual(name.encode(), (export / f"{idx:02d} - {name}.wav").read_bytes())
        self.assertEqual(6, len(list(stem_folder.glob("*.wav"))))
        new_export = projects.export_daw(self.root, record, "audacity")
        self.assertNotEqual(export, new_export)


if __name__ == "__main__":
    unittest.main()
