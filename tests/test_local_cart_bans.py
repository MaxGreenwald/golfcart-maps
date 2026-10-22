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
        for r in ("annamaria", "rockport", "chs", "staug"):
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
    def test_flag4_never_marks_a_road_green(self):
        # flag 4 only adds a golf-cart ban; it never replaces a both-vehicle ban (1) or a crossing (3)
        for r in ("annamaria", "rockport", "chs", "staug"):
            _, f = flagged(r)
            for nm, s in f: self.assertNotEqual(s[2], None, (r, nm))
if __name__ == "__main__": unittest.main()
