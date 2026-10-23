"""regions-25 batch (Oct 22 2026): every rule cited over https, access check recorded, key bans applied, beta flag follows v3, town pages sourced."""
import json, os, glob, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
IDS = ["ocnj", "lbi", "fmb", "sanibel", "capemay", "topsail", "carolinabeach", "emeraldisle", "clearwater", "stpete", "newport", "pensacola", "brunswick",
       "crystalbeach", "padre", "bocagrande", "pawleys", "dauphin", "stgeorge", "capesanblas", "delbeaches", "edisto", "nsb", "kelleys", "chincoteague"]
# (region, road-name regex, flag) that must be applied on drawn segments; flag 1 = full ban (99 mph), 4 = golf-cart-only ban
KEY_BANS = [("ocnj", r"^Bay Avenue$", 1), ("ocnj", r"^West Avenue$", 1), ("ocnj", r"^NJ 52$", 1), ("capemay", r"^Garden State Parkway$", 1),
            ("topsail", r"Anderson Boulevard$", 1), ("newport", r"^Pacific Coast Highway$", 1), ("crystalbeach", r"^(State Highway|TX) 87$", 1),
            ("padre", r"^(State Highway|TX) 361$", 1), ("padre", r"Kennedy Memorial Causeway$", 1), ("delbeaches", r"^Coastal Highway$", 1),
            ("nsb", r"Atlantic Avenue$", 1), ("pawleys", r"^Myrtle Avenue$", 1),
            ("pensacola", r"^Pensacola Beach Boulevard$", 4), ("pensacola", r"^Navarre Beach Causeway$", 4),
            ("carolinabeach", r"^Fort Fisher Boulevard", 4), ("emeraldisle", r"^Emerald Drive$", 4), ("emeraldisle", r"^Coast Guard Road$", 4),
            ("stpete", r"^Gulf Boulevard$", 4), ("stpete", r"^Pinellas Bayway$", 4), ("stgeorge", r"Gulf Beach Drive", 4), ("capesanblas", r"^US 98$|^Cape San Blas Road$", 4),
            ("edisto", r"^Palmetto Boulevard$", 4), ("chincoteague", r"^Main Street$", 4)]
SEGS = {}
def segs(rid):
    if rid not in SEGS:
        N = J(f"public/data/{rid}/index.json")["names"]
        SEGS[rid] = [(N[s[0]], s) for f in glob.glob(os.path.join(ROOT, f"public/data/{rid}/tiles/*.json")) for s in json.load(open(f))]
    return SEGS[rid]

class Regions25(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = {r["id"]: r for r in J("public/data/regions.json")}; cls.ST = J("research/beta_status.json")["regions"]; a = J("research/access_sources.json"); cls.ACC = {**a.get("state_law", {}), **a["regions"]}   # newport: state law, no local ordinance (recorded under state_law)
    def test_all_present_and_built(self):
        for rid in IDS:
            self.assertIn(rid, self.R, rid); self.assertGreater(len(segs(rid)), 300, rid)
    def test_beta_flag_follows_v3(self):
        for rid in IDS:
            self.assertEqual(bool(self.R[rid].get("beta")), not self.ST[rid]["passes"], rid)
    def test_every_rule_cited_https(self):
        for rid in IDS:
            cfg = J(f"research/regions/{rid}.json")
            for o in cfg.get("speed_names", []) + cfg.get("bans", []) + cfg.get("cart_only_bans", []):
                self.assertTrue(o["url"].startswith("https://"), (rid, o)); self.assertTrue(o.get("label"), (rid, o))
            self.assertTrue(cfg["enforcement"]["sources"], rid)
            self.assertTrue(all(s["url"].startswith("https://") for s in cfg["enforcement"]["sources"]), rid)
    def test_access_check_recorded(self):
        for rid in IDS:
            self.assertIn(rid, self.ACC, rid); self.assertTrue(self.ST[rid]["access_check"], rid)
    def test_key_bans_applied(self):
        for rid, pat, flag in KEY_BANS:
            hit = [s for nm, s in segs(rid) if re.search(pat, nm) and len(s) > 9 and s[9] == flag]
            self.assertTrue(hit, (rid, pat, flag))
            if flag == 1: self.assertTrue(all(s[2] == 99 for s in hit), (rid, pat))
    def test_bridge_bans_scoped_to_bridges(self):
        # the Pensacola bridge bans use exact OSM way ids, so the rest of Pensacola Beach Blvd / Navarre causeway stays open
        n = [s for nm, s in segs("pensacola") if nm == "Pensacola Beach Boulevard"]
        self.assertGreater(len([s for s in n if not (len(s) > 9 and s[9] in (1, 4))]), 0)
        self.assertEqual([s for nm, s in segs("pensacola") if len(s) > 9 and s[9] == 1], [], "no LSV ban on the Pensacola bridges without a source")
    def test_town_pages(self):
        for rid in IDS:
            slug = self.R[rid]["slug"]; towns = glob.glob(os.path.join(ROOT, f"content/towns/{slug}/*.json"))
            self.assertTrue(towns, rid)
            for t in towns:
                d = json.load(open(t)); self.assertTrue(d["rules"], t)
                self.assertTrue(all(x["source_url"].startswith("https://") for x in d["rules"]), t)
if __name__ == "__main__": unittest.main()
