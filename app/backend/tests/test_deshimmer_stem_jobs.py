"""Non-destructive candidate worker guards without requiring Deshimmer installation."""
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deshimmer_stem_jobs as runner

def wav(path: Path, frames=4800):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(bytes(4*frames))

class DeshimmerStemJobsTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self.ident="abcdef123456"
        self.filename="01 - Vocals.wav"
        self.source=self.root/"jobs"/self.ident/"stems"/self.filename
        wav(self.source)
        self.addCleanup(lambda:runner._jobs.clear())
        self.addCleanup(lambda:setattr(runner,"_active",None))

    def test_rejects_path_traversal(self):
        with self.assertRaisesRegex(ValueError,"Invalid working stem filename"):
            runner.start(self.root,self.ident,"../evil.wav")

    def test_rejects_unrecognized_song_id(self):
        with self.assertRaisesRegex(ValueError,"Invalid song identifier"):
            runner.start(self.root,"../../bad",self.filename)

    def test_rejects_missing_stem(self):
        with patch.object(runner,"resolve_python",return_value=sys.executable):
            with self.assertRaisesRegex(ValueError,"unavailable"):
                runner.start(self.root,self.ident,"missing.wav")

    def test_unknown_candidate_cannot_be_fetched(self):
        with self.assertRaises(KeyError):
            runner.candidate(self.ident,"not-found")

    def test_candidate_requires_ready_and_original_hash(self):
        candidate_id="candidate"
        folder=self.root/"jobs"/self.ident/"cleanup_candidates"/candidate_id
        folder.mkdir(parents=True)
        out=folder/"candidate.wav"
        wav(out)
        runner._jobs[candidate_id]={
            "id":candidate_id,"status":"ready","song_id":self.ident,
            "source":self.source,"source_hash":runner._sha(self.source),
            "folder":folder,"filename":self.filename,"message":"ready"}
        self.assertEqual(runner.candidate(self.ident,candidate_id),out)
        self.source.write_bytes(self.source.read_bytes()+b"x")
        with self.assertRaisesRegex(ValueError,"changed"):
            runner.candidate(self.ident,candidate_id)

    def test_cancellation_is_scoped_to_song(self):
        candidate_id="candidate"
        runner._jobs[candidate_id]={
            "id":candidate_id,"status":"queued","song_id":self.ident,
            "source":self.source,"source_hash":runner._sha(self.source),
            "folder":self.root,"filename":self.filename,
            "process":None,"message":"queued"}
        with self.assertRaises(KeyError):
            runner.cancel("123456abcdef",candidate_id)
        self.assertEqual(runner.cancel(self.ident,candidate_id)["status"],"cancelled")

if __name__=="__main__":
    unittest.main()
