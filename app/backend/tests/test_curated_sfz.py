"""Curated third-party instrument metadata, no external downloads during tests."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import curated_sfz
import sfz_pack


class CuratedSFZTests(unittest.TestCase):
    def test_recommendations_are_versioned_reviewable_and_within_upload_limit(self):
        packs=curated_sfz.curated_catalogue()
        self.assertGreaterEqual(len(packs),5)
        self.assertEqual(len({pack["id"] for pack in packs}),len(packs))
        for pack in packs:
            self.assertTrue(pack["name"])
            self.assertTrue(pack["description"])
            self.assertEqual(pack["license"],"CC0-1.0")
            self.assertEqual(urlparse(pack["download_url"]).scheme,"https")
            self.assertIn("/releases/download/",pack["download_url"])
            self.assertTrue(pack["download_url"].lower().endswith(".zip"))
            self.assertLess(pack["approx_mb"]*1024*1024,sfz_pack.MAX_ARCHIVE_BYTES)
            self.assertIn("not yet QA-tested",pack["status"])
        self.assertEqual(packs[0]["id"],"bigcat-cello")
        self.assertEqual(packs[1]["id"],"growlybass")

    def test_catalogue_defensive_copy(self):
        entries=curated_sfz.curated_catalogue()
        entries[0]["name"]="modified"
        self.assertNotEqual(curated_sfz.curated_catalogue()[0]["name"],"modified")


if __name__=="__main__":
    unittest.main()
