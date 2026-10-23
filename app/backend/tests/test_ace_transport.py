"""Transport contract tests. No live ACE service required."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ace_adapter import AceClient, AceError
from ace_transport import submit_cover, poll_cover, download_candidate


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json"):
        self.body = io.BytesIO(body)
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.body.close()

    def read(self, amount=-1):
        return self.body.read(amount)


class TransportTests(unittest.TestCase):
    def test_multipart_upload_and_submit(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "context.wav"
            file.write_bytes(b"RIFF" + b"\0" * 80)
            task = "7388d862-c22b-4139-86fc-c94a777363a4"
            response = FakeResponse(json.dumps({"code": 200, "data": {"task_id": task}}).encode())
            with patch("ace_transport.urllib.request.urlopen", return_value=response) as open_url:
                self.assertEqual(submit_cover(AceClient(), file, "acestep-v15-turbo",
                                               "Solo cello", 150719, bpm=84, duration=42.703), task)
            sent = open_url.call_args.args[0]
            self.assertTrue(sent.full_url.endswith("/release_task"))
            self.assertIn(b'name="ctx_audio"', sent.data)
            self.assertIn(b'name="task_type"', sent.data)
            self.assertIn(b"cover", sent.data)

    def test_poll_normalizes_double_encoded_result(self):
        client = AceClient()
        task = "7388d862-c22b-4139-86fc-c94a777363a4"
        with patch.object(client, "request", return_value={
            "code": 200, "data": [{"status": 1, "result": '[{"file":"/v1/audio?path=x"}]'}]}):
            self.assertEqual(poll_cover(client, task)["state"], "ready")

    def test_reject_external_result_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ("https://host/v1/audio?path=x", "//host/v1/audio?path=x",
                          "/health", "/v1/audio?path=x&path=y"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    download_candidate(AceClient(), value, Path(tmp) / "asset.wav")

    def test_download_valid_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "asset.wav"
            with patch("ace_transport.urllib.request.urlopen", return_value=FakeResponse(
                b"RIFF" + b"\0" * 80, "audio/wav")):
                self.assertEqual(download_candidate(AceClient(), "/v1/audio?path=abc", dest), dest)
            self.assertEqual(dest.stat().st_size, 84)

    def test_reject_non_audio_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "asset.wav"
            with patch("ace_transport.urllib.request.urlopen", return_value=FakeResponse(b"not audio")):
                with self.assertRaises(AceError):
                    download_candidate(AceClient(), "/v1/audio?path=abc", dest)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
