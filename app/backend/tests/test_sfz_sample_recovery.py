"""SFZ sample recovery tests: local-first and curated-only, no live network."""
from __future__ import annotations
import sys
import tempfile
import unittest
import zipfile
import json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sfz_pack
import sfz_sample_recovery as recovery

FLAC=b"fLaC"+b"\x00"*12

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.archive=self.root/"kit.zip"

    def install(self,files,curated="big-rusty-drums"):
        with zipfile.ZipFile(self.archive,"w",zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        return sfz_pack.install_zip(self.root,self.archive,"Recovery kit",curated_id=curated)

    def test_missing_curated_instrument_can_be_staged_for_recovery(self):
        result=self.install({"Programs/Kit.sfz":"<region> sample=../Samples/kick/kick.flac"})
        self.assertEqual(result["instruments"],0)
        self.assertEqual(result["unavailable_program_count"],1)

    def test_local_case_mismatch_is_repaired_before_network(self):
        result=self.install({
            "Programs/Kit.sfz":"<region> sample=../Samples/kick/Kick.flac",
            "Samples/kick/kick.flac":FLAC,
        })
        # On case-sensitive systems, audit reports the note unresolved. On
        # Windows, equivalent casing may already be treated as resolved.
        with patch.object(recovery,"_download_exact",side_effect=AssertionError("Network not allowed")):
            fixed=recovery.repair(self.root,result["pack_id"])
        self.assertEqual(fixed["playable"],1)
        self.assertEqual(fixed["from_publisher"],0)
        self.assertTrue((self.root/"instrument-packs"/result["pack_id"]/"Samples"/"kick"/"Kick.flac").exists() or
                        (self.root/"instrument-packs"/result["pack_id"]/"Samples"/"kick"/"kick.flac").exists())

    def test_explicit_approved_publisher_exact_file(self):
        result=self.install({"Programs/Kit.sfz":"<region> sample=../Samples/kick/kick.flac"})
        def fake_fetch(entry,relative,target):
            self.assertEqual(entry["id"],"big-rusty-drums")
            self.assertEqual(str(relative),"Samples/kick/kick.flac")
            target.write_bytes(FLAC)
            return True
        with patch.object(recovery,"_download_exact",side_effect=fake_fetch):
            fixed=recovery.repair(self.root,result["pack_id"])
        self.assertEqual(fixed["from_publisher"],1)
        self.assertEqual(fixed["playable"],1)
        self.assertEqual(fixed["unavailable_program_count"],0)
        manifest=json.loads((self.root/"instrument-packs"/result["pack_id"]/"manifest.json").read_text())
        self.assertEqual([x["name"] for x in manifest["instruments"]],["Kit"])
        self.assertTrue(manifest["repair_provenance"]["official_files"])

    def test_unapproved_pack_never_attempts_publisher_download(self):
        # Noncurated incomplete packs fail before any repair or network action.
        with patch.object(recovery,"_download_exact",side_effect=AssertionError("Network forbidden")):
            with self.assertRaisesRegex(ValueError,"no complete instrument programs"):
                self.install({"Programs/Kit.sfz":"<region> sample=../Samples/kick/kick.flac"},curated="")

    def test_relative_sample_rejects_arbitrary_paths(self):
        self.assertIsNone(recovery.relative_sample("other error"))
        self.assertIsNone(recovery.relative_sample(recovery.MISSING+"../../secret.flac"))
        self.assertIsNone(recovery.relative_sample(recovery.MISSING+"../Samples/foo.exe"))
        self.assertEqual(str(recovery.relative_sample(recovery.MISSING+"../Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac")),
                         "Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac")

    def test_no_publisher_redirects(self):
        self.assertIsNone(recovery.NoRedirect().redirect_request(None,None,None,None,None,None))
        self.assertEqual(recovery.official_base({
            "source_page":"https://github.com/sfzinstruments/karoryfer.big-rusty-drums",
            "version":"1.100"}),"https://raw.githubusercontent.com/sfzinstruments/karoryfer.big-rusty-drums/v1.100/")
        with self.assertRaisesRegex(ValueError,"allowlist"):
            recovery.official_base({"source_page":"https://github.com/other/malware","version":"1.100"})

if __name__=="__main__":
    unittest.main()
