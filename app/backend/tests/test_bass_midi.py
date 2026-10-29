"""Small CPU regression fixtures for the experimental bass MIDI path."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import numpy as np
    import bass_midi
    available=True
except ImportError:
    available=False

@unittest.skipUnless(available,"numpy is required for local bass MIDI engine")
class BassMidiTests(unittest.TestCase):
    def test_a2_pitch_and_note_bounds(self):
        duration=2
        t=np.arange(duration*bass_midi.RATE,dtype=np.float32)/bass_midi.RATE
        # Pure monophonic synthetic bass note with harmonics and no GPU.
        pcm=(.3*np.sin(2*np.pi*110*t)+.11*np.sin(2*np.pi*220*t)).astype(np.float32)
        notes=bass_midi.transcribe(pcm)
        self.assertTrue(notes,"A2 bass test should produce notes")
        self.assertTrue(any(abs(n["pitch"]-45)<=1 for n in notes),notes)
        self.assertTrue(all(0<=n["start"]<n["end"]<=duration for n in notes))

    def test_note_validation_rejects_polyphony_and_bad_values(self):
        notes=[{"pitch":45,"start":0.0,"end":1.0,"velocity":85}]
        self.assertEqual(bass_midi.validate_notes(notes,2),notes)
        for bad in (notes+[{"pitch":47,"start":.5,"end":1.2,"velocity":80}],
                    [{"pitch":120,"start":0,"end":1,"velocity":85}],
                    [{"pitch":45,"start":0,"end":2.4,"velocity":85}],
                    [{"pitch":45,"start":1,"end":1.02,"velocity":85}]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                bass_midi.validate_notes(bad,2)

    def test_chunked_whole_song_preserves_offsets_and_mono(self):
        note={"pitch":45,"start":0.1,"end":0.5,"velocity":85}
        with patch.object(bass_midi,"decode_excerpt",return_value=np.zeros(12000,dtype=np.float32)) as decoder:
            with patch.object(bass_midi,"transcribe",return_value=[note]):
                rows=bass_midi.transcribe_region(Path("source.wav"),10,95,"ffmpeg")
        self.assertEqual(len(rows),4)
        self.assertEqual([round(n["start"],1) for n in rows],[.1,30.1,60.1,90.1])
        self.assertTrue(all(n["end"]<=95 for n in rows))
        self.assertEqual(decoder.call_count,4)

    def test_region_limits_and_long_render(self):
        with self.assertRaises(ValueError):
            bass_midi.transcribe_region(Path("missing.wav"),0,601,"ffmpeg")
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"full.wav"
            bass_midi.render_bowed_wav(file,[{"pitch":40,"start":70,"end":70.4,"velocity":85}],90)
            self.assertGreater(file.stat().st_size,90*48000)

    def test_render_midi_and_source_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/"Bass.wav"
            source.write_bytes(b"unaltered source")
            notes=[{"pitch":40,"start":.05,"end":.4,"velocity":85},
                   {"pitch":43,"start":.5,"end":.8,"velocity":90}]
            data=bass_midi.midi_bytes(notes,1)
            self.assertTrue(data.startswith(b"MThd"))
            self.assertIn(b"MTrk",data)
            self.assertIn(bytes([0xc0,42]),data)
            preview=root/"generated"/"cello.wav"
            bass_midi.render_bowed_wav(preview,notes,1)
            self.assertGreater(preview.stat().st_size,1000)
            self.assertEqual(source.read_bytes(),b"unaltered source")

if __name__=="__main__":
    unittest.main()
