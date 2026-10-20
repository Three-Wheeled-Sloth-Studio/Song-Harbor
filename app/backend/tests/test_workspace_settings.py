"""Machine-local location preference and safety regression tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workspace_settings


class WorkingFilesSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name) / "runtime"
        self.root.mkdir()
        self.target=Path(self.tmp.name) / "Google Drive" / "Song Harbor" / "Data"

    def test_default_then_stage_does_not_move_data(self):
        original=self.root / "data" / "jobs" / "abcdef012345"
        original.mkdir(parents=True)
        (original / "source.wav").write_bytes(b"untouched")
        self.assertEqual((self.root / "data").resolve(), workspace_settings.configured_data(self.root))
        result=workspace_settings.stage(self.root,str(self.target))
        self.assertTrue(result["restart_required"])
        self.assertFalse(result["migration_performed"])
        self.assertEqual(self.target.resolve(),workspace_settings.configured_data(self.root))
        self.assertFalse(self.target.exists())
        self.assertEqual(b"untouched",(original / "source.wav").read_bytes())

    def test_configuration_preserves_ffmpeg(self):
        config=workspace_settings.settings_path(self.root)
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"ffmpeg":{"bin_directory":"C:/Tools/ffmpeg"}}))
        workspace_settings.stage(self.root,str(self.target))
        self.assertEqual("C:/Tools/ffmpeg",workspace_settings.read(self.root)["ffmpeg"]["bin_directory"])

    def test_invalid_roots_and_repository_rejected(self):
        for path in [str(self.root),str(Path.home()),str(Path(self.root.anchor)),"relative/path"]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    workspace_settings.stage(self.root,path)
        repo=self.root / "checkout"
        repo.mkdir()
        (repo / ".git").mkdir()
        with self.assertRaises(ValueError):
            workspace_settings.stage(self.root,str(repo))

    def test_restart_status(self):
        self.assertFalse(workspace_settings.status(self.root,self.root/"data")["restart_required"])
        workspace_settings.stage(self.root,str(self.target))
        self.assertTrue(workspace_settings.status(self.root,self.root/"data")["restart_required"])


if __name__=="__main__":
    unittest.main()
