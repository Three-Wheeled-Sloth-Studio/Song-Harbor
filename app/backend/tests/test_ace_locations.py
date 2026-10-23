"""ACE discovery tests use temporary installs, never real machine paths."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ace_locations


class AceLocationTests(unittest.TestCase):
    def make_install(self, folder: Path):
        python = folder / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        script = folder / "acestep" / "api_server.py"
        script.parent.mkdir(parents=True)
        script.write_text("pass")
        return folder

    def test_finds_install_without_hardcoded_drive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install = self.make_install(root / "SomeApps" / "Tools" / "ACE-Step-1.5")
            with patch.object(ace_locations, "candidate_roots", return_value=[root / "SomeApps" / "Tools"]):
                self.assertEqual(ace_locations.discover_installation(root / "app"), install.resolve())

    def test_recognizes_named_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install = self.make_install(root / "Apps" / "ACE-Step-1.5-main")
            with patch.object(ace_locations, "candidate_roots", return_value=[root / "Apps"]):
                self.assertEqual(ace_locations.discover_installation(root), install.resolve())

    def test_does_not_accept_arbitrary_named_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_install(root / "Apps" / "unrelated-package")
            with patch.object(ace_locations, "candidate_roots", return_value=[root / "Apps"]):
                self.assertIsNone(ace_locations.discover_installation(root))

    def test_override_is_respected_and_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            found = self.make_install(root / "Apps" / "ACE-Step")
            with patch.object(ace_locations, "candidate_roots", return_value=[root / "Apps"]):
                with patch.dict("os.environ", {"SONG_HARBOR_ACE_HOME": str(root / "missing")}):
                    self.assertIsNone(ace_locations.discover_installation(root))
                with patch.dict("os.environ", {"SONG_HARBOR_ACE_HOME": str(found)}):
                    self.assertEqual(ace_locations.discover_installation(root), found.resolve())


if __name__ == "__main__":
    unittest.main()
