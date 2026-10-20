"""DAW adapters: Audacity discovery, preserved Waveform config and portable export."""
import json
import os
import subprocess
import base64
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
        self.morningdaw = self.root / "Installed" / "MorningDAW" / "MorningDAW.exe"
        self.morningdaw.parent.mkdir(parents=True)
        self.morningdaw.write_bytes(b"test-fixture")

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

    def test_custom_apps_path_discovery(self):
        drive = self.root / "C"
        custom = drive / "Apps" / "Audacity"
        custom.mkdir(parents=True)
        exe = custom / "Audacity.exe"
        exe.write_bytes(b"fixture")
        with patch.object(daw, "available_drives", return_value=[drive]), \
             patch.object(daw, "windows_registry_locations", return_value=[]), \
             patch.object(daw, "windows_shortcut_locations", return_value=[]), \
             patch.object(daw.shutil, "which", return_value=None):
            self.assertEqual(str(exe.resolve()),
                             daw.resolve(self.root, target_id="audacity"))
        self.assertEqual(str(exe.resolve()), daw.configured(self.root, "audacity"))

    def test_deep_search_finds_nested_portable_installation(self):
        install = self.root / "C" / "Apps" / "Audio" / "Editors" / "Audacity 3.7"
        install.mkdir(parents=True)
        exe = install / "Audacity.exe"
        exe.write_bytes(b"fixture")
        with patch.object(daw, "search_roots", return_value=[self.root / "C" / "Apps"]):
            job = {"status": "running", "message": "starting", "target": "audacity"}
            daw.scan_existing(self.root, "audacity", job, max_directories=80, max_seconds=10)
        self.assertEqual("found", job["status"], job)
        self.assertEqual(str(exe.resolve()), job["executable"])
        self.assertEqual(str(exe.resolve()), daw.configured(self.root, "audacity"))

    def test_deep_search_does_not_scan_unrelated_junctions(self):
        app = self.root / "Apps"
        app.mkdir()
        (app / "node_modules").mkdir()
        (app / "node_modules" / "Audacity.exe").write_bytes(b"ignored")
        with patch.object(daw, "search_roots", return_value=[app]):
            job = {"status": "running", "message": "starting", "target": "audacity"}
            daw.scan_existing(self.root, "audacity", job, max_directories=20, max_seconds=3)
        self.assertEqual("not_found", job["status"])

    def test_audacity4_executable_names_and_folders(self):
        for filename in ("Audacity4.exe", "Audacity 4.exe", "Audacity3.exe",
                         "Audacity 3.exe", "Audacity.exe"):
            with self.subTest(filename=filename):
                candidate = self.root / filename
                candidate.write_bytes(b"fixture")
                self.assertEqual(candidate.resolve(),
                                 daw.verify_executable("audacity", candidate))
                self.assertEqual(candidate.resolve(),
                                 daw.verify_executable("audacity", self.root)
                                 if filename == "Audacity.exe" else candidate.resolve())
                candidate.unlink()
        invalid = self.root / "audacity-installer.exe"
        invalid.write_bytes(b"fixture")
        self.assertIsNone(daw.verify_executable("audacity", invalid))

    def test_shortcut_candidate_can_be_saved_for_audacity4(self):
        shortcut_target = self.root / "Audacity4.exe"
        shortcut_target.write_bytes(b"fixture")
        with patch.object(daw, "windows_registry_locations", return_value=[]), \
             patch.object(daw, "common_locations", return_value=[]), \
             patch.object(daw, "windows_shortcut_locations", return_value=[shortcut_target]), \
             patch.object(daw.shutil, "which", return_value=None):
            found = daw.resolve(self.root, target_id="audacity")
        self.assertEqual(str(shortcut_target.resolve()), found)
        self.assertEqual(found, daw.configured(self.root, "audacity"))

    @unittest.skipUnless(os.name == "nt", "Start Menu shortcut COM test requires Windows")
    def test_real_windows_start_menu_shortcut_resolution(self):
        """Exercise WScript COM + PowerShell using a synthetic Audacity 4 shortcut."""
        base = self.root / "Profile"
        menu = base / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        menu.mkdir(parents=True)
        app = self.root / "Audio Tools" / "Audacity 4"
        app.mkdir(parents=True)
        exe = app / "Audacity4.exe"
        exe.write_bytes(b"fixture")
        link = menu / "Audacity 4.lnk"
        import unittest.mock as mock
        script = (
            "$s=New-Object -ComObject WScript.Shell;"
            "$l=$s.CreateShortcut(" + json.dumps(str(link)) + ");"
            "$l.TargetPath=" + json.dumps(str(exe)) + ";$l.Save()"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", command],
            capture_output=True, text=True, timeout=15, creationflags=creationflags)
        self.assertEqual(0, proc.returncode, proc.stderr)
        with mock.patch.dict(os.environ, {"APPDATA": str(base), "PROGRAMDATA": str(self.root / "NoSharedMenu")}):
            targets = daw.windows_shortcut_locations("audacity")
        self.assertIn(exe.resolve(), [p.resolve() for p in targets])

    def test_morningdaw_discovery_configuration_and_portable_export(self):
        self.assertEqual(self.morningdaw.resolve(), daw.verify_executable("morningdaw", self.morningdaw))
        self.assertIsNone(daw.verify_executable("morningdaw", self.audacity))
        with patch.object(daw, "windows_registry_locations", return_value=[self.morningdaw.parent]), \
             patch.object(daw, "common_locations", return_value=[]), \
             patch.object(daw.shutil, "which", return_value=None):
            self.assertEqual(str(self.morningdaw.resolve()), daw.resolve(self.root, target_id="morningdaw"))
        self.assertEqual(str(self.morningdaw.resolve()), daw.configured(self.root, "morningdaw"))
        ident = "abcdef012345"
        folder = self.root / "jobs" / ident / "stems"
        folder.mkdir(parents=True)
        files = []
        for name in projects.ORDER:
            filename = f"song_({name})_htdemucs_6s.wav"
            (folder / filename).write_bytes(name.encode())
            files.append(filename)
        record = {"id": ident, "files": files, "title": "A Song",
                  "stems": projects.default_settings(files)}
        exported = projects.export_daw(self.root, record, "morningdaw")
        manifest = json.loads((exported / "manifest.json").read_text())
        self.assertEqual("morningdaw", manifest["target"])
        self.assertEqual(6, manifest["track_count"])
        self.assertTrue((exported / "IMPORT-IN-MORNINGDAW.txt").exists())
        for index, name in enumerate(projects.ORDER, 1):
            self.assertEqual(name.encode(), (exported / f"{index:02d} - {name}.wav").read_bytes())

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
            self.assertEqual({"audacity", "waveform", "morningdaw"},
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
