"""Native Lego request tests: offline, no checkpoint or GPU required."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ace_transport
from ace_adapter import AceError

class LegoTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.context=Path(self.temp.name)/"context.wav"
        self.context.write_bytes(b"RIFF"+b"x"*400)
        self.client=type("Client",(),{"base":"http://127.0.0.1:8001","timeout":5,"api_key":None})()

    def test_lego_rejects_turbo_before_http(self):
        with self.assertRaises(ValueError):
            ace_transport.submit_instrument(self.client,self.context,"acestep-v15-turbo",
                "Violin",1,task_type="lego",track_name="strings")

    def test_lego_rejects_vocals_and_unknown_family(self):
        for name in ("vocals","backing_vocals","violin","cello",""):
            with self.subTest(name=name),self.assertRaises(ValueError):
                ace_transport.submit_instrument(self.client,self.context,"acestep-v15-base",
                    "Instrument",1,task_type="lego",track_name=name)

    def test_multipart_has_native_task_family_and_base_steps(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,*args):
                return b'{"code":200,"error":null,"data":{"task_id":"aabbccddeeff00112233445566778899"}}'
        def capture(request,timeout):
            body=request.data
            for part in (b'name="task_type"\r\n\r\nlego',
                         b'name="track_name"\r\n\r\nstrings',
                         b'name="model"\r\n\r\nacestep-v15-base',
                         b'name="inference_steps"\r\n\r\n50',
                         b'name="lyrics"\r\n\r\n[Instrumental]',
                         b'name="instruction"\r\n\r\nGenerate the STRINGS track based on the audio context:'):
                self.assertIn(part,body)
            self.assertNotIn(b'name="audio_cover_strength"',body)
            self.assertNotIn(b'name="cover_noise_strength"',body)
            self.assertNotIn(b'name="chunk_mask_mode"',body)
            return Response()
        with patch("ace_transport.urllib.request.urlopen",side_effect=capture):
            task=ace_transport.submit_instrument(self.client,self.context,
                "acestep-v15-base","Dark violin counterpoint",1234,
                task_type="lego",track_name="strings",duration=20)
        self.assertEqual(task,"aabbccddeeff00112233445566778899")

if __name__=="__main__":unittest.main()
