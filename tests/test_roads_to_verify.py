"""The 24-town verify list records posted speeds from the tiles and drops a road only when sign evidence covers it.

Counts and the road list come from the data. A test must not freeze a town at zero signs or at 176 unread rows.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "roads_to_verify", os.path.join(ROOT, "scripts", "roads_to_verify.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
MD = os.path.join(ROOT, "research", "expansion100_roads_to_verify.md")


def piece(sign, flag=0, mph=25, source=""):
    return {"sign": sign, "flag": flag, "mph": mph, "source": source}


class RoadsToVerify(unittest.TestCase):
    def test_a_road_drops_only_when_every_piece_is_signed_and_unbanned(self):
        self.assertFalse(R.road_confirmed([]))
        self.assertFalse(R.road_confirmed([piece(True), piece(False)]))
        self.assertFalse(R.road_confirmed([piece(True, flag=1), piece(True)]))
        self.assertFalse(R.road_confirmed([piece(True, flag=4)]))
        self.assertTrue(R.road_confirmed([piece(True, mph=30), piece(True, mph=35)]))

    def test_clause_names_the_speeds_that_were_read(self):
        self.assertEqual(R.finding_clause([], []), "Posted speed seen: not read. Source: none.")
        self.assertEqual(
            R.finding_clause([25, 35], ["https://www.mapillary.com/app/?lat=1&lng=2"]),
            "Posted speed seen: 25/35 mph. Source: https://www.mapillary.com/app/?lat=1&lng=2.")

    def test_a_fifteen_mph_reading_does_not_open_a_forty_five(self):
        idx, segs = R.load_current("dadecity")
        for road in ("21st Street", "Old State Road 52"):
            hits = [s for s in segs if idx["names"][s[0]] == road and s[2] == 15]
            self.assertEqual(hits, [], road)

    def test_report_matches_the_tiles_and_does_not_freeze_a_count(self):
        R.main()
        with open(MD, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("\u2014", text)
        self.assertIn("21st Street", text)
        self.assertIn("Old State Road 52", text)
        bullets = [line for line in text.splitlines() if line.startswith("- **")]
        for line in bullets:
            self.assertIn("Posted speed seen:", line)
        with open(os.path.join(ROOT, "public/data/regions.json"), encoding="utf-8") as fh:
            names = {r["id"]: r["name"] for r in json.load(fh)}
        total = 0
        for rid in R.IDS:
            n = R.posted_sign_pieces(rid)
            total += n
            row = next(line for line in text.splitlines() if line.startswith("| %s |" % names[rid]))
            cells = [c.strip() for c in row.strip("|").split("|")]
            self.assertEqual(int(cells[2]), n, rid)
            self.assertGreaterEqual(int(cells[1]), 0)
        self.assertGreater(total, 0)
        self.assertIn("closed to open", text)
        self.assertIn("open to closed", text)
