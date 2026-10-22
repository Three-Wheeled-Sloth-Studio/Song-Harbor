"""Readable build identity contract.

The displayed identifier must be Version:Revision:Build, not a Git hash.
The full commit hash remains accessible in the tooltip for diagnostics.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app_update


class VersionBadgeTests(unittest.TestCase):
    def test_no_git_checkout_has_readable_version(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            directory=root/"app"/"frontend"
            directory.mkdir(parents=True)
            (directory/"package.json").write_text(json.dumps({"version":"0.7.3"}),encoding="utf-8")
            result=app_update.local_version(root)
            self.assertEqual(result["label"],"0.7.3:1:local")
            self.assertEqual(result["commit"],"")

    def test_git_checkout_uses_build_count_not_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/".git").mkdir()
            directory=root/"app"/"frontend"
            directory.mkdir(parents=True)
            (directory/"package.json").write_text(json.dumps({"version":"0.1.0"}),encoding="utf-8")
            def fake_run(args,**kwargs):
                from types import SimpleNamespace
                command=" ".join(args)
                if "rev-list" in command:return SimpleNamespace(returncode=0,stdout="412\n")
                if "branch" in command:return SimpleNamespace(returncode=0,stdout="main\n")
                return SimpleNamespace(returncode=0,stdout="abcdef12\n")
            with patch.object(app_update.subprocess,"run",side_effect=fake_run):
                result=app_update.local_version(root)
            self.assertEqual(result["label"],"0.1.0:1:412")
            self.assertRegex(result["label"],r"^\d+\.\d+\.\d+:\d+:\d+$")
            self.assertEqual(result["commit"],"abcdef12")
            self.assertNotIn("abcdef12",result["label"])


if __name__=="__main__":
    unittest.main()
