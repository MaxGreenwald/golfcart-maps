"""Official CTDOT OSTA speeds for 11 additional Greenwich roads (Max OK t559s3097)."""
import glob
import json
import math
import os
import re
import unittest
from collections import Counter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PDF = (
    "https://portal.ct.gov/dot/-/media/dot/osta/townspeeds/greenwichpdf.pdf"
    "?rev=bedef88afc6e4c7abcf63c8a86fc14ae"
)
ROADS = (
    "Taconic Road",
    "Round Hill Road",
    "Zaccheus Mead Lane",
    "Lower Cross Road",
    "North Maple Avenue",
    "Old Church Road",
    "Hillside Road",
    "Close Road",
    "Weaver Street",
    "Sound Beach Avenue",
    "Ritch Avenue",
)


def J(p):
    return json.load(open(os.path.join(ROOT, p)))


def segs():
    names = J("public/data/greenwich/index.json")["names"]
    out = []
    for f in glob.glob(os.path.join(ROOT, "public/data/greenwich/tiles/*.json")):
        for s in json.load(open(f)):
            out.append((names[s[0]], s))
    return out


def nearest(rows, want, lat, lon):
    best = None
    for nm, s in rows:
        if nm != want:
            continue
        for x, y in s[7]:
            d = math.hypot((y - lat) * 69, (x - lon) * math.cos(math.radians(lat)) * 69)
            if best is None or d < best[0]:
                best = (d, s)
    return best


def speeds(rows, want):
    return Counter((s[2], s[3]) for nm, s in rows if nm == want)


class GreenwichOsta11Roads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gw = segs()
        cls.cfg = J("research/regions/greenwich.json")

    def test_new_speed_names_are_cited(self):
        rules = [
            o for o in self.cfg["speed_names"]
            if any(re.search(o["names"], n) for n in ROADS)
        ]
        self.assertGreaterEqual(len(rules), 11)
        for o in rules:
            self.assertEqual(o["url"], PDF)
            self.assertIn("page ", o["label"].lower())
            self.assertIn("row ", o["label"].lower())
            # Applied rows are all-day listings. Labels may note that
            # school-hours and when-flashing rows were not used.
            self.assertFalse(re.search(r"\(when flash|w/flashing|sch/flashing\)", o["label"], re.I), o["label"])

    def test_official_pins(self):
        cases = [
            ("Taconic Road", 41.08145, -73.62418, 30),
            ("Round Hill Road", 41.08240, -73.66396, 35),
            ("Zaccheus Mead Lane", 41.03424, -73.63822, 25),
            ("Zaccheus Mead Lane", 41.05535, -73.65263, 30),
            ("Lower Cross Road", 41.11038, -73.64583, 30),
            ("North Maple Avenue", 41.04462, -73.62669, 30),
            ("Old Church Road", 41.04256, -73.61614, 30),
            ("Hillside Road", 41.04094, -73.61178, 25),
            ("Hillside Road", 41.03696, -73.61042, 30),
            ("Close Road", 41.11657, -73.65571, 30),
            ("Weaver Street", 41.01569, -73.65078, 25),
            ("Weaver Street", 41.03779, -73.66220, 30),
            ("Sound Beach Avenue", 41.04290, -73.57485, 30),
            ("Sound Beach Avenue", 41.03804, -73.56948, 25),
            ("Ritch Avenue", 41.02138, -73.63934, 30),
        ]
        for name, lat, lon, mph in cases:
            hit = nearest(self.gw, name, lat, lon)
            self.assertIsNotNone(hit, name)
            dist, s = hit
            self.assertLess(dist * 5280, 600, (name, lat, dist * 5280))
            self.assertEqual(s[2], mph, (name, lat, lon, s[2], s[3]))
            self.assertEqual(s[3], "v", (name, lat, lon))

    def test_round_hill_south_of_nyt107_left_unchanged(self):
        # Lake Avenue end has no all-day OSTA row.
        hit = nearest(self.gw, "Round Hill Road", 41.04909, -73.63782)
        self.assertIsNotNone(hit)
        dist, s = hit
        self.assertLess(dist * 5280, 200)
        self.assertEqual(s[2], 25)
        self.assertEqual(s[3], "i")

    def test_region_bbox_unchanged(self):
        box = next(r for r in J("public/data/regions.json") if r["id"] == "greenwich")["bbox"]
        self.assertEqual(box, [41.0, -73.66, 41.12, -73.57])

    def test_pr106_pins_still_hold(self):
        cases = [
            ("Lake Avenue", 41.08720, -73.64721, 30),
            ("Stanwich Road", 41.04933, -73.60742, 30),
            ("North Street", 41.12961, -73.63755, 40),
            ("Westover Road", 41.06274, -73.56435, 25),
        ]
        for name, lat, lon, mph in cases:
            hit = nearest(self.gw, name, lat, lon)
            self.assertIsNotNone(hit, name)
            dist, s = hit
            self.assertLess(dist * 5280, 600, name)
            self.assertEqual(s[2], mph, name)
            self.assertEqual(s[3], "v", name)


if __name__ == "__main__":
    unittest.main()
