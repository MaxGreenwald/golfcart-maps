"""30A / South Walton audit (2026-10-21, research/30a_audit_2026-10-21.md).
Source: Walton County Sheriff LSV page https://waltonso.org/lsv/ and its map
(https://waltonso.org/wp-content/uploads/2022/10/lsv_map_102022.png, red = prohibited for LSVs).
Roads red on that map must be blocked for LSVs; County Road 30A itself is NOT red (LSV-legal at <=35)."""
import glob, json, math, os, subprocess, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "public/data/30a")
IDX = json.load(open(os.path.join(D, "index.json")))
SEGS = [s for f in glob.glob(os.path.join(D, "tiles/*.json")) for s in json.load(open(f))]
CFG = json.load(open(os.path.join(ROOT, "research/regions/30a.json")))
NAMES = IDX["names"]
lsv_ok = lambda s: s[2] is not None and s[2] <= 35   # FL LSV rule (rules.json FL.lsv.max_posted 35); bans are written as 99
mi = lambda p: sum(math.hypot((a[0] - b[0]) * 96000, (a[1] - b[1]) * 110540) for a, b in zip(p, p[1:])) / 1609


def ok_miles(name, lat_min=-90, lat_max=90):
    return sum(mi(s[7]) for s in SEGS if NAMES[s[0]] == name and lsv_ok(s) and lat_min <= s[7][len(s[7]) // 2][1] <= lat_max)


class Audit30A(unittest.TestCase):
    def test_sheriff_red_roads_blocked(self):
        for n in ("County Highway 283", "CR 283", "North County Highway 395", "Old Blue Mountain Road", "South Eden Park Drive"):
            self.assertEqual(round(ok_miles(n), 3), 0, n)
        self.assertEqual(round(ok_miles("South County Highway 83", 30.357), 3), 0, "CR 83 between TDC office and US 98")

    def test_alys_rosemary_seaside_streets_blocked(self):
        for n in ("East Water Street", "Rosemary Avenue", "Geoff Wilder Lane", "Nonesuch Way", "Seaside Avenue", "Savannah Street", "Ruskin Place"):
            self.assertEqual(round(ok_miles(n), 3), 0, n)

    def test_30a_itself_stays_open_for_lsvs(self):
        tot = sum(ok_miles(n) for n in ("East County Highway 30A", "West County Highway 30A"))
        self.assertGreater(tot, 15)

    def test_us98_331_blocked(self):
        for s in SEGS:
            if NAMES[s[0]].startswith(("US Highway 98", "US Highway 331", "Emerald Coast Parkway")) and s[1] in ("trunk", "primary"):
                self.assertFalse(lsv_ok(s), NAMES[s[0]])

    def test_unbanned_rest_of_cr83_and_cr395_south(self):
        self.assertGreater(ok_miles("South County Highway 83", -90, 30.352), 0.5)
        self.assertGreater(ok_miles("South County Highway 395"), 0.3)   # south of the fire station: not red on the map

    def test_bans_cite_sheriff(self):
        for b in CFG["bans"]:
            self.assertEqual(b["url"], "https://waltonso.org/lsv/")
        labels = [s[1] for s in IDX["sources"]]
        self.assertTrue(any("CR 283" in l for l in labels))

    def test_golf_carts_not_street_legal_label(self):
        self.assertTrue(any("Golf carts (non-LSV) are not allowed on any Walton County public road" in s for s in CFG["sources"]))

    def test_roadrule_agrees(self):
        js = ("const R=require('%s/public/roadrule.js'),fs=require('fs');const D='%s/public/data/';"
              "const rules=JSON.parse(fs.readFileSync(D+'rules.json'));const reg=JSON.parse(fs.readFileSync(D+'regions.json')).find(x=>x.id=='30a');"
              "const idx=JSON.parse(fs.readFileSync(D+'30a/index.json'));let bad=0;const r=R.ruleFor(rules,reg,'lsv');"
              "for(const f of fs.readdirSync(D+'30a/tiles'))for(const s of JSON.parse(fs.readFileSync(D+'30a/tiles/'+f)))"
              "if(/^(County Highway 283|CR 283|North County Highway 395)$/.test(idx.names[s[0]])&&R.cls(s,r)!==3)bad++;console.log(bad)") % (ROOT, ROOT)
        self.assertEqual(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
