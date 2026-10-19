"""Trails and Coronado gaps (Oct 19 2026).
1. Coronado 1st St and Ocean Blvd (Alameda Blvd - Marina Ave) carry a posted limit (scripts/overrides.py), not Avoid/unknown.
2. Trails are never routable. Generic across every region's built tiles: a path-type segment (path/cycleway/footway/
   bridleway/track/pedestrian/steps) may only be routable when OSM tags it for golf carts (code 'c' cart path / 'd' designated).
3. San Diego: no routable service/unclassified/track segment with a trail name (build_data_lib.is_trail drops them at build time).
   Other regions have many real streets named "... Trail" (The Villages, Myrtle Beach campgrounds), so there the name check
   only prints a list for review."""
import glob, json, os, re, sys, unittest
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(R, "scripts"))
from build_data_lib import TRAIL_HW, TRAIL_NAME, is_trail

def jl(p):
    with open(p) as f: return json.load(f)
def regions(): return [x["id"] for x in jl(os.path.join(R, "public", "data", "regions.json"))]
def load(region):
    idx = jl(os.path.join(R, "public", "data", region, "index.json"))
    segs = []
    for f in sorted(glob.glob(os.path.join(R, "public", "data", region, "tiles", "*.json"))): segs += jl(f)
    return idx["names"], segs

def routable(s): return s[2] is not None and s[2] <= 35   # LSV limit; anything above is Avoid for every vehicle
def inb(p, b): return b[0] <= p[1] <= b[2] and b[1] <= p[0] <= b[3]
def name_trails(names, segs):
    return sorted({(names[s[0]], s[1]) for s in segs if s[3] not in ("c", "d") and routable(s)
                   and s[1] in ("service", "unclassified", "track") and TRAIL_NAME.search(names[s[0]] or "")})

class Coronado(unittest.TestCase):
    def test_first_st_and_ocean_blvd_have_limits(self):
        names, segs = load("sd")
        boxes = {"1st Street": (32.695, -117.1825, 32.7035, -117.1675), "Ocean Boulevard": (32.6815, -117.1871, 32.6860, -117.1795)}
        for road, b in boxes.items():
            got = [s for s in segs if names[s[0]] == road and inb(s[7][len(s[7]) // 2], b)]
            self.assertGreater(len(got), 3, road)
            bad = [(s[1], s[2], s[3], s[7][0]) for s in got if s[2] in (None, 99) or s[2] > 35]
            self.assertEqual(bad, [], f"Coronado {road} lost its posted limit")

class Trails(unittest.TestCase):
    def test_is_trail(self):
        self.assertTrue(is_trail({"highway": "unclassified", "name": "San Diego River Trail North", "bicycle": "designated", "surface": "asphalt"}))
        self.assertTrue(is_trail({"highway": "cycleway"}))
        self.assertTrue(is_trail({"highway": "unclassified", "name": "Old Sea World Drive", "motor_vehicle": "no", "bicycle": "designated"}))
        self.assertFalse(is_trail({"highway": "residential", "name": "Blue Dawn Trail"}))       # real street
        self.assertFalse(is_trail({"highway": "path", "golf_cart": "designated"}))             # cart path
        self.assertFalse(is_trail({"highway": "service", "motor_vehicle": "private"}))         # gated drive, not a trail

    def test_path_types_never_routable_all_regions(self):
        bad = {}
        for r in regions():
            if not os.path.exists(os.path.join(R, "public", "data", r, "index.json")): continue
            names, segs = load(r)
            b = [(names[s[0]], s[1]) for s in segs if s[1] in TRAIL_HW and s[3] not in ("c", "d") and routable(s)]
            if b: bad[r] = sorted(set(b))[:10]
        self.assertEqual(bad, {})

    def test_sd_named_trails_not_routable(self):
        names, segs = load("sd")
        self.assertEqual(name_trails(names, segs), [])
        self.assertFalse([s for s in segs if names[s[0]] == "San Diego River Trail North"], "River Trail North is back in the SD data")

    def test_report_named_trails_other_regions(self):
        """Informational: lists other regions' routable service/unclassified ways named like trails (many are real streets)."""
        tot = 0
        for r in regions():
            if r == "sd" or not os.path.exists(os.path.join(R, "public", "data", r, "index.json")): continue
            names, segs = load(r); t = name_trails(names, segs); tot += len(t)
            if t and os.environ.get("TRAIL_REPORT"): print(f"\n  {r}: {len(t)} named-trail roads: " + ", ".join(n for n, _ in t))
        if os.environ.get("TRAIL_REPORT"): print(f"\n  total {tot} (review only)")

if __name__ == "__main__":
    unittest.main()
