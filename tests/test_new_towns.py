"""Towns added where a statute or ordinance opens a usable street network.

Boxes do not overlap another region. Plain golf carts stay off streets where
no local permit was found. Each new region has an https citation, an
enforcement record, and a town page.
"""
import glob, json, os, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
IDS = ["traversecity", "holland", "mystic", "boothbay", "jaxbeaches", "atlanticcity", "scottsdale", "madison", "newportri"]
CARTS_OFF = ("traversecity", "holland", "mystic", "boothbay", "atlanticcity", "scottsdale", "madison", "newportri")

def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

class NewTowns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = {r["id"]: r for r in J("public/data/regions.json")}
        rules = J("public/data/rules.json")
        cls.rules = rules
        a = J("research/access_sources.json")
        cls.ACC = {**a.get("state_law", {}), **a["regions"]}

    def test_present_and_distinct_from_newport_beach(self):
        self.assertGreaterEqual(len(self.R), 109)
        for rid in IDS:
            self.assertIn(rid, self.R, rid)
        self.assertEqual(self.R["newport"]["state"], "CA")
        self.assertEqual(self.R["newportri"]["state"], "RI")
        self.assertNotEqual(self.R["newport"]["slug"], self.R["newportri"]["slug"])

    def test_no_overlap(self):
        live = list(self.R.values())
        for a in live:
            if a["id"] not in IDS:
                continue
            for b in live:
                if a["id"] == b["id"]:
                    continue
                self.assertFalse(overlap(a["bbox"], b["bbox"]), (a["id"], b["id"]))

    def test_built(self):
        for rid in IDS:
            tiles = glob.glob(os.path.join(ROOT, f"public/data/{rid}/tiles/*.json"))
            self.assertTrue(tiles, rid)
            n = sum(len(json.load(open(f))) for f in tiles)
            self.assertGreater(n, 40, rid)

    def test_plain_carts_stay_off_without_a_permit(self):
        for rid in CARTS_OFF:
            merged = {**self.rules[self.R[rid]["state"]]["golf_cart"], **(self.R[rid].get("rule") or {}).get("golf_cart", {})}
            self.assertTrue(merged.get("not_street_legal"), rid)
        beaches = {**self.rules["FL"]["golf_cart"], **(self.R["jaxbeaches"].get("rule") or {}).get("golf_cart", {})}
        self.assertTrue(beaches.get("designated_only"))

    def test_caps(self):
        self.assertEqual(self.rules["CT"]["lsv"]["max_posted"], 25)
        self.assertEqual(self.rules["NJ"]["lsv"]["max_posted"], 25)
        self.assertEqual(self.rules["MI"]["lsv"]["max_posted"], 35)
        self.assertEqual(self.R["madison"]["rule"]["lsv"]["max_posted"], 35)
        self.assertEqual(self.R["scottsdale"]["rule"]["lsv"]["max_posted"], 35)
        self.assertIn("12.792", self.R["madison"]["rule"]["lsv"]["cite"])
        self.assertIn("28-966", self.R["scottsdale"]["rule"]["lsv"]["cite"])

    def test_citations_and_enforcement(self):
        for rid in IDS:
            cfg = J(f"research/regions/{rid}.json")
            for o in cfg.get("bans", []) + cfg.get("cart_only_bans", []):
                self.assertTrue(str(o.get("url", "")).startswith("https://"), (rid, o.get("label")))
                self.assertTrue(o.get("label"), rid)
            enf = cfg["enforcement"]
            self.assertIn(enf["result"], ("bans_applied", "none_found"), rid)
            self.assertTrue(all(s["url"].startswith("https://") for s in enf["sources"]), rid)
            self.assertIn(rid, self.ACC, rid)

    def test_town_pages(self):
        for rid in IDS:
            slug = self.R[rid]["slug"]
            towns = glob.glob(os.path.join(ROOT, f"content/towns/{slug}/*.json"))
            self.assertTrue(towns, rid)
            for t in towns:
                d = json.load(open(t, encoding="utf-8"))
                self.assertTrue(d["rules"], t)
                self.assertTrue(all(x["source_url"].startswith("https://") for x in d["rules"]), t)
                self.assertLessEqual(len(d["answer_short"].split()), 60, t)
                blob = json.dumps(d)
                self.assertNotRegex(blob, r"(?i)\bbeta\b|verified|\u2014")

    def test_new_states_are_in_the_rule_file(self):
        for st in ("MI", "WI", "RI"):
            self.assertIn(st, self.rules)
            self.assertIn("lsv", self.rules[st])
            self.assertIn("golf_cart", self.rules[st])

if __name__ == "__main__":
    unittest.main()
