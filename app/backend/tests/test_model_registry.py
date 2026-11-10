"""Offline checkpoint discovery/registration regression tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import model_registry
import moss_runtime


class ModelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "app"
        self.root.mkdir()
        self.models = self.base / "shared-models"
        self.models.mkdir()

    def make_model(self, name="MOSS-Music-8B-Instruct", complete=True):
        folder = self.models / "vendor" / name
        folder.mkdir(parents=True)
        (folder / "config.json").write_text(json.dumps({"model_type": "moss_music"}))
        (folder / "model.safetensors.index.json").write_text(json.dumps({
            "weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}}))
        (folder / "model-00001-of-00002.safetensors").write_bytes(b"fake-weight")
        if complete:
            (folder / "model-00002-of-00002.safetensors").write_bytes(b"fake-weight")
        return folder

    def test_discovery_is_read_only_and_shows_incomplete(self):
        folder = self.make_model(complete=False)
        before = sorted(str(p) for p in self.models.rglob("*"))
        result = model_registry.list_models(self.root, self.models)
        self.assertEqual(len(result["discovered"]), 1)
        self.assertEqual(result["discovered"][0]["status"], "incomplete")
        self.assertEqual(before, sorted(str(p) for p in self.models.rglob("*")))
        with self.assertRaisesRegex(ValueError, "missing"):
            model_registry.register(self.root, str(folder))

    def test_registration_and_unlink_keep_checkpoint_bytes(self):
        folder = self.make_model()
        registered = model_registry.register(self.root, str(folder))
        self.assertTrue(registered["registered"])
        self.assertEqual(model_registry.list_models(self.root, self.models)["registered"][0]["id"], registered["id"])
        model_registry.unregister(self.root, registered["id"])
        self.assertTrue((folder / "model-00001-of-00002.safetensors").exists())

    def test_no_path_traversal_in_shards(self):
        folder = self.make_model()
        (folder / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"a": "../outside.safetensors"}}))
        self.assertIsNone(model_registry.inspect(folder))

    def test_upstream_architecture_names_detected(self):
        folder = self.models / "upstream-music"
        folder.mkdir()
        (folder / "config.json").write_text(json.dumps({"architectures": ["MossMusicModel"], "model_type": "custom"}))
        (folder / "model.safetensors").write_bytes(b"weights")
        self.assertEqual(model_registry.inspect(folder)["family"], "moss_music")
        other = self.models / "upstream-audio"
        other.mkdir()
        (other / "config.json").write_text(json.dumps({"architectures": ["MossAudioModel"], "model_type": "moss_audio"}))
        (other / "model.safetensors").write_bytes(b"weights")
        self.assertEqual(model_registry.inspect(other)["family"], "moss_audio")

    def test_unrecognized_model_does_not_register(self):
        folder = self.models / "random"
        folder.mkdir()
        (folder / "config.json").write_text('{"model_type":"other"}')
        (folder / "model.safetensors").write_bytes(b"data")
        self.assertEqual(model_registry.scan(self.models), [])

    def test_external_wsl_attach_checks_served_model_identity(self):
        folder = self.make_model()
        registered = model_registry.register(self.root, str(folder))
        expected = "songharbor-moss-" + registered["id"]
        with patch.object(moss_runtime, "_probe", return_value=False) as probe:
            with self.assertRaisesRegex(ValueError, "No matching MOSS service"):
                moss_runtime.attach(self.root, self.models, registered["id"])
            probe.assert_called_once_with(expected)
        self.assertIsNone(moss_runtime._ATTACHED["id"])

    def test_external_wsl_disconnect_does_not_kill_process(self):
        moss_runtime._ATTACHED.update({"id": "test", "model_name": "songharbor-moss-test"})
        try:
            with patch.object(moss_runtime, "_probe", return_value=True):
                self.assertEqual(moss_runtime.status()["status"], "connected")
            with patch.object(moss_runtime, "_stop_process") as stop:
                result = moss_runtime.unload()
                self.assertFalse(result["service_stopped"])
                stop.assert_not_called()
        finally:
            moss_runtime._ATTACHED.update({"id": None, "model_name": None})

    def test_load_refuses_without_explicit_trusted_code_approval(self):
        with self.assertRaisesRegex(ValueError, "explicitly approve"):
            moss_runtime.load(self.root, self.models, "unused", sys.executable, False)


if __name__ == "__main__":
    unittest.main()
