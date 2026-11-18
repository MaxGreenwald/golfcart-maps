"""St. Marys road data from Bobby Marr, Public Works Director (Max OK t561s3115).

Charlie Smith Senior Highway is a state highway and is closed for golf carts and LSVs.
Kings Bay Road and Colerain Road are posted 45 mph. Laurel Island Parkway is left alone.
"""
import glob
import json
import math
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
URL = "https://www.stmarysga.gov/departments/public_works/index.php"
LSV_CAP = 35
CHARLIE = "Charlie Smith Senior Highway"
KINGS = "Kings Bay Road"
COLERAIN = "Colerain Road"
LAUREL = "Laurel Island Parkway"
# Mid of the longest stretch that was previously inferred 25 and LSV-legal.
BEFORE_PIN = (30.81369, -81.5717)


def J(p):
    return json.load(open(os.path.join(ROOT, p)))


def hav_mi(a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def seg_len(s):
    pts = s[7]
    return sum(hav_mi(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def lsv_legal(s):
    flag = s[9] if len(s) > 9 else 0
    return s[2] <= LSV_CAP and s[2] != 99 and flag != 1


def load_segs():
    names = J("public/data/stmarys/index.json")["names"]
    out = []
    for f in glob.glob(os.path.join(ROOT, "public/data/stmarys/tiles/*.json")):
        for s in json.load(open(f)):
            out.append((names[s[0]], s))
    return out


def of(rows, want):
    return [s for nm, s in rows if nm == want]


class StMarysBobbyMarr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_segs()
        cls.cfg = J("research/regions/stmarys.json")
        cls.idx = J("public/data/stmarys/index.json")

    def test_research_rules_cite_bobby_marr(self):
        bans = [o for o in self.cfg["bans"] if re.search(o["names"], CHARLIE)]
        self.assertEqual(len(bans), 1)
        self.assertEqual(bans[0]["url"], URL)
        self.assertIn("Bobby Marr", bans[0]["label"])
        self.assertIn("state highway", bans[0]["label"].lower())

        rules = {o["names"]: o for o in self.cfg["speed_names"]}
        self.assertIn("^Kings Bay Road$", rules)
        self.assertIn("^Colerain Road$", rules)
        for key in ("^Kings Bay Road$", "^Colerain Road$"):
            self.assertEqual(rules[key]["mph"], 45)
            self.assertEqual(rules[key]["url"], URL)
            self.assertIn("Bobby Marr", rules[key]["label"])
            self.assertIn("45", rules[key]["label"])

    def test_poly_unchanged(self):
        self.assertEqual(
            self.cfg["poly"],
            [
                [-81.63, 30.715],
                [-81.485, 30.715],
                [-81.485, 30.82],
                [-81.63, 30.82],
                [-81.63, 30.715],
            ],
        )

    def test_laurel_island_unchanged(self):
        rows = of(self.rows, LAUREL)
        self.assertTrue(rows)
        for s in rows:
            self.assertNotEqual(s[3], "v")
            src = s[8] if len(s) > 8 else -1
            if src is not None and src >= 0:
                label = self.idx["sources"][src][1]
                self.assertNotIn("Bobby Marr", label)

    def test_charlie_smith_closed_for_lsvs(self):
        rows = of(self.rows, CHARLIE)
        self.assertTrue(rows)
        miles = sum(seg_len(s) for s in rows)
        legal = sum(seg_len(s) for s in rows if lsv_legal(s))
        self.assertGreater(miles, 8.0)
        self.assertEqual(legal, 0.0)
        for s in rows:
            self.assertEqual(s[2], 99)
            self.assertEqual(s[3], "v")
            self.assertGreaterEqual(len(s), 10)
            self.assertEqual(s[9], 1)
            url, label = self.idx["sources"][s[8]]
            self.assertEqual(url, URL)
            self.assertIn("Bobby Marr", label)

    def test_before_pin_is_banned(self):
        lat, lon = BEFORE_PIN
        best = None
        for s in of(self.rows, CHARLIE):
            for x, y in s[7]:
                d = math.hypot((y - lat) * 69, (x - lon) * math.cos(math.radians(lat)) * 69)
                if best is None or d < best[0]:
                    best = (d, s)
        self.assertIsNotNone(best)
        self.assertLess(best[0], 0.05)
        s = best[1]
        self.assertEqual(s[2], 99)
        self.assertEqual(s[3], "v")
        self.assertEqual(s[9], 1)
        self.assertFalse(lsv_legal(s))

    def test_kings_bay_and_colerain_are_45_verified(self):
        for want in (KINGS, COLERAIN):
            rows = of(self.rows, want)
            self.assertTrue(rows, want)
            for s in rows:
                self.assertEqual(s[2], 45, want)
                self.assertEqual(s[3], "v", want)
                url, label = self.idx["sources"][s[8]]
                self.assertEqual(url, URL)
                self.assertIn("Bobby Marr", label)
                self.assertIn("45", label)
