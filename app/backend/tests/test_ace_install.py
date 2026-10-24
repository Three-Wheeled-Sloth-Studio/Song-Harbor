"""ACE Base installer checks without downloading checkpoint weights."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ace_install import Installer, MODEL, REPOSITORY, checkpoint_root, model_complete

class InstallerTests(unittest.TestCase):
    def test_default_root_is_ace_not_song_harbor(self):
        with tempfile.TemporaryDirectory() as temp:
            ace=Path(temp)/"Tools"/"ACE-Step"
            self.assertEqual(checkpoint_root(ace,{}), (ace/"checkpoints").resolve())

    def test_override_and_dotenv_root(self):
        with tempfile.TemporaryDirectory() as temp:
            ace=Path(temp)/"ACE"
            ace.mkdir()
            (ace/".env").write_text("ACESTEP_CHECKPOINTS_DIR=weights\\n")
            self.assertEqual(checkpoint_root(ace,{}), (ace/"weights").resolve())
            custom=Path(temp)/"shared_models"
            self.assertEqual(checkpoint_root(ace,{"ACESTEP_CHECKPOINTS_DIR":str(custom)}),custom.resolve())

    def test_incomplete_checkpoint_is_not_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            root.mkdir(exist_ok=True)
            (root/"config.json").write_text(json.dumps({"is_turbo":False}))
            self.assertFalse(model_complete(root))
            (root/"model.safetensors").write_bytes(b"test weights")
            self.assertTrue(model_complete(root))
            (root/"config.json").write_text(json.dumps({"is_turbo":True}))
            self.assertFalse(model_complete(root))

    def test_install_requires_explicit_complete_ace_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            manager=Installer(Path(temp))
            self.assertEqual(manager.inspect()["phase"],"idle")
            with self.assertRaises(ValueError):
                manager.install()

    def test_no_arbitrary_model_repository(self):
        self.assertEqual(MODEL,"acestep-v15-base")
        self.assertEqual(REPOSITORY,"ACE-Step/acestep-v15-base")

if __name__=="__main__":
    unittest.main()
