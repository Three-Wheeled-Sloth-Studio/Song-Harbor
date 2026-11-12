"""Snapshot validation without a running Q4 model or Song Harbor server."""
import io
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import moss_q4_snapshots as snapshots


def wave_bytes(seconds: float = 2.0, rate: int = 48000) -> bytes:
    buffer=io.BytesIO()
    with wave.open(buffer,"wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(3)
        stream.setframerate(rate)
        stream.writeframes(bytes([0]) * (round(seconds*rate)*6))
    return buffer.getvalue()


class SnapshotTests(unittest.TestCase):
    def test_crops_selection_and_keeps_source_unchanged(self):
        source=wave_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=snapshots.create(root,io.BytesIO(source),project_id="song",
                recipe_revision=hashlib.sha256(source).hexdigest(),section_ids=["chorus-1"],
                start_seconds=.5,end_seconds=1.5)
            loaded=snapshots.read(root,result["snapshot_id"])
            self.assertEqual(loaded["sha256"],result["sha256"])
            self.assertEqual(loaded["section_ids"],["chorus-1"])
            with wave.open(loaded["audio_path"],"rb") as wav:
                self.assertEqual(wav.getnframes(),48000)
            self.assertEqual(source,wave_bytes())

    def test_invalid_snapshot_reference_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                snapshots.read(Path(directory),"../../outside")

    def test_corrupted_snapshot_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=wave_bytes()
            result=snapshots.create(root,io.BytesIO(source),project_id="song",
                recipe_revision=hashlib.sha256(source).hexdigest(),section_ids=[],
                start_seconds=None,end_seconds=None)
            audio=root/"cache"/"moss-q4-snapshots"/(result["snapshot_id"]+".wav")
            with audio.open("ab") as stream:
                stream.write(b"X")
            with self.assertRaises(ValueError):
                snapshots.read(root,result["snapshot_id"])


if __name__=="__main__":
    unittest.main()
