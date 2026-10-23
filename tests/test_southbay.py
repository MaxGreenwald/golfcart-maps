"""South Bay LA (region-southbay): cited city speed lists, the Strand/pier bans, PCH golf carts crossing only, Rolling Hills private."""
import json, os, glob, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
IDX = None
def segs():
    global IDX
    IDX = IDX or J("public/data/southbay/index.json"); N, S = IDX["names"], IDX["sources"]
    for f in glob.glob(os.path.join(ROOT, "public/data/southbay/tiles/*.json")):
        for s in json.load(open(f)):
            yield N[s[0]], s, (S[s[8]] if len(s) > 8 and s[8] >= 0 else None)
def mid(s): p = s[7][len(s[7]) // 2]; return p[1], p[0]
def ring(f):
    g = J("research/city_limits/" + f)["geojson"]; return g["coordinates"][0] if g["type"] == "Polygon" else max((p[0] for p in g["coordinates"]), key=len)
def inside(lat, lon, r):
    c = False
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i - 1][:2], r[i][:2]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: c = not c
    return c

class SouthBayConfig(unittest.TestCase):
    def setUp(self):
        self.reg = next(r for r in J("public/data/regions.json") if r["id"] == "southbay"); self.cfg = J("research/regions/southbay.json")
    def test_region_entry(self):
        st = J("research/beta_status.json")["regions"]["southbay"]   # beta flag follows the v3 bar, not a fixed value
        self.assertEqual(bool(self.reg.get("beta")), not st["passes"]); self.assertEqual(self.reg["slug"], "southbay"); self.assertEqual(self.reg["state"], "CA")
        self.assertEqual(self.reg["rule"]["golf_cart"]["max_posted"], 25)
        for c in ["Manhattan Beach", "Hermosa Beach", "Redondo Beach", "Torrance", "Palos Verdes Estates", "Rancho Palos Verdes", "Rolling Hills Estates"]:
            self.assertIn(c, json.dumps(self.reg["cover"]), c)
    def test_every_rule_cited_https(self):
        for o in self.cfg["speed_names"] + self.cfg["bans"] + self.cfg["cart_only_bans"]:
            self.assertTrue(o["url"].startswith("https://"), o); self.assertTrue(o["label"], o)
        self.assertTrue(all(s["url"].startswith("https://") for s in self.cfg["enforcement"]["sources"]))
        self.assertIn("southbay", J("research/access_sources.json")["regions"])
    def test_strand_pier_freeway_bans(self):
        pats = [re.compile(b["names"]) for b in self.cfg["bans"]]
        for n in ["The Strand", "Strand", "Pier Plaza", "Manhattan Beach Pier", "I 405", "I-405", "I 105", "I 110", "CA 91", "San Diego Freeway"]:
            self.assertTrue(any(p.search(n) for p in pats), n)
        for n in ["Strand Street", "Pacific Coast Highway", "Hermosa Avenue", "Manhattan Avenue"]:
            self.assertFalse(any(p.search(n) for p in pats), n)
    def test_pch_cart_only_ban_not_lsv(self):
        pats = [re.compile(b["names"]) for b in self.cfg["cart_only_bans"]]
        for n in ["Pacific Coast Highway", "South Pacific Coast Highway", "CA 1", "CA 213"]:
            self.assertTrue(any(p.search(n) for p in pats), n)
        self.assertFalse(any(re.search(b["names"], "Pacific Coast Highway") for b in self.cfg["bans"]), "PCH must not be a full (LSV) ban")
    def test_hermosa_default_25_and_rolling_hills_private(self):
        self.assertTrue(any(o["names"] == "." and o["mph"] == 25 and o.get("poly") == "hermosa_beach.json" for o in self.cfg["speed_names"]))
        self.assertEqual(self.cfg["private_polys"], ["rolling_hills.json"])
        self.assertTrue(any("Rolling Hills" in u for u in self.cfg["unverified"]))

class SouthBayData(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.S = list(segs())
    def test_built(self):
        self.assertGreater(len(self.S), 20000)
    def test_no_footways_or_strand(self):
        for nm, s, _ in self.S:
            self.assertNotIn(s[1], ("footway", "pedestrian", "path", "cycleway") if s[3] != "c" else (), (nm, s[1]))
            if re.match(r"^(The )?Strand$", nm): self.assertEqual(s[2], 99, nm)
    def test_pch_golf_carts_crossing_only(self):
        n = 0
        for nm, s, _ in self.S:
            if re.search(r"Pacific Coast Highway$", nm) and s[1] in ("primary", "trunk"):
                n += 1; self.assertTrue(s[2] > 25 or (len(s) > 9 and s[9] in (1, 4)), (nm, s[2], s[3], s[9:]))
        self.assertGreater(n, 50)
    def test_pch_redondo_torrance_speeds(self):
        got = {}
        for nm, s, src in self.S:
            if re.search(r"Pacific Coast Highway$", nm) and src and s[3] == "v":
                got.setdefault(src[0].split("/")[2], set()).add(s[2])
        self.assertTrue({35, 40, 45} <= got.get("ecode360.com", set()), got)          # Redondo Beach MC 3-7.503
        self.assertIn(45, got.get("gocodebook.com", set()), got)                      # Torrance 61.10 east of Vista del Parque
        fhwa = [(nm, s[2]) for nm, s, src in self.S if re.search(r"Pacific Coast Highway$", nm) and src and "FHWA" in src[1]]
        self.assertEqual(fhwa, [], "city codes override the FHWA 60 mph on PCH")
    def test_mb_sepulveda_35_not_fhwa_60(self):
        r = ring("manhattan_beach.json"); n = 0
        for nm, s, src in self.S:
            if re.match(r"^(North |South )?Sepulveda Boulevard$", nm) and s[1] == "primary" and inside(*mid(s), r):
                n += 1; self.assertEqual(s[2], 35, (nm, s[2], src)); self.assertIn("thembnews", src[0])
        self.assertGreater(n, 20)
    def test_rpv_hawthorne_45(self):
        r = ring("rancho_palos_verdes.json"); n = 0
        for nm, s, src in self.S:
            if nm == "Hawthorne Boulevard" and inside(*mid(s), r) and s[1] in ("primary", "secondary"):
                n += 1; self.assertEqual(s[2], 45, (nm, s[2]))
        self.assertGreater(n, 10)
    def test_hermosa_residential_25(self):
        r = ring("hermosa_beach.json"); n = 0
        for nm, s, src in self.S:
            if s[1] == "residential" and inside(*mid(s), r) and s[3] == "v":
                n += 1; self.assertEqual(s[2], 25, nm)
        self.assertGreater(n, 100)
    def test_rolling_hills_not_drawn(self):
        r = ring("rolling_hills.json")
        bad = [nm for nm, s, _ in self.S if inside(*mid(s), r) and nm in ("Portuguese Bend Road", "Crest Road West", "Georgeff Road", "Running Brand Road", "Meadowlark Lane")]
        self.assertEqual(bad, [])
    def test_town_pages(self):
        towns = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(ROOT, "content/towns/southbay/*.json"))}
        self.assertTrue({"manhattan-beach", "hermosa-beach", "redondo-beach", "torrance", "palos-verdes-estates", "rancho-palos-verdes", "rolling-hills-estates"} <= towns)
        for t in towns:
            d = J(f"content/towns/southbay/{t}.json"); self.assertTrue(all(x["source_url"].startswith("https://") for x in d["rules"])); self.assertTrue(d["local_resources"])
if __name__ == "__main__": unittest.main()
