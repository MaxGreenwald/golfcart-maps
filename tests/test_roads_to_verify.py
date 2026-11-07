"""The 24-town verify list records a posted speed only from a real sign check.

research/expansion100_signchecks.json is the only way a road is dropped.
Without it, every road stays and says the posted speed was not read.
"""
import importlib.util
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "roads_to_verify", os.path.join(ROOT, "scripts", "roads_to_verify.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
MD = os.path.join(ROOT, "research", "expansion100_roads_to_verify.md")


class RoadsToVerify(unittest.TestCase):
    def test_clause_names_speed_and_source_or_says_unread(self):
        self.assertEqual(R.finding_clause(None), "Posted speed seen: not read. Source: none.")
        self.assertEqual(
            R.finding_clause({"mph": 35, "source": "Mapillary", "confirmed": False}),
            "Posted speed seen: 35 mph. Source: Mapillary.")

    def test_sign_checks_skip_rows_without_a_speed_and_a_source(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "checks.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"fairhope": {
                    "Good Road": {"mph": 25, "source": "Mapillary", "confirmed": True},
                    "Thin Road": {"mph": 30},
                }}, fh)
            old = R.CHECKS
            R.CHECKS = path
            try:
                got = R.sign_checks()
            finally:
                R.CHECKS = old
        self.assertEqual(got, {"fairhope": {"Good Road": {"mph": 25, "source": "Mapillary", "confirmed": True}}})

    def test_list_keeps_every_road_until_a_sign_is_confirmed(self):
        with open(MD, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("\u2014", text)
        bullets = [line for line in text.splitlines() if line.startswith("- **")]
        self.assertEqual(len(bullets), 176)
        for line in bullets:
            self.assertIn("Posted speed seen: not read. Source: none.", line)
        self.assertIn("MAPILLARY_TOKEN", text)
        self.assertIn("Roads whose legal status changed (open to closed or closed to open): none.", text)
        for rid in R.IDS:
            self.assertEqual(R.posted_sign_pieces(rid), 0)
