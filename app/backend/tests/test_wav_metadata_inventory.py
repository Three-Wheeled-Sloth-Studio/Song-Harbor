"""Container inventory must report structural evidence without leaking tag values."""
from __future__ import annotations
import struct
import tempfile
import unittest
import wave
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wav_metadata_inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "stem.wav"
        with wave.open(str(self.path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(48000)
            out.writeframes(b"\x00\x00" * 128)

    def test_plain_wave_has_format_and_data_without_metadata(self):
        result = wav_metadata_inventory.inspect_wav(self.path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metadata_chunks"], 0)
        self.assertEqual([chunk["id"] for chunk in result["chunks"]], ["fmt ", "data"])

    def test_metadata_presence_only_does_not_reveal_contents(self):
        content = b"SECRET_IDENTIFIER"
        with self.path.open("ab") as out:
            out.write(b"iXML" + struct.pack("<I", len(content)) + content + b"\x00")
        result = wav_metadata_inventory.inspect_wav(self.path)
        self.assertEqual(result["metadata_chunks"], 1)
        self.assertNotIn("SECRET_IDENTIFIER", str(result))
        self.assertEqual(result["chunks"][-1]["bytes"], len(content))

    def test_malformed_length_does_not_read_audio_payload(self):
        with self.path.open("ab") as out:
            out.write(b"LIST" + struct.pack("<I", 999999))
        result = wav_metadata_inventory.inspect_wav(self.path)
        self.assertEqual(result["status"], "malformed")
        self.assertNotIn("LIST", [chunk["id"] for chunk in result["chunks"]])

    def test_unsupported_header_is_explicit(self):
        self.path.write_bytes(b"not a wave file")
        result = wav_metadata_inventory.inspect_wav(self.path)
        self.assertEqual(result["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
