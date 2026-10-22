"""Nocatee (region-nocatee): beta, sourced access rules, golf carts capped at 25 mph, state roads banned."""
import json, os, glob, gzip, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
def segs():
    out = []
    for f in glob.glob(os.path.join(ROOT, "public/data/nocatee/tiles/*.json*")):
        raw = open(f, "rb").read(); raw = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        d = json.loads(raw); out.append(d)
    return out
class Nocatee(unittest.TestCase):
    def setUp(self):
        self.reg = next(r for r in J("public/data/regions.json") if r["id"] == "nocatee"); self.cfg = J("research/regions/nocatee.json")
    def test_beta_and_slug(self):
        self.assertTrue(self.reg["quality_hold"]); self.assertEqual(self.reg["slug"], "nocatee"); self.assertEqual(self.reg["state"], "FL")
    def test_cart_rule_25(self):
        g = self.reg["rule"]["golf_cart"]; self.assertEqual(g["max_posted"], 25); self.assertTrue(g["url"].startswith("https://"))
    def test_enforcement_source_recorded(self):
        e = self.cfg["enforcement"]; self.assertTrue(e["sources"]); self.assertTrue(all(s["url"].startswith("https://") for s in e["sources"]))
    def test_state_road_bans(self):
        import re
        pats = [re.compile(b["names"]) for b in self.cfg["bans"] if not b.get("per_segment")]   # whole-road bans; Crosswater/Cross Town are per-segment (NocateeRoads)
        for name in ["US 1", "SR A1A", "CR 210", "Nocatee Parkway", "I-95", "SR 9B"]:
            self.assertTrue(any(p.search(name) for p in pats), name)
        for name in ["CR 210A", "Crosswater Parkway"]:
            self.assertFalse(any(p.search(name) for p in pats), name)
    def test_valley_ridge_45(self):
        self.assertTrue(any(o["names"] == "^Valley Ridge Boulevard$" and o["mph"] == 45 for o in self.cfg["speed_names"]))
    def test_data_built(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "public/data/nocatee/index.json")))
if __name__ == "__main__": unittest.main()

def _segs(names):
    idx = J("public/data/nocatee/index.json"); N = idx["names"]; S = idx["sources"]
    for f in glob.glob(os.path.join(ROOT, "public/data/nocatee/tiles/*.json")):
        for s in json.load(open(f)):
            if N[s[0]] in names: yield N[s[0]], s, (S[s[8]] if len(s) > 8 and s[8] >= 0 else None)
class NocateeRoads(unittest.TestCase):
    def test_crosswater_crosstown_never_cart_legal(self):
        n = 0
        for nm, s, src in _segs({"Crosswater Parkway", "Cross Town Drive"}):
            n += 1; self.assertGreater(s[2], 25, (nm, s[2], s[3]))
        self.assertGreater(n, 10)
    def test_valley_ridge_red_and_sourced_to_nocatee(self):
        n = 0
        for nm, s, src in _segs({"Valley Ridge Boulevard"}):
            n += 1; self.assertGreaterEqual(s[2], 45); self.assertEqual(s[3], "v"); self.assertTrue(src and src[0].startswith("https://"))
        self.assertGreater(n, 5)
        o = J("research/regions/nocatee.json")["speed_names"][0]; self.assertIn("Nocatee", o["label"])
    def test_max_mph_ban_filter_only_lower(self):
        b = [x for x in J("research/regions/nocatee.json")["bans"] if x.get("max_mph")]
        self.assertEqual({x["names"] for x in b}, {"^Cross Town Drive$", "^Crosswater Parkway$"}); self.assertTrue(all(x["max_mph"] == 25 for x in b))
