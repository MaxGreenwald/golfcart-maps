"""Venice, FL: Sarasota County Street GIS posted speeds close LSV-open stretches over 35 mph.

Official source: https://ags3.scgov.net/server/rest/services/Hosted/Street/FeatureServer/0
field speedlimit, extract in research/venice_sarasota_gis/speedlimit_extract.json (queried 2026-11-23).

Closes:
  - Pinebrook Road, Edmondson Road to Laurel Road East / Honore Avenue, at 40 mph
  - Laurel Road East LSV-open eastern mainline (tertiary, lat ~27.137, lon about -82.406 to -82.380) at 40 or 45 mph

Does not change Center Road, Albee Farm Road, already-closed Laurel Road East (99i),
residential/service Laurel pieces, or Pinebrook Road south of Edmondson Road.
"""
import json, os, glob, re, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GIS_URL = "https://ags3.scgov.net/server/rest/services/Hosted/Street/FeatureServer/0"
EXTRACT = os.path.join(ROOT, "research/venice_sarasota_gis/speedlimit_extract.json")
CFG = os.path.join(ROOT, "research/regions/venice.json")
PB_OIDS = [9528, 182, 43, 33238, 79, 33132, 9425, 9413]
LAU40_OIDS = [9429, 9438, 9430, 9437, 9427]
LAU45_OIDS = [34165, 9421, 10562, 34606, 33115, 8404, 33116]


def J(p):
    return json.load(open(p if os.path.isabs(p) else os.path.join(ROOT, p)))


def segs():
    names = J("public/data/venice/index.json")["names"]
    out = []
    for f in glob.glob(os.path.join(ROOT, "public/data/venice/tiles/*.json")):
        for s in json.load(open(f)):
            out.append((names[s[0]], s))
    return out


