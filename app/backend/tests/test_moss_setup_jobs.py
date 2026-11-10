"""No-download tests for the in-app MOSS setup controller."""
import sys
import io
import hashlib
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import moss_setup_jobs
import moss_setup_worker


class MossSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app = Path(tmp.name) / "app"
        self.models = Path(tmp.name) / "models"
        self.app.mkdir()
        self.models.mkdir()
        moss_setup_jobs._JOB.update({"process": None, "operation": None,
                                     "model": None, "distro": None, "log": None,
                                     "state": "idle", "error": ""})

    def test_never_download_without_approval(self):
        with patch.object(moss_setup_jobs.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "Approve"):
                moss_setup_jobs.start(self.app, self.models, "Ubuntu", "runtime", None, False)
            spawn.assert_not_called()

    def test_only_allowlisted_checkpoint_ids(self):
        with self.assertRaisesRegex(ValueError, "Unsupported checkpoint"):
            moss_setup_jobs.start(self.app, self.models, "Ubuntu", "checkpoint",
                                  "arbitrary/repo", True)

    def test_status_idle_has_no_download_side_effects(self):
        before = list(self.models.iterdir())
        result = moss_setup_jobs.status(self.app, self.models)
        self.assertEqual(result["state"], "idle")
        self.assertFalse(result["runtime_installed"])
        self.assertTrue(all(not item["installed"] for item in result["catalog"]))
        self.assertEqual(list(self.models.iterdir()), before)

    def test_worker_requires_existing_dedicated_root(self):
        with patch.object(sys, "argv", ["moss_setup_worker.py", "runtime", "/", "none"]):
            with self.assertRaises(ValueError):
                moss_setup_worker.main()

    def test_standalone_uv_bootstrap_never_uses_venv(self):
        payload = b"dummy-uv-executable"
        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w:gz") as archive:
            entry = tarfile.TarInfo("uv-x86_64-unknown-linux-gnu/uv")
            entry.size = len(payload)
            archive.addfile(entry, io.BytesIO(payload))
        archive_bytes = tar_bytes.getvalue()
        digest = hashlib.sha256(archive_bytes).hexdigest()
        with patch.object(moss_setup_worker.platform, "system", return_value="Linux"), \
             patch.object(moss_setup_worker.platform, "machine", return_value="x86_64"), \
             patch.object(moss_setup_worker, "_download_bytes", side_effect=[
                 (digest + "  uv-x86_64-unknown-linux-gnu.tar.gz").encode(), archive_bytes
             ]), patch.object(moss_setup_worker.subprocess, "run") as runner:
            binary = moss_setup_worker.ensure_uv(self.models)
            self.assertEqual(Path(binary).read_bytes(), payload)
            self.assertEqual(runner.call_count, 1)
            self.assertEqual(runner.call_args.args[0][-1], "--version")

    def test_bootstrap_refuses_checksum_mismatch_without_installing(self):
        with patch.object(moss_setup_worker.platform, "system", return_value="Linux"), \
             patch.object(moss_setup_worker.platform, "machine", return_value="x86_64"), \
             patch.object(moss_setup_worker, "_download_bytes", side_effect=[b"0"*64, b"invalid"]):
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                moss_setup_worker.ensure_uv(self.models)
        self.assertFalse((self.models / "tools" / ("uv-" + moss_setup_worker.UV_VERSION)).exists())

    def test_runtime_uses_pinned_sglang_revision(self):
        self.assertEqual(len(moss_setup_worker.SGLANG_REVISION), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in moss_setup_worker.SGLANG_REVISION))


if __name__ == "__main__":
    unittest.main()
