"""24 towns added so the map has at least 100 regions.

Boxes do not overlap. Every new region has an https citation, an enforcement
record, and a town page. A ban that names a drawn road is on those segments.
Plain golf carts stay off streets where the street list was not digitized.
"""
import glob, json, os, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
IDS = ["fairhope", "ocracoke", "dadecity", "mountdora", "pinehurst", "beaufort", "portroyal",
       "georgetown", "horseshoebay", "surfside", "colonialbeach", "flaglerbeach", "oriental",
       "celina", "capecharles", "sunlakes", "morrobay", "pismo", "howey", "apalachicola",
       "cedarkey", "islamorada", "keylargo", "crystalriver"]
# Roads that must be banned when the extract contains them. flag 1 = everyone, flag 4 = golf carts only.
KEY = [("fairhope", r"Greeno Road|US 98", 1),
       ("pinehurst", r"NC 211|US 15", 4),
       ("surfside", r"Bluewater Highway|Fort Velasco", 4),
       ("flaglerbeach", r"A1A|Oceanshore|Moody", 4),
       ("sunlakes", r"Alma School Road", 1),
       ("mountdora", r"Donnelly Street|US 441", 1),
       ("beaufort", r"Ribaut Road|Boundary Street|Carteret Street", 4),
       ("dadecity", r"US 301|US 98|CR 52", 4)]
DESIGNATED_ONLY = ("dadecity", "flaglerbeach", "colonialbeach", "capecharles", "howey",
                   "apalachicola", "cedarkey", "islamorada", "keylargo", "crystalriver")
SEGS = {}
def segs(rid):
    if rid not in SEGS:
        N = J(f"public/data/{rid}/index.json")["names"]
        SEGS[rid] = [(N[s[0]], s) for f in glob.glob(os.path.join(ROOT, f"public/data/{rid}/tiles/*.json")) for s in json.load(open(f))]
    return SEGS[rid]
def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

class Regions100(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = {r["id"]: r for r in J("public/data/regions.json")}
        a = J("research/access_sources.json")
        cls.ACC = {**a.get("state_law", {}), **a["regions"]}
    def test_count(self):
        self.assertGreaterEqual(len(self.R), 100)
        for rid in IDS: self.assertIn(rid, self.R, rid)
        self.assertEqual(len(IDS), 24)
    def test_no_overlap(self):
        live = list(self.R.values())
        for a in live:
            if a["id"] not in IDS: continue
            for b in live:
                if a["id"] == b["id"]: continue
                self.assertFalse(overlap(a["bbox"], b["bbox"]), (a["id"], b["id"]))
    def test_built(self):
        for rid in IDS:
            self.assertGreater(len(segs(rid)), 40, rid)
    def test_citations_and_enforcement(self):
        for rid in IDS:
            cfg = J(f"research/regions/{rid}.json")
            for o in cfg.get("bans", []) + cfg.get("cart_only_bans", []) + cfg.get("designated_names", []):
                self.assertTrue(str(o.get("url", "")).startswith("https://"), (rid, o.get("label")))
                self.assertTrue(o.get("label"), rid)
            enf = cfg["enforcement"]
            self.assertIn(enf["result"], ("bans_applied", "none_found"), rid)
            self.assertTrue(all(s["url"].startswith("https://") for s in enf["sources"]), rid)
            self.assertIn(rid, self.ACC, rid)
    def test_fairhope_carts_are_not_street_legal(self):
        g = self.R["fairhope"]["rule"]["golf_cart"]
        self.assertTrue(g["not_street_legal"])
        self.assertIn("Greeno", g["cite"])
    def test_mountdora_cap_is_30(self):
        g = self.R["mountdora"]["rule"]["golf_cart"]
        self.assertEqual(g["max_posted"], 30)
        self.assertFalse(g["designated_only"])
    def test_undesignated_lists_stay_red_for_carts(self):
        rules = J("public/data/rules.json")
        for rid in DESIGNATED_ONLY:
            merged = {**rules[self.R[rid]["state"]]["golf_cart"], **(self.R[rid].get("rule") or {}).get("golf_cart", {})}
            if rid == "fairhope":
                continue
            self.assertTrue(merged.get("designated_only"), rid)
    def test_key_bans_when_the_road_is_drawn(self):
        for rid, pat, flag in KEY:
            hit = [(nm, s) for nm, s in segs(rid) if re.search(pat, nm)]
            if not hit:
                continue
            banned = [s for nm, s in hit if len(s) > 9 and s[9] == flag]
            self.assertTrue(banned, (rid, pat, flag, hit[0][0]))
    def test_town_pages(self):
        for rid in IDS:
            slug = self.R[rid]["slug"]
            towns = glob.glob(os.path.join(ROOT, f"content/towns/{slug}/*.json"))
            self.assertTrue(towns, rid)
            for t in towns:
                d = json.load(open(t))
                self.assertTrue(d["rules"], t)
                self.assertTrue(all(x["source_url"].startswith("https://") for x in d["rules"]), t)
                blob = json.dumps(d)
                self.assertNotRegex(blob, r"(?i)\bbeta\b|verified|\u2014")

if __name__ == "__main__":
    unittest.main()
