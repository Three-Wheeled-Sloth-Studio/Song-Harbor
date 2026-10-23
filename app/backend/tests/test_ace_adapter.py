"""Pure ACE integration-contract tests; no GPU, network or ACE process required."""
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ace_adapter import AceClient, AceError, resolve_sections, normalize_poll, unwrap


class RangeTests(unittest.TestCase):
    def setUp(self):
        self.sections = [
            {"start_seconds": 0.0, "end_seconds": 40.0},
            {"start_seconds": 40.0, "end_seconds": 71.719},
            {"start_seconds": 71.719, "end_seconds": 82.402},
            {"start_seconds": 82.402, "end_seconds": 110.0},
        ]

    def test_single_section_poc(self):
        selection = resolve_sections(self.sections, 2, 2, 341.36, 32.02)
        self.assertAlmostEqual(selection.target.start, 71.719)
        self.assertAlmostEqual(selection.target.end, 82.402)
        self.assertAlmostEqual(selection.context.start, 39.699)

    def test_inclusive_multi_section(self):
        selection = resolve_sections(self.sections, 1, 3, 341.36, 5, 7)
        self.assertEqual((selection.target.start, selection.target.end), (40, 110))
        self.assertEqual((selection.context.start, selection.context.end), (35, 117))

    def test_context_clamps_to_song(self):
        selection = resolve_sections(self.sections, 0, 3, 110, 30, 50)
        self.assertEqual((selection.context.start, selection.context.end), (0, 110))

    def test_invalid_range(self):
        for args in ((3, 2), (-1, 0), (0, 4)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                resolve_sections(self.sections, *args, 110)

    def test_overlapping_sections_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sections([self.sections[0], {"start_seconds": 39, "end_seconds": 60}], 0, 1, 110)


class ApiTests(unittest.TestCase):
    def test_loopback_only(self):
        with self.assertRaises(ValueError):
            AceClient("example.com")

    def test_discovery_not_ready_even_when_default_named(self):
        client = AceClient()
        def fake(path, body=None):
            if path == "/health":
                return {"code": 200, "data": {"status": "ok", "models_initialized": False,
                                               "loaded_model": "acestep-v15-turbo"}}
            return {"code": 200, "data": {"models": [
                {"name": "acestep-v15-turbo", "supported_task_types": ["cover", "repaint"],
                 "is_loaded": False},
                {"name": "acestep-v15-base", "supported_task_types": ["lego", "extract", "cover"],
                 "is_loaded": False}]}}
        with patch.object(client, "request", side_effect=fake):
            result = client.discover()
        self.assertFalse(result["ready"])
        self.assertIsNone(result["loaded_model"])
        self.assertEqual(result["models"][0]["validated_tasks"], ["cover", "repaint"])
        self.assertTrue(result["models"][1]["advanced_capabilities_unverified"])
        self.assertNotIn("lego", result["models"][1]["validated_tasks"])

    def test_envelope_error_even_when_http_200(self):
        with self.assertRaises(AceError):
            unwrap({"code": 404, "error": "Task not found", "data": None})

    def test_double_encoded_poll_success(self):
        response = {"code": 200, "error": None, "data": [
            {"status": 1, "result": '[{"file":"/v1/audio?path=x.wav"}]'}]}
        result = normalize_poll(response, "job-1")
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["assets"], ["/v1/audio?path=x.wav"])

    def test_unknown_task_not_declared_running(self):
        response = {"code": 200, "data": [{"status": 0, "result": "[]"}]}
        result = normalize_poll(response, "job-1")
        self.assertEqual(result["state"], "pending_or_unknown")
        self.assertTrue(result["ambiguous"])

    def test_failed_and_cancelled_distinguished_by_stage(self):
        for stage, state in (("failed", "failed"), ("cancelled", "cancelled")):
            with self.subTest(stage=stage):
                response = {"code": 200, "data": [
                    {"status": 2, "result": '[{"stage":"' + stage + '"}]'}]}
                self.assertEqual(normalize_poll(response, "job")["state"], state)


if __name__ == "__main__":
    unittest.main()
