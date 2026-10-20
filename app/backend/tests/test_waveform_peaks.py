"""Cached waveform preview tests, including short audio and cache invalidation."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import waveform_peaks


class FakePipe:
    def __init__(self,raw):
        self.raw=raw
        self.position=0
    def read(self,n):
        block=self.raw[self.position:self.position+n]
        self.position+=len(block)
        return block
    def close(self): pass

class FakeProcess:
    def __init__(self,raw):
        self.stdout=FakePipe(raw)
    def wait(self,timeout=None): return 0
    def kill(self): pass

class WaveformTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"stem.wav"
        self.source.write_bytes(b"source media, treated as immutable")
        self.cache=self.root/"peaks"/"stem.json"

    def test_preview_shape_and_positive_negative_peaks(self):
        raw=struct.pack("<hhhhhhh",0,10000,-16000,500,-3000,18000,-500)
        with patch.object(waveform_peaks.subprocess,"Popen",return_value=FakeProcess(raw)):
            data=waveform_peaks.calculate(self.source,0.002,"ffmpeg")
        self.assertEqual(2048,data["bins"])
        self.assertEqual(2048,len(data["min"]))
        self.assertEqual(2048,len(data["max"]))
        self.assertLess(min(data["min"]),-0.4)
        self.assertGreater(max(data["max"]),0.5)
        self.assertEqual(0,data["min"][-1])

    def test_cache_reuse_and_invalidation(self):
        calls=[]
        def calculate(path,duration,ffmpeg):
            calls.append((duration,ffmpeg))
            return {"bins":waveform_peaks.BIN_COUNT,"min":[0],"max":[0]}
        with patch.object(waveform_peaks,"calculate",side_effect=calculate):
            a=waveform_peaks.get_or_create(self.source,self.cache,3.0,"ffmpeg")
            b=waveform_peaks.get_or_create(self.source,self.cache,3.0,"ffmpeg")
            self.assertEqual(a,b)
            self.assertEqual(1,len(calls))
            self.source.write_bytes(b"new source bytes")
            waveform_peaks.get_or_create(self.source,self.cache,3.0,"ffmpeg")
            self.assertEqual(2,len(calls))
        self.assertEqual(b"new source bytes",self.source.read_bytes())

    def test_reject_non_positive_duration(self):
        with self.assertRaises(ValueError):
            waveform_peaks.calculate(self.source,0,"ffmpeg")


if __name__=="__main__":
    unittest.main()
