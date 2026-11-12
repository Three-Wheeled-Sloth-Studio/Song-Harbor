"""WSL model supervisor safety without spawning Linux processes."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import moss_wsl_supervisor as supervisor


class MossSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "moss-worker.json"
        self.served = "songharbor-moss-verified123"

    def test_refuse_unrecognized_worker_identity_without_signaling(self):
        self.path.write_text(json.dumps({
            "pid": 23456, "start_ticks": "11", "served": "songharbor-moss-another"
        }))
        with patch.object(supervisor.os, "killpg") as kill, \
             patch.object(supervisor, "_group_alive", return_value=True):
            self.assertEqual(supervisor.stop(self.path, self.served), 4)
            kill.assert_not_called()
        self.assertTrue(self.path.exists())

    def test_stale_worker_record_pruned_only_after_no_group_is_alive(self):
        self.path.write_text(json.dumps({
            "pid": 23456, "start_ticks": "11", "served": self.served
        }))
        with patch.object(supervisor, "_record", return_value=None), \
             patch.object(supervisor, "_group_alive", return_value=False), \
             patch.object(supervisor.os, "killpg") as kill:
            self.assertEqual(supervisor.stop(self.path, self.served), 0)
            kill.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_stop_verified_worker_signals_only_its_process_group(self):
        self.path.write_text(json.dumps({
            "pid": 23456, "start_ticks": "11", "served": self.served
        }))
        with patch.object(supervisor, "_record", return_value={"pid": 23456}), \
             patch.object(supervisor, "_group_alive", side_effect=[True, False]), \
             patch.object(supervisor.os, "killpg") as kill:
            self.assertEqual(supervisor.stop(self.path, self.served), 0)
            kill.assert_called_once_with(23456, supervisor.signal.SIGTERM)
        self.assertFalse(self.path.exists())

    def test_invalid_state_does_not_terminate_other_processes(self):
        self.path.write_text("not-json")
        with patch.object(supervisor.os, "killpg") as kill:
            self.assertEqual(supervisor.stop(self.path, self.served), 4)
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
