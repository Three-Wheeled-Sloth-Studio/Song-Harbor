"""ACE candidate tests without an ACE process or external audio tools."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ace_adapter import AceError, AudioRange, Selection
from ace_candidates import (candidate_directory, create_candidate,
                            load_record, sample_bounds, validate_generation,
                            crop_generated_candidate)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.a = "a" * 32
        self.b = "b" * 32
        self.c = "c" * 32
        self.project = {
            "id": "586a03b40c9c", "source_duration_seconds": 341.360,
            "sections": [
                {"id": self.a, "start_seconds": 39.699, "end_seconds": 71.719},
                {"id": self.b, "start_seconds": 71.719, "end_seconds": 82.402},
                {"id": self.c, "start_seconds": 82.402, "end_seconds": 115.0},
            ],
            "files": ["01 (Vocals).wav"],
        }
        self.models = {"models": [{"name": "acestep-v15-turbo",
                                   "validated_tasks": ["cover", "repaint"]}]}

    def test_poc_samples(self):
        selection, bounds = validate_generation(self.project, self.b, self.b,
                                                 32.02, 0, "acestep-v15-turbo",
                                                 "Sparse cello", "cover", self.models)
        self.assertAlmostEqual(selection.context.start, 39.699)
        self.assertEqual(bounds["crop_start"], round(32.02 * 48000))
        self.assertEqual(bounds["crop_end"], round((82.402 - 39.699) * 48000))

    def test_from_to_sections(self):
        selection, bounds = validate_generation(self.project, self.a, self.c,
                                                 20, 5, "acestep-v15-turbo",
                                                 "Dark cello", "cover", self.models)
        self.assertEqual((selection.target.start, selection.target.end), (39.699, 115))
        self.assertAlmostEqual(selection.context.start, 19.699)

    def test_reject_unverified_lego(self):
        with self.assertRaises(ValueError):
            validate_generation(self.project, self.b, self.b, 0, 0,
                                "acestep-v15-turbo", "Cello", "lego", self.models)

    def test_reject_reversed_section_selection(self):
        with self.assertRaises(ValueError):
            validate_generation(self.project, self.c, self.b, 0, 0,
                                "acestep-v15-turbo", "Cello", "cover", self.models)

    def test_candidate_preparation_does_not_change_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            original = folder / "source.wav"
            original.write_bytes(b"unchanged source")
            def fake_extract(ffmpeg, source, destination, start, end, rate=48000):
                self.assertEqual(source, original)
                destination.write_bytes(b"simulated context")
            with patch("ace_candidates.ffmpeg_extract", side_effect=fake_extract):
                result = create_candidate(self.project, folder, original,
                                          self.b, self.b, 32.02, 0,
                                          "acestep-v15-turbo", "Cello line", "cover",
                                          self.models, "ffmpeg", seed=150719)
            self.assertEqual(result["state"], "prepared")
            self.assertEqual(result["isolation"], "cover-mix-not-isolated")
            self.assertEqual(result["variants"], [])
            self.assertEqual(load_record(folder, result["candidate_id"]), result)
            self.assertEqual(self.project["files"], ["01 (Vocals).wav"])
            self.assertEqual(original.read_bytes(), b"unchanged source")

    def test_target_crop_is_context_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            original = folder / "source.wav"
            original.write_bytes(b"source")
            with patch("ace_candidates.ffmpeg_extract", side_effect=lambda f,s,d,a,b,rate=48000: d.write_bytes(b"wav")):
                result = create_candidate(self.project, folder, original, self.b, self.b,
                                          32.02, 0, "acestep-v15-turbo", "Cello",
                                          "cover", self.models, "ffmpeg")
            directory = candidate_directory(folder, result["candidate_id"])
            generated = directory / "generated.wav"
            generated.write_bytes(b"fake")
            calls = []
            def crop(ffmpeg, source, destination, start, end, rate=48000):
                calls.append((start, end))
                destination.write_bytes(b"cropped")
            target_length = (result["samples"]["crop_end"] - result["samples"]["crop_start"]) / 48000
            def duration_probe(ffmpeg, path):
                if str(path).endswith("generated.wav"):
                    return result["samples"]["crop_end"] / 48000 + 1
                return target_length
            with patch("ace_candidates.ffmpeg_extract", side_effect=crop), patch(
                "ace_candidates.probe_audio_duration", side_effect=duration_probe
            ):
                ready = crop_generated_candidate(folder, result["candidate_id"], generated, "ffmpeg")
            self.assertEqual(ready["state"], "ready")
            self.assertEqual(calls[0], (result["samples"]["crop_start"],
                                        result["samples"]["crop_end"]))
            self.assertEqual(ready["variants"][0]["file"], "target.wav")

    def test_reject_short_generated_float_wav_before_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            original = folder / "source.wav"
            original.write_bytes(b"source")
            with patch("ace_candidates.ffmpeg_extract", side_effect=lambda f,s,d,a,b,rate=48000: d.write_bytes(b"context")):
                record = create_candidate(self.project, folder, original, self.b, self.b,
                                          32.02, 0, "acestep-v15-turbo", "Violin",
                                          "cover", self.models, "ffmpeg")
            generated = candidate_directory(folder, record["candidate_id"]) / "generated.wav"
            generated.write_bytes(b"fake float wav")
            with patch("ace_candidates.probe_audio_duration", return_value=1.0), patch(
                "ace_candidates.ffmpeg_extract") as crop:
                with self.assertRaises(AceError):
                    crop_generated_candidate(folder, record["candidate_id"], generated, "ffmpeg")
                crop.assert_not_called()

    def test_reject_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                candidate_directory(Path(tmp), "../escape")

if __name__ == "__main__":
    unittest.main()
