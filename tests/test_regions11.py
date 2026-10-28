"""Greenwich and the next 10 (Oct 28 2026): boxes do not overlap a live region, every rule is cited
over https, the access check is recorded, key bans are on the drawn roads, the beta flag follows v3,
and town pages cite a source. Sarasota is not a region: it sits inside live siesta. Cocoa Beach replaces it."""
import json, os, glob, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
IDS = ["greenwich", "tyrone", "fayetteville", "senoia", "conyers", "augusta", "euharlee", "stmarys", "lowerkeys", "cocoabeach", "venice"]
# (region, road-name regex, flag) that must be applied on drawn segments; flag 1 = full ban (99 mph), 4 = golf-cart-only ban
KEY_BANS = [("greenwich", r"^I 95$", 1),
            ("fayetteville", r"^Glynn Street", 4),
            ("senoia", r"^Wells Street$", 4),
            ("conyers", r"^Purple Heart Highway$", 1),
            ("augusta", r"^Walton Way$", 4),
            ("euharlee", r"^Euharlee Road", 4),
            ("stmarys", r"^Winding Road$", 4),
            ("stmarys", r"^Osborne Road$", 4),
            ("cocoabeach", r"Atlantic Avenue$", 4)]
SEGS = {}
def segs(rid):
    if rid not in SEGS:
        N = J(f"public/data/{rid}/index.json")["names"]
        SEGS[rid] = [(N[s[0]], s) for f in glob.glob(os.path.join(ROOT, f"public/data/{rid}/tiles/*.json")) for s in json.load(open(f))]
    return SEGS[rid]
def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

class Regions11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = {r["id"]: r for r in J("public/data/regions.json")}
        cls.ST = J("research/beta_status.json")["regions"]
        a = J("research/access_sources.json")
        cls.ACC = {**a.get("state_law", {}), **a["regions"]}
    def test_eleven_and_no_sarasota_duplicate(self):
        for rid in IDS: self.assertIn(rid, self.R, rid)
        self.assertNotIn("sarasota", self.R)
        self.assertIn("CT", J("public/data/rules.json"))
        ct = J("public/data/rules.json")["CT"]
        self.assertEqual(ct["lsv"]["max_posted"], 25)
        self.assertTrue(ct["golf_cart"]["not_street_legal"])
        self.assertIn("14-289m", ct["lsv"]["cite"])
        self.assertIn("14-300g", ct["golf_cart"]["cite"])
    def test_bboxes_do_not_overlap(self):
        live = list(self.R.values())
        for a in live:
            if a["id"] not in IDS: continue
            for b in live:
                if a["id"] == b["id"]: continue
                self.assertFalse(overlap(a["bbox"], b["bbox"]), (a["id"], b["id"], a["bbox"], b["bbox"]))
        # the keys strip named in the request is already siesta; lowerkeys stays north of keywest
        self.assertGreaterEqual(self.R["lowerkeys"]["bbox"][0], self.R["keywest"]["bbox"][2])
        self.assertGreaterEqual(self.R["tyrone"]["bbox"][0], self.R["ptc"]["bbox"][2])
        self.assertGreaterEqual(self.R["fayetteville"]["bbox"][1], self.R["ptc"]["bbox"][3])
        self.assertLessEqual(self.R["senoia"]["bbox"][2], self.R["ptc"]["bbox"][0])
        self.assertLessEqual(self.R["venice"]["bbox"][2], self.R["siesta"]["bbox"][0])
        self.assertGreaterEqual(self.R["stmarys"]["bbox"][0], self.R["amelia"]["bbox"][2])
    def test_all_built(self):
        for rid in IDS:
            self.assertGreater(len(segs(rid)), 80, rid)
    def test_beta_flag_follows_v3(self):
        for rid in IDS:
            self.assertEqual(bool(self.R[rid].get("beta")), not self.ST[rid]["passes"], rid)
    def test_every_rule_cited_https(self):
        for rid in IDS:
            cfg = J(f"research/regions/{rid}.json")
            for o in cfg.get("speed_names", []) + cfg.get("bans", []) + cfg.get("cart_only_bans", []) + cfg.get("designated_names", []):
                self.assertTrue(o["url"].startswith("https://"), (rid, o)); self.assertTrue(o.get("label"), (rid, o))
            self.assertTrue(cfg["enforcement"]["sources"], rid)
            self.assertIn(cfg["enforcement"]["result"], ("bans_applied", "none_found", "bans_pending"), rid)
            self.assertTrue(all(s["url"].startswith("https://") for s in cfg["enforcement"]["sources"]), rid)
    def test_access_check_recorded(self):
        for rid in IDS:
            self.assertIn(rid, self.ACC, rid)
            self.assertTrue(self.ST[rid]["access_check"], rid)
    def test_key_bans_applied(self):
        for rid, pat, flag in KEY_BANS:
            hit = [s for nm, s in segs(rid) if re.search(pat, nm) and len(s) > 9 and s[9] == flag]
            self.assertTrue(hit, (rid, pat, flag))
            if flag == 1: self.assertTrue(all(s[2] == 99 for s in hit), (rid, pat))
    def test_undesignated_lists_stay_designated_only(self):
        # street lists we could not digitize must not fall through to "every slow street is a cart street"
        for rid in ("tyrone", "fayetteville", "conyers", "augusta", "cocoabeach"):
            self.assertTrue(self.R[rid]["rule"]["golf_cart"].get("designated_only"), rid)
        for rid in ("senoia", "euharlee", "stmarys"):
            self.assertFalse(self.R[rid]["rule"]["golf_cart"].get("designated_only"), rid)
    def test_town_pages(self):
        for rid in IDS:
            slug = self.R[rid]["slug"]; towns = glob.glob(os.path.join(ROOT, f"content/towns/{slug}/*.json"))
            self.assertTrue(towns, rid)
            for t in towns:
                d = json.load(open(t)); self.assertTrue(d["rules"], t)
                self.assertTrue(all(x["source_url"].startswith("https://") for x in d["rules"]), t)
                blob = json.dumps(d)
                self.assertNotRegex(blob, r"(?i)\bbeta\b|verified|\u2014")
    def test_greenwich_lsv_cap_is_25_not_35(self):
        self.assertEqual(self.R["greenwich"]["state"], "CT")
        self.assertNotIn("rule", self.R["greenwich"])  # state profile is the cap; no looser region override
if __name__ == "__main__": unittest.main()
