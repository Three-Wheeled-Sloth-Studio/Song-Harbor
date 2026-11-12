"""Synthetic pulse and tempo-change checks; no model or uploaded song needed."""
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempo_measure


def write_clicks(path: Path, segments: list[tuple[float, float]], rate: int = 48000):
    """Short broadband percussive clicks at specified tempos."""
    length = int(sum(duration for duration, _ in segments) * rate)
    pcm = np.zeros(length, dtype=np.float32)
    offset = 0
    for duration, bpm in segments:
        n = round(duration * rate)
        for t in np.arange(.15, duration, 60 / bpm):
            ix = offset + round(t * rate)
            if ix + 240 < length:
                # Fast attack with a decaying, high-frequency click.
                pulse = np.exp(-np.arange(240) / 55) * np.cos(np.arange(240) * .9)
                pcm[ix:ix+240] += pulse.astype(np.float32) * .85
        offset += n
    data = np.clip(pcm, -1, 1)
    ints = np.round(data * 8388607).astype(np.int32)
    unsigned = ints & 0xffffff
    stereo = np.column_stack([unsigned, unsigned]).reshape(-1)
    packed = np.stack([stereo & 255, (stereo >> 8) & 255, (stereo >> 16) & 255], axis=1).astype(np.uint8)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(3)
        out.setframerate(rate)
        out.writeframes(packed.tobytes())


class TempoMeasureTests(unittest.TestCase):
    def test_silence_does_not_invent_bpm(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "silent.wav"
            write_clicks(path, [(14.0, 120)])
            with wave.open(str(path), "rb") as source:
                params = source.getparams()
            with wave.open(str(path), "wb") as output:
                output.setparams(params)
                output.writeframes(bytes(14 * 48000 * 6))
            result = tempo_measure.measure(path)
            self.assertTrue(result["windows"])
            self.assertTrue(all(row["bpm"] is None for row in result["windows"]))

    def test_variable_tempo_retains_local_estimates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changes.wav"
            write_clicks(path, [(18.0, 96.0), (18.0, 144.0)])
            result = tempo_measure.measure(path)
            observations = result["windows"]
            first = [r for r in observations if r["start_sample"] < 48000 * 6 and r["bpm"] is not None]
            last = [r for r in observations if r["start_sample"] >= 48000 * 24 and r["bpm"] is not None]
            self.assertTrue(first, "First sustained tempo should produce a candidate")
            self.assertTrue(last, "Second sustained tempo should produce a candidate")
            # Half/double pulse alternatives are possible: require one
            # candidate or alternative close to the known pulse.
            self.assertTrue(any(any(abs(value - 96) < 6 for value in [r["bpm"], *r["alternatives"]]) for r in first))
            self.assertTrue(any(any(abs(value - 144) < 7 for value in [r["bpm"], *r["alternatives"]]) for r in last))
            self.assertTrue(all(r["status"] == "unverified" for r in observations))

    def test_isolated_fills_do_not_establish_a_beat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fills.wav"
            rate = 48000
            pcm = np.zeros(rate * 12, dtype=np.float32)
            # Four separated, irregular sharp attacks, not a stable rhythm.
            for seconds in (.7, 3.2, 7.1, 10.65):
                i = round(seconds * rate)
                pcm[i:i+240] = (np.exp(-np.arange(240) / 55) *
                                np.cos(np.arange(240) * .9)).astype(np.float32)
            integers = np.round(pcm * 8388607).astype(np.int32) & 0xffffff
            unsigned = np.column_stack((integers, integers)).reshape(-1)
            packed = np.stack((unsigned & 255, (unsigned >> 8) & 255,
                               (unsigned >> 16) & 255), axis=1).astype(np.uint8)
            with wave.open(str(path), "wb") as out:
                out.setnchannels(2)
                out.setsampwidth(3)
                out.setframerate(rate)
                out.writeframes(packed.tobytes())
            result = tempo_measure.measure(path)
            self.assertTrue(result["windows"])
            self.assertTrue(all(row["bpm"] is None for row in result["windows"]))

    def test_offset_is_absolute_project_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "section.wav"
            write_clicks(path, [(14, 100)])
            result = tempo_measure.measure(path, offset_seconds=31.884)
            self.assertEqual(result["windows"][0]["start_sample"], round(31.884 * 48000))


if __name__ == "__main__":
    unittest.main()
