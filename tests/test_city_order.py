"""City picker (city chip in the top chip row): A-Z by display name, sorted in code at render time (public/regions.js),
so a new region added anywhere in data/regions.json lands in order. San Diego stays the default."""
import json, os, re, subprocess, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PUB = os.path.join(ROOT, "public")
NODE = """const G=require(process.argv[1]),R=JSON.parse(require('fs').readFileSync(process.argv[2]));
const extra=[{id:'zz_new',short:'Aardvark Bay',beta:true},{id:'hid',short:'Hidden Town',hidden:true}];
console.log(JSON.stringify({web:G.pickerList(R,null,false),ios:G.pickerList(R,null,true),plus:G.pickerList(R.concat(extra),null,false),keep:G.pickerList(R.concat(extra),'hid',false),ids:R.map(r=>r.id)}))"""

def run():
    out = subprocess.run(["node", "-e", NODE, os.path.join(PUB, "regions.js"), os.path.join(PUB, "data/regions.json")],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def read(p):
    with open(p) as f: return f.read()

def label(t): return re.sub(r" \(beta\)$", "", t)

class CityOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run(); cls.regs = json.loads(read(os.path.join(PUB, "data/regions.json")))

    def assertAZ(self, opts):
        names = [label(o["text"]) for o in opts]
        self.assertEqual(names, sorted(names, key=str.casefold), "picker is not A-Z")

    def test_alphabetical(self):
        self.assertAZ(self.r["web"]); self.assertAZ(self.r["ios"])

    def test_every_visible_region_once(self):
        vis = sorted(r["id"] for r in self.regs if not r.get("hidden"))
        self.assertEqual(sorted(o["id"] for o in self.r["web"]), vis)

    def test_new_region_lands_in_order(self):
        ids = [o["id"] for o in self.r["plus"]]
        self.assertAZ(self.r["plus"]); self.assertNotIn("hid", ids)
        self.assertIn("zz_new", ids)   # appended last in regions.json, still sorted into place by assertAZ above
        self.assertIn("hid", [o["id"] for o in self.r["keep"]])   # hidden region opened by ?r= stays selectable

    def test_beta_tag_web_only(self):
        self.assertFalse(any("(beta)" in o["text"] for o in self.r["web"]))
        self.assertFalse(any("(beta)" in o["text"] for o in self.r["ios"]))

    def test_san_diego_default(self):
        # regions.json keeps San Diego first (REGIONS[0] fallback); app.js falls back to 'sd' with no path/saved choice
        self.assertEqual(self.r["ids"][0], "sd")
        app = read(os.path.join(PUB, "app.js"))
        self.assertIn("await loadRegion(id||'sd')", app)
        self.assertIn("GCMRegions.pickerList(REGIONS", app)

    def test_picker_is_top_chip(self):
        html = read(os.path.join(PUB, "index.html"))
        chips = re.search(r'<div id="chips">(.*?)<div id="help">', html, re.S).group(1)
        self.assertRegex(chips, r'^<label class="chip city"[^>]*>.*<select id="city"')   # first chip in the top row
        panel = html[html.index('<div id="setPanel"'):]
        self.assertNotIn('id="city"', panel[:panel.index('<details id="more"')])   # not in Settings
        self.assertNotIn('id="cityNow"', html)
        self.assertLess(html.index('src="regions.js"'), html.index('src="app.js"'))
        self.assertIn("'regions.js'", read(os.path.join(PUB, "sw.js")))

if __name__ == "__main__":
    unittest.main()
