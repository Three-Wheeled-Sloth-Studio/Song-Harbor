"""Offline verification for pinned CrispASR + Q4 GGUF installation."""
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import moss_q4_installer as installer


class FakeResponse:
    def __init__(self, data, code=200, headers=None):
        self.body=io.BytesIO(data)
        self.status=code
        self.headers=headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, n=-1): return self.body.read(n)


class Q4InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.app=self.root/"app"
        self.models=self.root/"models"
        self.app.mkdir()
        self.models.mkdir()
        installer._CANCEL.clear()
        installer._JOB.update(state="idle",thread=None,kind=None,
                              downloaded=0,total=0,error="",started=None)

    def test_approval_required_before_network_or_files(self):
        with patch.object(installer.urllib.request,"urlopen") as network:
            with self.assertRaisesRegex(ValueError,"Approve"):
                installer.start(self.app,self.models,"model",False)
            network.assert_not_called()
        self.assertEqual(list(self.models.iterdir()),[])

    def test_pinned_runtime_release_identity(self):
        self.assertEqual(installer.RUNTIME_VERSION,"v0.8.53")
        self.assertEqual(len(installer.RUNTIME_SHA256),64)
        self.assertEqual(installer.RUNTIME_BYTES,714327349)
        self.assertTrue(installer.RUNTIME_URL.endswith("crispasr-windows-x86_64-cuda126.zip"))

    def test_metadata_requires_immutable_lfs_sha(self):
        payload={"sha":"a"*40,"siblings":[{"rfilename":installer.MODEL_FILE,
                     "size":4500000000,"lfs":{"sha256":"b"*64,"size":4500000000}}]}
        with patch.object(installer.urllib.request,"urlopen",
                          return_value=FakeResponse(json.dumps(payload).encode())):
            revision,digest,size,url=installer._metadata()
        self.assertEqual(revision,"a"*40)
        self.assertEqual(digest,"b"*64)
        self.assertEqual(size,4500000000)
        self.assertIn("/resolve/"+revision+"/",url)

    def test_metadata_refuses_missing_lfs_checksum(self):
        payload={"sha":"a"*40,"siblings":[{"rfilename":installer.MODEL_FILE,
                     "size":4500000000}]}
        with patch.object(installer.urllib.request,"urlopen",
                          return_value=FakeResponse(json.dumps(payload).encode())):
            with self.assertRaisesRegex(RuntimeError,"SHA-256"):
                installer._metadata()

    def test_download_hash_verified_and_identity_recorded(self):
        raw=b"testdownload"*50
        dest=self.models/"gguf"/"test.gguf"
        sha=hashlib.sha256(raw).hexdigest()
        with patch.object(installer.urllib.request,"urlopen",return_value=FakeResponse(raw)):
            part=installer._download("https://example.org/pinned",dest,len(raw),sha)
        self.assertEqual(part.read_bytes(),raw)
        self.assertFalse(dest.exists())
        marker=json.loads(part.with_name(part.name+".json").read_text())
        self.assertEqual(marker["sha256"],sha)

    def test_complete_staging_verifies_without_network_request(self):
        payload=b"completed-asset"*100
        dest=self.models/"gguf"/"test.gguf"
        dest.parent.mkdir()
        part=dest.with_name(dest.name+".part")
        part.write_bytes(payload)
        digest=hashlib.sha256(payload).hexdigest()
        marker={"sha256":digest,"size":len(payload),"source":"https://example.org/revision"}
        part.with_name(part.name+".json").write_text(json.dumps(marker))
        with patch.object(installer.urllib.request,"urlopen") as network:
            result=installer._download(marker["source"],dest,marker["size"],digest)
            self.assertEqual(result,part)
            network.assert_not_called()

    def test_runtime_archive_duplicate_flattened_paths_refused(self):
        archive=self.models/"crispasr.zip"
        with zipfile.ZipFile(archive,"w") as z:
            z.writestr("a/crispasr.exe",b"runtime")
            z.writestr("a/common.dll",b"one")
            z.writestr("b/common.dll",b"two")
        with self.assertRaisesRegex(RuntimeError,"Duplicate extracted path"):
            installer._install_runtime(self.models,archive)
        self.assertFalse(installer._destination(self.models,"runtime").is_file())

    def test_resume_rejects_wrong_source_and_no_network(self):
        dest=self.models/"gguf"/"test.gguf"
        dest.parent.mkdir()
        part=dest.with_name(dest.name+".part")
        part.write_bytes(b"partial")
        part.with_name(part.name+".json").write_text(json.dumps({
             "sha256":"a"*64,"size":100,"source":"https://example.org/old"}))
        with patch.object(installer.urllib.request,"urlopen") as network:
            with self.assertRaisesRegex(RuntimeError,"identity"):
                installer._download("https://example.org/new",dest,100,"b"*64)
            network.assert_not_called()

    def test_runtime_extracts_verified_zip_without_running_binary(self):
        archive=self.models/"crispasr.zip"
        with zipfile.ZipFile(archive,"w") as z:
            z.writestr("crispasr-windows/crispasr.exe",b"program")
            z.writestr("crispasr-windows/cudart64_12.dll",b"runtime")
        with patch.object(installer.moss_q4_experiment.subprocess,"Popen") as spawn:
            installer._install_runtime(self.models,archive)
            spawn.assert_not_called()
        self.assertTrue(installer._installed(self.models,"runtime"))

    def test_unsafe_zip_entry_rejected(self):
        archive=self.models/"crispasr.zip"
        with zipfile.ZipFile(archive,"w") as z:
            z.writestr("crispasr-windows/crispasr.exe",b"program")
            z.writestr("crispasr-windows/../../outside.dll",b"untrusted")
        with self.assertRaisesRegex(RuntimeError,"Unsafe ZIP"):
            installer._install_runtime(self.models,archive)
        self.assertFalse(installer._destination(self.models,"runtime").exists())


if __name__=="__main__":
    unittest.main()