def mid(s):
    """Same midpoint build_region.py uses for speed_names (vertex at len//2)."""
    g = s[7]
    return g[len(g) // 2]


def miles(s):
    import math
    t = 0.0
    coords = s[7]
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        r = 3958.8
        p1, p2 = math.radians(y1), math.radians(y2)
        dphi = math.radians(y2 - y1)
        dl = math.radians(x2 - x1)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        t += 2 * r * math.asin(min(1, math.sqrt(a)))
    return t


def speed_name(cfg, name, highway, lat, lon):
    for o in cfg["speed_names"]:
        if not re.search(o["names"], name):
            continue
        if "highway" in o and not re.search(o["highway"], highway):
            continue
        if "bbox" in o:
            b = o["bbox"]
            if not (b[0] <= lat <= b[2] and b[1] <= lon <= b[3]):
                continue
        if ("north_of" in o and lat <= o["north_of"]) or ("south_of" in o and lat >= o["south_of"]):
            continue
        if ("east_of" in o and lon <= o["east_of"]) or ("west_of" in o and lon >= o["west_of"]):
            continue
        return o
    return None


class VeniceGisSpeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = J(CFG)
        cls.extract = J(EXTRACT)
        cls.idx = J("public/data/venice/index.json")
        cls.rows = segs()

    def test_speed_names_cite_the_county_gis_https_url(self):
        rules = self.cfg["speed_names"]
        self.assertEqual(len(rules), 4)
        self.assertTrue(all(o["url"] == GIS_URL for o in rules))
        self.assertTrue(all(o["url"].startswith("https://") for o in rules))
        self.assertTrue(all(o.get("label") for o in rules))
        self.assertTrue(all(o["names"].startswith("^") for o in rules))
        self.assertTrue(all("speedlimit" in o["label"] for o in rules))
        self.assertTrue(all("research/venice_sarasota_gis/speedlimit_extract.json" in o["label"] for o in rules))
        mphs = [(o["names"], o["mph"]) for o in rules]
        self.assertEqual(mphs[0], ("^Pinebrook Road$", 40))
        self.assertEqual(mphs[1], ("^Pinebrook Road$", 40))
        self.assertEqual(mphs[2], ("^Laurel Road East$", 40))
        self.assertEqual(mphs[3], ("^Laurel Road East$", 45))

    def test_extract_lists_the_cited_objectids(self):
        self.assertEqual(self.extract["source_url"], GIS_URL)
        self.assertEqual(self.extract["field"], "speedlimit")
        by = {r["objectid"]: r for r in self.extract["records"]}
        for oid in PB_OIDS:
            self.assertEqual(by[oid]["full_name"], "PINEBROOK RD")
            self.assertEqual(by[oid]["speedlimit"], 40)
        for oid in LAU40_OIDS:
            self.assertEqual(by[oid]["full_name"], "LAUREL RD E")
            self.assertEqual(by[oid]["speedlimit"], 40)
        for oid in LAU45_OIDS:
            self.assertEqual(by[oid]["full_name"], "LAUREL RD E")
            self.assertEqual(by[oid]["speedlimit"], 45)
        self.assertEqual(set(by), set(PB_OIDS + LAU40_OIDS + LAU45_OIDS))

    def test_north_pinebrook_is_40_and_not_lsv_legal(self):
        pb = [(nm, s) for nm, s in self.rows if nm == "Pinebrook Road"]
        closed, open_s = [], []
        for nm, s in pb:
            lo, la = mid(s)
            rule = speed_name(self.cfg, nm, s[1], la, lo)
            if rule:
                closed.append(s)
                self.assertEqual(s[2], 40, (la, lo))
                self.assertEqual(s[3], "v", (la, lo))
                self.assertGreater(s[2], 35)
                self.assertEqual(self.idx["sources"][s[8]][0], GIS_URL)
            else:
                open_s.append(s)
                self.assertLessEqual(s[2], 35, (la, lo, s[2], s[3]))
                self.assertEqual((s[2], s[3]), (25, "i"), (la, lo))
        self.assertEqual(len(closed), 20)
        self.assertGreater(sum(miles(s) for s in closed), 2.0)
        self.assertLess(sum(miles(s) for s in closed), 2.1)
        self.assertGreater(len(open_s), 20)
        # Edmondson west-side piece is included; the short east-side stub at 27.1229,-82.41715 stays open
        self.assertTrue(any(abs(mid(s)[1] - 27.1229) < 1e-5 and mid(s)[0] < -82.41722 and s[2] == 40 for s in closed))
        self.assertTrue(any(abs(mid(s)[1] - 27.1229) < 1e-5 and mid(s)[0] > -82.4172 and s[2] == 25 for s in open_s))

    def test_laurel_eastern_mainline_is_40_or_45_and_not_lsv_legal(self):
        closed40, closed45 = [], []
        for nm, s in self.rows:
            if nm != "Laurel Road East":
                continue
            lo, la = mid(s)
            rule = speed_name(self.cfg, nm, s[1], la, lo)
            if not rule:
                continue
            self.assertEqual(s[1], "tertiary")
            self.assertEqual(s[3], "v")
            self.assertGreater(s[2], 35)
            self.assertEqual(s[2], rule["mph"], (la, lo))
            self.assertEqual(self.idx["sources"][s[8]][0], GIS_URL)
            (closed40 if s[2] == 40 else closed45).append(s)
        self.assertEqual(len(closed40), 5)
        self.assertEqual(len(closed45), 13)
        self.assertAlmostEqual(sum(miles(s) for s in closed40), 0.662, places=2)
        self.assertAlmostEqual(sum(miles(s) for s in closed45), 1.452, places=2)

    def test_already_closed_laurel_and_side_streets_unchanged(self):
        sec99, side25 = [], []
        for nm, s in self.rows:
            if nm != "Laurel Road East":
                continue
            if s[1] == "secondary" and s[2] == 99 and s[3] == "i":
                sec99.append(s)
            if s[1] in ("residential", "service") and s[2] == 25 and s[3] == "i":
                side25.append(s)
        self.assertEqual(len(sec99), 66)
        self.assertAlmostEqual(sum(miles(s) for s in sec99), 4.12, places=2)
        self.assertEqual(len(side25), 12)
        # no tertiary Laurel left at assumed 25 in the eastern window
        leftover = [
            s for nm, s in self.rows
            if nm == "Laurel Road East" and s[1] == "tertiary" and s[2] == 25
            and 27.1365 <= mid(s)[1] <= 27.138 and -82.4067 <= mid(s)[0] <= -82.3795
        ]
        self.assertEqual(leftover, [])

    def test_center_and_albee_unchanged(self):
        center = [s for nm, s in self.rows if nm == "Center Road"]
        self.assertEqual(len(center), 68)
        self.assertTrue(all(s[2] == 25 and s[3] == "i" for s in center))
        albee = [s for nm, s in self.rows if nm == "Albee Farm Road"]
        self.assertEqual(len(albee), 34)
        self.assertTrue(all(s[2] == 99 and s[3] == "i" for s in albee))

    def test_tiles_match_speed_names_rules(self):
        """A later build_region.py run of these rules must not reopen the closed stretches."""
        for nm, s in self.rows:
            if nm not in ("Pinebrook Road", "Laurel Road East"):
                continue
            lo, la = mid(s)
            rule = speed_name(self.cfg, nm, s[1], la, lo)
            if rule:
                self.assertEqual((s[2], s[3]), (rule["mph"], "v"), (nm, la, lo))
            elif nm == "Pinebrook Road":
                self.assertNotEqual((s[2], s[3]), (40, "v"), (nm, la, lo))


if __name__ == "__main__":
    unittest.main()
