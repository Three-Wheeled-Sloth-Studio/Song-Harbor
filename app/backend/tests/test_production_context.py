"""Reviewed production context is author-controlled, revisioned and model-agnostic."""
import copy
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import production_context as pc


class ProductionContextTests(unittest.TestCase):
    def setUp(self):
        self.section = uuid.uuid4().hex
        self.sections = {self.section}

    def test_context_starts_empty_and_saves_without_touching_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(pc.read(root, self.sections)["sections"], {})
            submitted = {"schema_version": 1, "revision": 0,
                         "sections": {self.section: {"tone": "ominous",
                           "origin": "author", "note": "Keep bass centered"}}}
            original = copy.deepcopy(submitted)
            saved = pc.save(root, submitted, self.sections, 0)
            self.assertEqual(submitted, original)
            self.assertEqual(saved["revision"], 1)
            self.assertEqual(saved, pc.read(root, self.sections))
            with self.assertRaisesRegex(ValueError, "Stale"):
                pc.save(root, submitted, self.sections, 0)

    def test_model_run_is_only_provenance_not_automatic_context(self):
        row = {"tone": "intimate", "origin": "q4-reviewed", "note": "",
               "source_run_id": uuid.uuid4().hex, "source_sha256": "a" * 64}
        data = pc.normalize({"schema_version": 1, "revision": 0,
                             "sections": {self.section: row}}, self.sections)
        self.assertEqual(data["sections"][self.section]["origin"], "q4-reviewed")
        with self.assertRaisesRegex(ValueError, "complete run"):
            pc.normalize({"schema_version": 1, "revision": 0,
                          "sections": {self.section: {"tone": "intimate",
                                                     "origin": "q4-reviewed", "note": ""}}},
                         self.sections)

    def test_context_rejects_unknown_section_and_unrecognized_tone(self):
        for section, tone in ((uuid.uuid4().hex, "ominous"), (self.section, "alarming")):
            with self.assertRaises(ValueError):
                pc.normalize({"schema_version": 1, "revision": 0,
                              "sections": {section: {"tone": tone, "origin": "author", "note": ""}}},
                             self.sections)

    def test_retired_section_context_archived_not_reassigned(self):
        another=uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            initial={"schema_version":1,"revision":0,"sections":{
                self.section:{"tone":"intimate","origin":"author","note":"Old verse"},
                another:{"tone":"driving","origin":"author","note":"Chorus"}
            }}
            pc.save(root,initial,{self.section,another},0)
            changed=pc.read(root,{another})
            self.assertNotIn(self.section,changed["sections"])
            self.assertEqual(changed["archived"][self.section]["note"],"Old verse")
            pc.save(root,{"schema_version":1,"revision":1,
                         "sections":changed["sections"]},{another},1)
            restored=pc.read(root,{another})
            self.assertIn(self.section,restored["archived"])
            self.assertNotIn(self.section,restored["sections"])

    def test_empty_context_fails_closed_on_model_provenance(self):
        with self.assertRaisesRegex(ValueError, "Only reviewed Q4"):
            pc.normalize({"schema_version": 1, "revision": 0,
                          "sections": {self.section: {"tone": "neutral", "origin": "author",
                                                    "note": "", "source_run_id": uuid.uuid4().hex}}},
                         self.sections)


if __name__ == "__main__":
    unittest.main()
