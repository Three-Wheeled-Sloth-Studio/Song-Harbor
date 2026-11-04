"""SFZ importer security and library integration tests: no real sampler required."""
from __future__ import annotations
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sfz_pack
import instrument_library


class SFZPackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.archive=self.root/"instrument.zip"

    def make_zip(self,files):
        with zipfile.ZipFile(self.archive,"w",zipfile.ZIP_DEFLATED) as z:
            for name,payload in files.items():
                z.writestr(name,payload)

    def test_install_catalogue_and_resolve(self):
        self.make_zip({"Cello.sfz":"<region> sample=samples/c4.wav key=60",
                       "samples/c4.wav":b"sample fixture"})
        outcome=sfz_pack.install_zip(self.root,self.archive,"Test Cello")
        pack=outcome["pack_id"]
        found=instrument_library.catalogue(self.root)
        self.assertTrue(any(row["id"]==pack and row["engine"]=="sfz"
                            for row in found["packs"]))
        instrument=next(x for x in found["instruments"] if x["pack_id"]==pack)
        self.assertEqual(instrument["engine"],"sfz")
        _, definition=instrument_library.resolve_instrument(self.root,pack,instrument["id"])
        self.assertEqual(definition.name,"Cello.sfz")
        manifest=json.loads((definition.parent/"manifest.json").read_text())
        self.assertEqual(len(manifest["sha256"]),64)

    def test_archive_traversal_rejected_without_install(self):
        self.make_zip({"../outside.sfz":"<region> sample=x.wav",
                       "x.wav":b"x"})
        with self.assertRaisesRegex(ValueError,"unsafe|traversal"):
            sfz_pack.install_zip(self.root,self.archive,"Unsafe")

    def test_unresolved_sample_rejected(self):
        self.make_zip({"Bad.sfz":"<region> sample=missing.wav"})
        with self.assertRaisesRegex(ValueError,"missing or external"):
            sfz_pack.install_zip(self.root,self.archive,"Bad")

    def test_external_directive_rejected(self):
        self.make_zip({"Unsafe.sfz":"#include \"../external.sfz\"",
                       "x.wav":b"x"})
        with self.assertRaisesRegex(ValueError,"unsupported preprocessing"):
            sfz_pack.install_zip(self.root,self.archive,"Unsafe")

    def test_case_insensitive_duplicate_rejected(self):
        self.make_zip({"A.sfz":"<region> sample=x.wav",
                       "a.sfz":"<region> sample=x.wav","x.wav":b"x"})
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            sfz_pack.inspect_archive(self.archive)

    def test_declared_unpacked_limit_rejected_before_extraction(self):
        from unittest.mock import patch
        self.make_zip({"Cello.sfz": "<region> sample=c4.wav",
                       "c4.wav": b"0" * 256})
        with patch.object(sfz_pack, "MAX_UNPACKED_BYTES", 60):
            with self.assertRaisesRegex(ValueError, "uncompressed size|Oversized"):
                sfz_pack.inspect_archive(self.archive)

    def test_relative_default_path_and_readme_import(self):
        self.make_zip({"Cello.sfz": "<control> default_path=samples/\n<region> sample=c4.wav",
                       "samples/c4.wav": b"sample",
                       "LICENSE": "CC0",
                       "README.txt": "Sample instrument"})
        result = sfz_pack.install_zip(self.root, self.archive, "Default path sample")
        self.assertEqual(result["instruments"], 1)

    def test_parent_default_path_rejected(self):
        self.make_zip({"Cello.sfz": "<control> default_path=../outside/\n<region> sample=c4.wav",
                       "samples/c4.wav": b"sample"})
        with self.assertRaisesRegex(ValueError, "escapes"):
            sfz_pack.install_zip(self.root, self.archive, "Unsafe defaults")

    def test_failed_install_does_not_leave_pack_folder(self):
        self.make_zip({"Cello.sfz": "<region> sample=missing.wav"})
        with self.assertRaises(ValueError):
            sfz_pack.install_zip(self.root, self.archive, "Broken")
        pack_folder = self.root / "instrument-packs"
        self.assertEqual(list(pack_folder.iterdir()), [])

    def test_missing_pack_is_not_in_catalogue(self):
        self.assertEqual(instrument_library.catalogue(self.root)["packs"][0]["engine"],"synthetic")


if __name__=="__main__":
    unittest.main()
