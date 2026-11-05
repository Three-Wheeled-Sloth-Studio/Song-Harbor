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

    def test_sfz_builtin_silence_does_not_require_audio_file(self):
        self.make_zip({
            "Programs/Kit.sfz": (
                "<region> sample=*silence key=24\\n"
                "<region> sample=../Samples/Kick.wav key=36\\n"
            ),
            "Samples/Kick.wav": b"audio fixture",
        })
        result=sfz_pack.install_zip(self.root,self.archive,"Silence region")
        self.assertEqual(result["instruments"],1)

    def test_fake_silence_filename_still_rejected(self):
        self.make_zip({"Kit.sfz":"<region> sample=*silence.wav key=24"})
        with self.assertRaisesRegex(ValueError,"missing or external sample"):
            sfz_pack.install_zip(self.root,self.archive,"Not built-in silence")

    def test_unresolved_sample_rejected(self):
        self.make_zip({"Bad.sfz":"<region> sample=missing.wav"})
        with self.assertRaisesRegex(ValueError,"missing or external"):
            sfz_pack.install_zip(self.root,self.archive,"Bad")

    def test_external_directive_rejected(self):
        self.make_zip({"Unsafe.sfz":"#include \"../external.sfz\"",
                       "x.wav":b"x"})
        with self.assertRaisesRegex(ValueError,"missing or external include"):
            sfz_pack.install_zip(self.root,self.archive,"Unsafe")

    def test_case_insensitive_duplicate_rejected(self):
        self.make_zip({"A.sfz":"<region> sample=x.wav",
                       "a.sfz":"<region> sample=x.wav","x.wav":b"x"})
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            sfz_pack.inspect_archive(self.archive)

    def test_large_archive_limits_remain_explicit_and_bounded(self):
        self.assertEqual(sfz_pack.MAX_ARCHIVE_BYTES,4*1024**3)
        self.assertEqual(sfz_pack.MAX_UNPACKED_BYTES,8*1024**3)
        from unittest.mock import patch
        self.make_zip({"Kit.sfz":"<region> sample=kick.wav","kick.wav":b"sample"})
        with patch.object(sfz_pack,"MAX_ARCHIVE_BYTES",self.archive.stat().st_size-1):
            with self.assertRaisesRegex(ValueError,"too large"):
                sfz_pack.inspect_archive(self.archive)

    def test_import_refuses_insufficient_disk_without_leaving_pack(self):
        from unittest.mock import patch
        from collections import namedtuple
        self.make_zip({"Kit.sfz":"<region> sample=kick.wav","kick.wav":b"sample"})
        Space=namedtuple("Space",["total","used","free"])
        with patch.object(sfz_pack.shutil,"disk_usage",return_value=Space(1024,1023,1)):
            with self.assertRaisesRegex(ValueError,"Not enough disk space"):
                sfz_pack.install_zip(self.root,self.archive,"No space")
        self.assertEqual(list((self.root/"instrument-packs").iterdir()),[])

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

    def test_sibling_sample_folder_allowed(self):
        self.make_zip({
            "Programs/Cello.sfz": "<control> default_path=../Samples/\n<region> sample=C4.wav",
            "Samples/C4.wav": b"sample",
            "Programs/Cello.nki": b"Kontakt companion not imported",
            "README": "Original publisher notes"
        })
        outcome = sfz_pack.install_zip(self.root, self.archive, "Cello")
        self.assertEqual(outcome["instruments"], 1)
        imported = next((self.root / "instrument-packs").iterdir())
        self.assertFalse((imported / "Programs" / "Cello.nki").exists())
        self.assertTrue((imported / "Programs" / "Cello.sfz").is_file())
        self.assertTrue((imported / "Samples" / "C4.wav").is_file())

    def test_muldjord_style_txt_includes_macros_and_same_line_directives(self):
        """Text fragments and sample macros are data, not external dependencies."""
        self.make_zip({
            "Kit/Stereo/Kit.sfz": (
                '#include "../Data/keymap.txt"\n'
                '#include "../Data/macro.txt"\n'
                '<global> #include "../Data/stereo/Kdrum.txt" '
                '#include "../Data/stereo/Snare.txt"\n'
            ),
            "Kit/Data/keymap.txt": "#define $kick 36\n#define $snare 38\n",
            "Kit/Data/macro.txt": (
                "#define $sample_dir ../Samples\n"
                "#define $ext flac\n"
                "default_path=$sample_dir/\n"
            ),
            "Kit/Data/stereo/Kdrum.txt": (
                '#define $mic OHL\n'
                '#include "../Data/group/Kdrum.txt"\n'
            ),
            "Kit/Data/group/Kdrum.txt": (
                '#define $instr Kdrum\n'
                '<region> key=$kick sample=$instr/1-$instr-$mic.$ext '
                'seq_length=2 seq_position=1\n'
            ),
            "Kit/Data/stereo/Snare.txt": (
                '#define $mic OHR\n'
                '#include "../Data/group/Snare.txt"\n'
            ),
            "Kit/Data/group/Snare.txt": (
                '#define $instr Snare\n'
                '<region> key=$snare sample=$instr/1-$instr-$mic.$ext\n'
            ),
            "Kit/Samples/Kdrum/1-Kdrum-OHL.flac": b"kick",
            "Kit/Samples/Snare/1-Snare-OHR.flac": b"snare",
            "Kit/README.txt": b"Informational, not executed",
        })
        result=sfz_pack.install_zip(self.root,self.archive,"Muldjord pattern")
        self.assertEqual(result["instruments"],1)
        self.assertEqual(result["unavailable_program_count"],0)
        folder=next((self.root/"instrument-packs").iterdir())
        self.assertTrue((folder/"Kit"/"Data"/"macro.txt").is_file())

    def test_muldjord_txt_include_missing_sample_is_still_rejected(self):
        self.make_zip({
            "Stereo/Kit.sfz": (
                '#include "../Data/macro.txt"\n'
                '#include "../Data/region/Kick.txt"\n'
            ),
            "Data/macro.txt": "#define $sample_dir ../Samples\n"
                              "#define $ext flac\n"
                              "default_path=$sample_dir/\n",
            "Data/region/Kick.txt": '#define $instr Kick\n'
                                    '<region> sample=$instr/1.$ext\n',
        })
        with self.assertRaisesRegex(ValueError,"missing or external sample"):
            sfz_pack.install_zip(self.root,self.archive,"Incomplete kit")

    def test_txt_include_cannot_escape_pack(self):
        self.make_zip({
            "Stereo/Kit.sfz": '#include "../../external.txt"\n',
            "Data/region.txt": "<region> sample=kick.wav\n",
            "Samples/kick.wav": b"sample",
        })
        with self.assertRaisesRegex(ValueError,"missing or external include"):
            sfz_pack.install_zip(self.root,self.archive,"Unsafe text")

    def test_big_rusty_style_nested_includes_and_key_definitions(self):
        self.make_zip({
            "Programs/02-basic.sfz": (
                '<control>\n#include "keymap/keymap.sfz"\n'
                '#define $ht_init 127\n'
                '#include "mappings/kick.sfz"\n'
            ),
            "Programs/keymap/keymap.sfz":"#define $kickkey 36\n",
            "Programs/mappings/kick.sfz":(
                '<master> key=$kickkey\n'
                '#include "mappings/kick_hits.sfz"\n'
            ),
            "Programs/mappings/kick_hits.sfz": (
                "<region> sample=../Samples/kick/kick_vl1.flac\n"
            ),
            "Samples/kick/kick_vl1.flac":b"sample bytes",
            "Presets/com.Plogue.Aria/Big Rusty Drums.plg":b"sampler preset",
        })
        outcome=sfz_pack.install_zip(self.root,self.archive,"Rusty Fixture")
        self.assertEqual(outcome["instruments"],1)
        pack=next((self.root/"instrument-packs").iterdir())
        manifest=json.loads((pack/"manifest.json").read_text())
        self.assertEqual(manifest["instruments"][0]["name"],"02-basic")
        self.assertFalse((pack/"Presets").exists())

    def test_missing_optional_articulation_does_not_block_complete_basic_kit(self):
        self.make_zip({
            "Programs/01-full.sfz": (
                '#include "mappings/kick_rc.sfz"\n'
            ),
            "Programs/02-basic.sfz": (
                '#include "mappings/kick_basic.sfz"\n'
            ),
            "Programs/mappings/kick_rc.sfz": (
                "<region> sample=../Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac\n"
            ),
            "Programs/mappings/kick_basic.sfz": (
                "<region> sample=../Samples/kick_24/kick/kick_vl1_rr1.flac\n"
            ),
            "Samples/kick_24/kick/kick_vl1_rr1.flac":b"sample",
        })
        result=sfz_pack.install_zip(self.root,self.archive,"Partially complete kit")
        self.assertEqual(result["instruments"],1)
        self.assertEqual(result["unavailable_program_count"],1)
        self.assertEqual(result["unavailable_programs"][0]["name"],"01-full")
        self.assertIn("k_rc_vl1_rr1.flac",result["unavailable_programs"][0]["reason"])
        pack=next((self.root/"instrument-packs").iterdir())
        manifest=json.loads((pack/"manifest.json").read_text())
        self.assertEqual([row["name"] for row in manifest["instruments"]],["02-basic"])

    def test_missing_sample_still_rejects_if_every_program_is_incomplete(self):
        self.make_zip({
            "Programs/01-full.sfz":'#include "mapping.sfz"\\n',
            "Programs/mapping.sfz":"<region> sample=../Samples/absent.flac\\n",
        })
        with self.assertRaisesRegex(ValueError,"no complete instrument programs"):
            sfz_pack.install_zip(self.root,self.archive,"Broken kit")
        self.assertEqual(list((self.root/"instrument-packs").iterdir()),[])

    def test_include_cannot_escape_imported_pack(self):
        self.make_zip({
            "Programs/Kit.sfz":'#include "../../external.sfz"\n',
            "Samples/kick.wav":b"data",
        })
        with self.assertRaisesRegex(ValueError,"missing or external include"):
            sfz_pack.install_zip(self.root,self.archive,"Invalid external include")

    def test_unknown_directive_rejected(self):
        self.make_zip({"Kit.sfz":"#unknown /tmp/outside\n<region> sample=Kick.wav",
                       "Kick.wav":b"sample"})
        with self.assertRaisesRegex(ValueError,"unsupported preprocessing"):
            sfz_pack.install_zip(self.root,self.archive,"Unsupported directive")

    def test_non_audio_support_files_are_skipped_not_extracted(self):
        self.make_zip({
            "Programs/Kit.sfz":"<region> sample=../Samples/Kick.flac key=36",
            "Samples/Kick.flac":b"sample data fixture",
            "GUI/Kit.png":b"graphic",
            "Presets/com.Plogue.Aria/Kit.plg":b"sampler preset metadata",
            "Presets/com.Plogue.Aria/Kit.xml":b"sampler companion",
            ".DS_Store":b"mac metadata",
            "__MACOSX/._Kit.sfz":b"mac resource fork",
        })
        result=sfz_pack.install_zip(self.root,self.archive,"Big Rusty fixture")
        self.assertEqual(result["instruments"],1)
        self.assertEqual(result["ignored_support_files"],5)
        destination=next((self.root/"instrument-packs").iterdir())
        self.assertTrue((destination/"Programs"/"Kit.sfz").is_file())
        self.assertTrue((destination/"Samples"/"Kick.flac").is_file())
        self.assertFalse((destination/"Presets"/"com.Plogue.Aria"/"Kit.plg").exists())
        self.assertFalse((destination/"__MACOSX").exists())

    def test_unsupported_sample_reference_still_rejected(self):
        self.make_zip({
            "Kit.sfz":"<region> sample=Kick.mp3 key=36",
            "Kick.mp3":b"unsupported audio",
        })
        with self.assertRaisesRegex(ValueError,"missing or external sample"):
            sfz_pack.install_zip(self.root,self.archive,"No MP3 support")

    def test_unsafe_support_file_path_still_rejected(self):
        self.make_zip({
            "Kit.sfz":"<region> sample=Kick.wav",
            "Kick.wav":b"sample",
            "../evil.plg":b"invalid path",
        })
        with self.assertRaisesRegex(ValueError,"traversal"):
            sfz_pack.install_zip(self.root,self.archive,"Unsafe")

    def test_parent_default_path_rejected(self):
        self.make_zip({"Cello.sfz": "<control> default_path=../outside/\n<region> sample=c4.wav",
                       "samples/c4.wav": b"sample"})
        with self.assertRaisesRegex(ValueError, "missing or external"):
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
