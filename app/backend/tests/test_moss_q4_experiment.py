"""No-download, no-inference checks for experimental CrispASR Q4 bridge."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import moss_q4_experiment as q4


class Q4ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.binary = self.root / "crispasr.exe"
        self.binary.write_bytes(b"fake-executable")
        self.model = self.root / "moss-audio-4b-q4_k.gguf"
        self.model.write_bytes(b"GGUF" + b"0" * (1024 * 1024))
        self.audio = self.root / "test.wav"
        self.audio.write_bytes(b"RIFF" + bytes(4) + b"WAVE" + bytes(64))
        q4._JOB.update({"process": None, "log": None, "state": "idle",
                        "error": "", "result": "", "audio": "", "log_start": 0})

    def test_discovery_never_executes_or_downloads(self):
        with patch.object(q4.subprocess, "Popen") as spawn:
            result = q4.discover(self.root, self.root)
            self.assertEqual(result["executables"], [])
            self.assertEqual(result["models"], [])
            spawn.assert_not_called()

    def test_configure_is_local_and_does_not_execute(self):
        with patch.object(q4.subprocess, "Popen") as spawn:
            result = q4.configure(self.root, str(self.binary), str(self.model))
            self.assertFalse(result["verified"])
            self.assertEqual(q4.config(self.root)["model"], str(self.model))
            spawn.assert_not_called()

    def test_blocks_unapproved_test(self):
        q4.configure(self.root, str(self.binary), str(self.model))
        with patch.object(q4.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "approval"):
                q4.start(self.root, str(self.audio), "Describe", False)
            spawn.assert_not_called()

    def test_rejects_invalid_model_and_text_only(self):
        self.model.rename(self.root / "moss-music-8b-q4.gguf")
        with self.assertRaisesRegex(ValueError, "MOSS-Audio"):
            q4.configure(self.root, str(self.binary), str(self.root / "moss-music-8b-q4.gguf"))

    def test_rejects_invalid_gguf_header(self):
        self.model.write_bytes(b"NOPE" + b"0" * (1024 * 1024))
        with self.assertRaisesRegex(ValueError, "GGUF header"):
            q4.configure(self.root, str(self.binary), str(self.model))

    def test_run_result_keeps_beginning_and_flags_oversize(self):
        output = self.root / "moss-q4-one-run.txt"
        output.write_text("Opening sentence.\n" + "x" * 9000, encoding="utf-8")
        whole, oversized = q4._read_run_output(output)
        self.assertTrue(whole.startswith("Opening sentence."))
        self.assertFalse(oversized)
        limited, truncated = q4._read_run_output(output, 100)
        self.assertTrue(limited.startswith("Opening sentence."))
        self.assertTrue(truncated)

    def test_separate_runs_do_not_inherit_previous_output(self):
        first = self.root / "moss-q4-first.txt"
        second = self.root / "moss-q4-second.txt"
        first.write_text("Prior analysis of an unrelated song")
        second.write_text("Fresh opening. A test clip")
        result, truncated = q4._read_run_output(second)
        self.assertEqual(result, "Fresh opening. A test clip")
        self.assertFalse(truncated)

    def test_rejects_non_wav_without_execution(self):
        q4.configure(self.root, str(self.binary), str(self.model))
        self.audio.write_bytes(b"NOPE" + bytes(128))
        with patch.object(q4.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "RIFF/WAVE"):
                q4.start(self.root, str(self.audio), "Describe", True)
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
