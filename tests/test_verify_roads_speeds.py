"""Official posted speeds from the 2026-11-16 road-check replies (Max OK t558s3087)."""
import json, os, glob, math, re, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def J(p):
    return json.load(open(os.path.join(ROOT, p)))

def segs(rid):
    names = J(f"public/data/{rid}/index.json")["names"]
    out = []
    for f in glob.glob(os.path.join(ROOT, f"public/data/{rid}/tiles/*.json")):
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
    from collections import Counter
    return Counter((s[2], s[3]) for nm, s in rows if nm == want)


class VerifyRoadSpeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gw = segs("greenwich")
        cls.cy = segs("conyers")
        cls.gw_cfg = J("research/regions/greenwich.json")
        cls.cy_cfg = J("research/regions/conyers.json")

    def test_speed_names_are_cited_https(self):
        for rid, cfg in (("greenwich", self.gw_cfg), ("conyers", self.cy_cfg)):
            self.assertTrue(cfg.get("speed_names"), rid)
            for o in cfg["speed_names"]:
                self.assertTrue(o["url"].startswith("https://"), (rid, o))
                self.assertTrue(o.get("label"), (rid, o))
                self.assertRegex(o["names"], r"^\^")

    def test_asked_pins_match_official_posted_speeds(self):
        # Pins from the 2026-11-16 emails (email_drafts_20261116.md).
        cases = [
            (self.gw, "Lake Avenue", 41.08720, -73.64721, 30),
            (self.gw, "Stanwich Road", 41.04933, -73.60742, 30),
            (self.gw, "North Street", 41.12961, -73.63755, 40),
            (self.gw, "Westover Road", 41.06274, -73.56435, 25),
            (self.cy, "Parker Road Southeast", 33.64081, -84.02219, 35),
        ]
        for rows, name, lat, lon, mph in cases:
            hit = nearest(rows, name, lat, lon)
            self.assertIsNotNone(hit, name)
            dist, s = hit
            self.assertLess(dist * 5280, 600, (name, dist * 5280))
            self.assertEqual(s[2], mph, name)
            self.assertEqual(s[3], "v", name)

    def test_westover_stays_inside_existing_greenwich_region(self):
        bbox = J("public/data/regions.json")
        box = next(r for r in bbox if r["id"] == "greenwich")["bbox"]
        self.assertEqual(box, [41.0, -73.66, 41.12, -73.57])
        rows = [s for nm, s in self.gw if nm == "Westover Road"]
        self.assertTrue(rows)
        # Every Westover segment is official 25; the region was not widened.
        self.assertTrue(all(s[2] == 25 and s[3] == "v" for s in rows))

    def test_stamford_north_street_fragment_not_given_greenwich_list(self):
        stray = [
            s for nm, s in self.gw
            if nm == "North Street" and s[7][len(s[7]) // 2][0] > -73.60
        ]
        self.assertEqual(len(stray), 1)
        self.assertEqual(stray[0][2], 25)
        self.assertEqual(stray[0][3], "i")

    def test_rockdale_county_roads_unchanged(self):
        for name in (
            "Smyrna Road Southwest",
            "Flat Shoals Road Southeast",
            "Old Salem Road Southeast",
        ):
            codes = speeds(self.cy, name)
            self.assertTrue(codes, name)
            self.assertFalse(any(code == "v" for mph, code in codes), (name, dict(codes)))

    def test_south_stanwich_and_north_stanwich_not_changed(self):
        for name in ("South Stanwich Road", "North Stanwich Road", "Stanwich Lane"):
            codes = speeds(self.gw, name)
            if not codes:
                continue
            self.assertFalse(any(code == "v" for mph, code in codes), (name, dict(codes)))


if __name__ == "__main__":
    unittest.main()
