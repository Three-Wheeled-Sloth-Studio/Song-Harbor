"""Non-destructive channel extraction: deterministic command and rollback checks."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import channel_split
import projects


class SplitChannelsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ident="abcdef012345"
        self.folder=self.root/"jobs"/self.ident
        (self.folder/"stems").mkdir(parents=True)
        self.files=[]
        for label in projects.ORDER:
            name=f"song_({label})_htdemucs_6s.wav"
            (self.folder/"stems"/name).write_bytes(b"original-"+label.encode())
            self.files.append(name)
        self.project={"id":self.ident,"files":self.files,"title":"Test",
                      "stems":projects.default_settings(self.files)}
        self.before={p.name:p.read_bytes() for p in (self.folder/"stems").iterdir()}

    def fake_run(self,argv,**kwargs):
        if argv[0]=="ffprobe":
            return subprocess.CompletedProcess(argv,0,stdout=json.dumps(
                {"streams":[{"channels":2,"sample_rate":"48000"}]}))
        if argv[0]=="ffmpeg":
            output=Path(argv[-1])
            output.write_bytes(b"RIFF"+bytes(100))
            return subprocess.CompletedProcess(argv,0,stdout="")
        raise AssertionError(argv)

    def test_selected_stem_creates_two_mono_outputs(self):
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            return self.fake_run(argv,**kwargs)
        out=channel_split.split_stems(self.root,self.project,[self.files[0]],
                                      "ffmpeg","ffprobe",run=run)
        manifest=json.loads((out/"manifest.json").read_text())
        self.assertEqual(2,manifest["track_count"])
        self.assertEqual(["left","right"],[t["channel"] for t in manifest["tracks"]])
        self.assertTrue(all(t["start_seconds"]==0 for t in manifest["tracks"]))
        self.assertIn("pan=mono|c0=c0",calls[1])
        self.assertIn("pan=mono|c0=c1",calls[2])
        self.assertIn("pcm_f32le",calls[1])
        self.assertEqual(self.before,{p.name:p.read_bytes() for p in (self.folder/"stems").iterdir()})
        another=channel_split.split_stems(self.root,self.project,[self.files[0]],
                                           "ffmpeg","ffprobe",run=self.fake_run)
        self.assertNotEqual(out,another)
        self.assertTrue(out.exists())

    def test_invalid_selection_rejected_without_new_files(self):
        for values in ([],["../song.wav"],[self.files[0],self.files[0]]):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    channel_split.split_stems(self.root,self.project,values,"ffmpeg","ffprobe",
                                              run=self.fake_run)
        self.assertFalse((self.folder/"exports").exists() and
                         any((self.folder/"exports").iterdir()))

    def test_mono_source_fails_without_partial_export(self):
        def mono(argv,**kwargs):
            if argv[0]=="ffprobe":
                return subprocess.CompletedProcess(argv,0,stdout='{"streams":[{"channels":1,"sample_rate":"48000"}]}')
            raise AssertionError("Must not render mono source")
        with self.assertRaisesRegex(ValueError,"exactly two"):
            channel_split.split_stems(self.root,self.project,[self.files[0]],"ffmpeg","ffprobe",run=mono)
        self.assertEqual([],list((self.folder/"exports").iterdir()))

    def test_render_failure_rolls_back_staging(self):
        def fail(argv,**kwargs):
            if argv[0]=="ffmpeg":
                raise subprocess.CalledProcessError(1,argv)
            return self.fake_run(argv,**kwargs)
        with self.assertRaises(subprocess.CalledProcessError):
            channel_split.split_stems(self.root,self.project,[self.files[0]],"ffmpeg","ffprobe",run=fail)
        self.assertEqual([],list((self.folder/"exports").iterdir()))
        self.assertEqual(self.before,{p.name:p.read_bytes() for p in (self.folder/"stems").iterdir()})


if __name__=="__main__":
    unittest.main()
