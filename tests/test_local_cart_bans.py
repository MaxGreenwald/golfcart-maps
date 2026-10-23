"""Local golf-cart-only bans (flag s[9] == 4, source D.sources[s[10]]), applied Oct 22 2026 with Max's OK.
Each ban must cite its ordinance/city page, sit on the named road inside the right city, and leave the speed alone."""
import glob, json, os, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def segs(r):
    ix = json.load(open(os.path.join(ROOT, "public/data", r, "index.json")))
    out = [s for f in glob.glob(os.path.join(ROOT, "public/data", r, "tiles/*.json")) for s in json.load(open(f))]
    return ix, out
def flagged(r):
    ix, out = segs(r)
    return ix, [(ix["names"][s[0]], s) for s in out if len(s) > 9 and s[9] == 4]
class LocalCartBans(unittest.TestCase):
    def test_every_flag4_cites_a_source(self):
        for r in ("annamaria", "rockport", "chs", "staug", "obx", "lwr"):
            ix, f = flagged(r)
            self.assertTrue(f, r)
            for nm, s in f:
                self.assertEqual(len(s), 11, (r, nm)); src = ix["sources"][s[10]]
                self.assertTrue(src[0].startswith("http") and src[1], (r, nm))
                self.assertNotEqual(s[3], "c", (r, nm))   # cart paths are never flagged
    def test_holmes_beach_roads(self):
        ix, f = flagged("annamaria")
        self.assertEqual({nm for nm, _ in f}, {"Gulf Drive", "Palm Drive", "Marina Drive"})
        for nm, s in f:
            lat = s[7][len(s[7])//2][1]
            self.assertTrue(27.48 < lat < 27.53, (nm, lat))   # Holmes Beach only, not Bradenton Beach or Anna Maria city
            if nm == "Marina Drive": self.assertLessEqual(lat, 27.5152)   # 5300-6600 blocks only
            self.assertIn("62-39", ix["sources"][s[10]][1])
        _, allsegs = segs("annamaria")
        self.assertTrue(any(ix["names"][s[0]] == "Gulf Drive" and not (len(s) > 9 and s[9] == 4) for s in allsegs))   # Gulf Dr outside Holmes Beach untouched
    def test_charleston_roads(self):
        _, f = flagged("chs")
        self.assertEqual({nm for nm, _ in f}, {"Palm Boulevard", "Center Street", "Folly Road"})
    def test_rockport_state_system_only(self):
        ix, f = flagged("rockport")
        for nm, s in f: self.assertIn("98-133", ix["sources"][s[10]][1])
        self.assertTrue(any("FM" in nm or "Farm-to-Market" in nm for nm, _ in f))
    def test_st_augustine_beach_streets(self):
        ix, f = flagged("staug")
        self.assertGreater(len(f), 300)
        for nm, s in f:
            lat, lon = s[7][len(s[7])//2][1], s[7][len(s[7])//2][0]
            self.assertTrue(29.81 < lat < 29.87 and -81.29 < lon < -81.25, (nm, lat, lon))
    def test_outer_banks_towns(self):
        # Dare County map + town codes (Oct 22 2026): carts barred from KDH/Kitty Hawk/Southern Shores/Nags Head/Colington/
        # unincorporated Roanoke Island roads; Duck only along NC 12; Manteo only on US 64
        ix, f = flagged("obx")
        labs = {ix["sources"][s[10]][1] for _, s in f}
        for town in ("Kill Devil Hills", "Kitty Hawk", "Southern Shores", "42-92(b)", "Colington", "unincorporated Manteo", "46-152", "18-04"):
            self.assertTrue(any(town in l for l in labs), town)
        for nm, s in f:
            l = ix["sources"][s[10]][1]
            if "18-04" in l: self.assertIn(nm, ("Duck Road", "NC 12"))
            if "46-152" in l: self.assertIn(nm, ("N US Highway 64", "S US Highway 64"))
        _, allsegs = segs("obx")
        duck_side = [s for s in allsegs if ix["names"][s[0]] in ("Sea Hawk Drive", "Ships Watch Drive", "Plover Drive") and not (len(s) > 9 and s[9] == 4)]
        self.assertTrue(duck_side)   # Duck side streets stay open to registered carts
        gj = json.load(open(os.path.join(ROOT, "research/city_limits/manteo.json")))["geojson"]
        rings = [p[0] for p in gj["coordinates"]] if gj["type"] == "MultiPolygon" else [gj["coordinates"][0]]
        def inside(x, y):
            for ring in rings:
                c = False
                for i in range(len(ring)):
                    (x1, y1), (x2, y2) = ring[i - 1][:2], ring[i][:2]
                    if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
                if c: return True
            return False
        town = [s for s in allsegs if all(inside(*q[:2]) for q in s[7])]   # wholly inside (the builder tests the raw-node midpoint)
        self.assertGreater(len(town), 100)
        for s in town:   # inside Manteo town limits only US 64 is barred; permitted road-legal carts use the rest
            if len(s) > 9 and s[9] == 4: self.assertIn(ix["names"][s[0]], ("N US Highway 64", "S US Highway 64"))
        self.assertTrue(any(ix["names"][s[0]] == "Budleigh Street" for s in town))
        us158 = [ix["sources"][s[8]] for s in allsegs if len(s) > 9 and s[9] == 1 and "158" in ix["sources"][s[8]][1]]
        self.assertTrue(us158 and all(u[0].startswith("http") for u in us158))   # US 158 ban now cited
    def test_lakewood_ranch_villages(self):
        ix, f = flagged("lwr")
        self.assertGreater(len(f), 500)
        for nm, s in f:
            self.assertIn("mylwr.com", ix["sources"][s[10]][0])
            self.assertNotEqual(s[3], "d", nm)   # never over a designated cart road
    def test_flag4_never_marks_a_road_green(self):
        # flag 4 only adds a golf-cart ban; it never replaces a both-vehicle ban (1) or a crossing (3)
        for r in ("annamaria", "rockport", "chs", "staug", "obx", "lwr"):
            _, f = flagged(r)
            for nm, s in f: self.assertNotEqual(s[2], None, (r, nm))
if __name__ == "__main__": unittest.main()
