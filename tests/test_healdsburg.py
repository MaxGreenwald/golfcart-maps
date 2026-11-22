"""Healdsburg, CA: California state caps (CVC 21716 golf carts 25 mph, CVC 21260 LSVs 35 mph) with street
speeds from Healdsburg Municipal Code Chapter 10.50, clipped to the city limits."""
import glob, json, os, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
RID = "healdsburg"

def segs():
    idx = J(f"public/data/{RID}/index.json")
    out = []
    for f in glob.glob(os.path.join(ROOT, f"public/data/{RID}/tiles/*.json")):
        for s in json.load(open(f)):
            out.append((idx["names"][s[0]], s))
    return out

def near(s, lat, lon, d=0.0012):
    return any(abs(p[1] - lat) < d and abs(p[0] - lon) < d for p in s[7])

class Healdsburg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = {r["id"]: r for r in J("public/data/regions.json")}
        cls.cfg = J(f"research/regions/{RID}.json")
        cls.S = segs()

    def test_region_entry(self):
        r = self.R[RID]
        self.assertEqual((r["state"], r["slug"]), ("CA", "healdsburg"))
        st = J("research/beta_status.json")["regions"][RID]   # beta flag follows the v3 bar, not a fixed value
        self.assertEqual(bool(r.get("beta")), not st["passes"])
        self.assertNotIn("rule", r)   # no local plan: the California rule in rules.json applies
        a = r["bbox"]
        for o in self.R.values():
            if o["id"] != RID:
                b = o["bbox"]
                self.assertFalse(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3], o["id"])

    def test_city_code_speeds(self):
        def mph_at(name, lat, lon):
            v = {s[2] for n, s in self.S if n == name and near(s, lat, lon, 0.0004)}
            self.assertTrue(v, (name, lat, lon)); return v
        self.assertEqual(mph_at("Healdsburg Avenue", 38.6110, -122.8707), {20})   # Piper to Mill
        self.assertEqual(mph_at("Healdsburg Avenue", 38.6345, -122.8741), {30})   # Parkland Farms to Powell (OSM says 35)
        self.assertEqual(mph_at("Healdsburg Avenue", 38.6413, -122.8731), {35})   # north of Parkland Farms
        self.assertEqual(mph_at("Vine Street", 38.60998, -122.87255), {25})         # OSM says 35
        self.assertEqual(mph_at("Mill Street", 38.6079, -122.8711), {25})         # OSM says 45
        self.assertEqual(mph_at("Dry Creek Road", 38.6262, -122.8760), {25})

    def test_speed_list_cites_the_code(self):
        sn = self.cfg["speed_names"]
        self.assertGreaterEqual(len(sn), 20)
        for o in sn:
            self.assertLessEqual(o["mph"], 35, o["label"])
            self.assertEqual(o["url"], "https://ecode360.com/47365641")
            self.assertIn("Healdsburg Municipal Code 10.50", o["label"])
            self.assertEqual(o.get("poly"), "healdsburg.json")

    def test_us101_closed(self):
        hwy = [s for n, s in self.S if s[1] == "motorway"]
        self.assertTrue(hwy)
        self.assertTrue(all(s[2] > 35 for s in hwy))

    def test_clipped_to_city(self):
        names = {n for n, _ in self.S}
        for far in ("West Dry Creek Road", "Los Amigos Road", "Lytton Station Road", "Fredson Road", "Kinley Drive"):
            self.assertNotIn(far, names)

    def test_records_and_town_page(self):
        enf = self.cfg["enforcement"]
        self.assertEqual(enf["result"], "bans_applied")
        self.assertTrue(all(s["url"].startswith("https://") for s in enf["sources"]))
        acc = J("research/access_sources.json")
        self.assertIn("21716", acc["state_law"][RID]["law"])
        t = J("content/towns/healdsburg/healdsburg.json")
        self.assertTrue(all(x["source_url"].startswith("https://") for x in t["rules"]))
        self.assertLessEqual(len(t["answer_short"].split()), 60)
        self.assertNotRegex(json.dumps(t, ensure_ascii=False), r"(?i)\bbeta\b|verified|\u2014")

if __name__ == "__main__":
    unittest.main()
