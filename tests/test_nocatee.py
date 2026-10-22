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
        self.assertTrue(self.reg["beta"]); self.assertEqual(self.reg["slug"], "nocatee"); self.assertEqual(self.reg["state"], "FL")
    def test_cart_rule_25(self):
        g = self.reg["rule"]["golf_cart"]; self.assertEqual(g["max_posted"], 25); self.assertTrue(g["url"].startswith("https://"))
    def test_enforcement_source_recorded(self):
        e = self.cfg["enforcement"]; self.assertTrue(e["sources"]); self.assertTrue(all(s["url"].startswith("https://") for s in e["sources"]))
    def test_state_road_bans(self):
        import re
        pats = [re.compile(b["names"]) for b in self.cfg["bans"]]
        for name in ["US 1", "SR A1A", "CR 210", "Nocatee Parkway", "I-95", "SR 9B"]:
            self.assertTrue(any(p.search(name) for p in pats), name)
        for name in ["CR 210A", "Crosswater Parkway"]:
            self.assertFalse(any(p.search(name) for p in pats), name)
    def test_valley_ridge_45(self):
        self.assertTrue(any(o["names"] == "^Valley Ridge Boulevard$" and o["mph"] == 45 for o in self.cfg["speed_names"]))
    def test_data_built(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "public/data/nocatee/index.json")))
if __name__ == "__main__": unittest.main()
