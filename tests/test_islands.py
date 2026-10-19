"""Same-road red islands (scripts/islands.py): the builders' heal rule and the validator's detector.
Regression for Max's Oct 18 2026 report: an unnamed carriageway of Soledad Mountain Rd (OSM way 1493577203, added Mar 2026
with no name/maxspeed) drew red between posted-35 pieces of the same road. Run: python3 -m unittest discover -s tests"""
import os, sys, json, glob, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import islands as I

def road(mid, mph=99, code="i", name=1, hw="secondary", m=100, src=-1):
    """A straight 3-piece road a-b-c-d along a meridian; middle piece mid=(mph, code, name) of length m metres."""
    d = m / 110540.0
    segs = [[name, hw, 35, "m", 0, 1, 2, [[-117.0, 32.0], [-117.0, 32.001]], 0],
            [mid[2], hw, mid[0], mid[1], 0, 2, 3, [[-117.0, 32.001], [-117.0, 32.001 + d]], src],
            [name, hw, 35, "t", 0, 3, 4, [[-117.0, 32.001 + d], [-117.0, 32.002 + d]]]]
    return segs, ["", "Soledad Mountain Road", "Other Road"], [["https://mapillary/x", "Mapillary corridor: posted <= 35"], ["u", "Mapillary: 1 posted 45 mph sign(s) detected"], ["u", "Mapillary: 3 posted 45 mph sign(s) detected"]]

class Heal(unittest.TestCase):
    def test_unnamed_carriageway_borrows_name_and_inherits(self):   # the Soledad case
        segs, names, src = road((99, "i", 0))
        ch = I.heal(segs, names, src)
        self.assertEqual(len(ch), 1); self.assertEqual(segs[1][2:4], [35, "n"]); self.assertEqual(names[segs[1][0]], "Soledad Mountain Road")
        self.assertIn("posted 35 mph on both sides", src[segs[1][8]][1])
    def test_named_untagged_piece_inherits(self):
        segs, names, src = road((99, "i", 1)); I.heal(segs, names, src); self.assertEqual(segs[1][2:4], [35, "n"])
    def test_single_osm_tag_becomes_caution_not_red(self):
        segs, names, src = road((45, "t", 1)); I.heal(segs, names, src)
        self.assertEqual(segs[1][2:4], [35, "q"]); self.assertIn("OpenStreetMap says 45", src[segs[1][8]][1])
    def test_long_single_source_stretch_stays_red_for_review(self):
        segs, names, src = road((45, "t", 1), m=500); self.assertEqual(I.heal(segs, names, src), []); self.assertEqual(segs[1][2], 45)
    def test_one_mapillary_sign_is_single_two_signs_confirm(self):
        segs, names, src = road((45, "m", 1), src=1); I.heal(segs, names, src); self.assertEqual(segs[1][3], "q")
        segs, names, src = road((45, "m", 1), src=2); I.heal(segs, names, src); self.assertEqual(segs[1][2:4], [45, "m"])
    def test_official_source_stays_red(self):
        segs, names, src = road((45, "v", 1)); self.assertEqual(I.heal(segs, names, src), []); self.assertEqual(segs[1][2], 45)
    def test_assumed_side_is_not_enough(self):
        segs, names, src = road((99, "i", 1)); segs[2][3] = "i"; segs[2][2] = 25
        self.assertEqual(I.heal(segs, names, src), []); self.assertEqual(segs[1][2], 99)
        self.assertEqual(len(I.find(segs, names)), 1)   # still reported to the validator
    def test_red_on_one_side_is_a_real_change(self):
        segs, names, src = road((99, "i", 1)); segs[2][2] = 45
        self.assertEqual(I.find(segs, names), [])
    def test_long_run_is_not_an_island(self):
        segs, names, src = road((99, "i", 1), m=900); self.assertEqual(I.find(segs, names), [])
    def test_freeway_and_bans_ignored(self):
        segs, names, src = road((99, "i", 1), hw="motorway"); self.assertEqual(I.find(segs, names), [])
        segs, names, src = road((99, "v", 1)); self.assertEqual(I.find(segs, names), [])   # ordinance ban, not speed data
    def test_unnamed_piece_between_two_different_roads_is_left_alone(self):
        segs, names, src = road((99, "i", 0)); segs[2][0] = 2
        self.assertEqual(I.heal(segs, names, src), [])

class RealData(unittest.TestCase):
    def load(self, r):
        root = os.path.join(HERE, "..", "public", "data", r)
        return [s for f in sorted(glob.glob(os.path.join(root, "tiles", "*.json"))) for s in json.load(open(f))], json.load(open(os.path.join(root, "index.json")))
    def test_soledad_mountain_road_carriageway_is_not_red(self):
        segs, ix = self.load("sd")
        hit = [s for s in segs if ix["names"][s[0]] == "Soledad Mountain Road" and abs(s[7][0][1] - 32.81562) < 1e-4 and abs(s[7][0][0] + 117.23579) < 1e-4 and s[4] == 1]
        self.assertTrue(hit)
        for s in hit: self.assertLessEqual(s[2], 35); self.assertIn(s[3], "vmn")
    def test_no_healable_island_left_in_any_region(self):
        for r in [x["id"] for x in json.load(open(os.path.join(HERE, "..", "public", "data", "regions.json")))]:
            segs, ix = self.load(r)
            for x in I.find(segs, ix["names"]):
                k = I.kind(x, segs, ix["sources"])
                if x["known_out"]: self.assertTrue(k == "confirmed" or (k == "single" and x["m"] > I.SINGLE_M), (r, x["name"], x["at"]))

if __name__ == "__main__": unittest.main()
