"""Instrument pack parsing, filtering, user-owned storage and MIDI bank safety."""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import instrument_library as lib


def _chunk(tag:bytes,body:bytes)->bytes:
    return tag+struct.pack("<I",len(body))+body+(b"\x00" if len(body)&1 else b"")


def make_sf2(path:Path)->None:
    def preset(name:str,program:int,bank:int)->bytes:
        return (name.encode()[:20].ljust(20,b"\x00")+
                struct.pack("<HHHIII",program,bank,0,0,0,0))
    data=preset("Low Cello",42,0)+preset("EOP",0,0)
    riff=_chunk(b"LIST",b"pdta"+_chunk(b"phdr",data))
    raw=b"RIFF"+struct.pack("<I",4+len(riff))+b"sfbk"+riff
    path.write_bytes(raw)


class InstrumentLibraryTests(unittest.TestCase):
    def test_sf2_preset_and_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            sample=root/"incoming.sf2"
            make_sf2(sample)
            presets=lib.sf2_presets(sample)
            self.assertEqual(presets,[{"name":"Low Cello","program":42,"bank":0}])
            installed=lib.install_sf2(root,sample,"Dark Chamber Strings")
            self.assertEqual(installed["instruments"],1)
            catalogue=lib.catalogue(root)
            self.assertEqual(catalogue["packs"][0]["id"],"song-harbor-core")
            self.assertTrue(any(i["name"]=="Low Cello" for i in catalogue["instruments"]))
            selection,selected_path=lib.resolve_instrument(root,installed["pack_id"],"p-0-b-0-n-42")
            self.assertEqual(selection["program"],42)
            self.assertTrue(selected_path.is_file())
            self.assertFalse(sample.exists())
            with self.assertRaises(ValueError):
                lib.resolve_instrument(root,installed["pack_id"],"../../bad")

    def test_invalid_soundfont_and_bad_manifest_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);bad=root/"bad.sf2";bad.write_bytes(b"not a soundfont"*20)
            with self.assertRaises(ValueError):lib.sf2_presets(bad)
            junk=lib.pack_root(root)/"bad";junk.mkdir(parents=True)
            (junk/"manifest.json").write_text(json.dumps({"id":"other","engine":"sf2"}))
            self.assertEqual(len(lib.catalogue(root)["packs"]),1)


if __name__=="__main__":
    unittest.main()
