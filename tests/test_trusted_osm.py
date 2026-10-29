"""Trusted OSM ('o', scripts/trusted_osm.py): relabel only. It must never lift a ban, change a speed, or turn a road green."""
import glob, json, os, sys, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts")); import trusted_osm as T
def seg(name, mph, code, a, b, src=-1, flag=0): return [name, "secondary", mph, code, 0, a, b, [[0, 0], [1, 1]]] + ([src, flag] if flag else [src] if src >= 0 else [])
class Rule(unittest.TestCase):
    def test_explicit(self):
        self.assertTrue(T.explicit({"maxspeed": "35 mph"})); self.assertTrue(T.explicit({"maxspeed": "45", "source:maxspeed": "sign"}))
        for t in ({"maxspeed": "US:urban"}, {"maxspeed": "25 mph", "source:maxspeed": "US:residential"}, {"maxspeed": "25 mph", "maxspeed:type": "US:urban"},
                  {"maxspeed": "25 mph", "source:maxspeed": "California vehicle code 22352"}, {"maxspeed": "none"}, {}):
            self.assertFalse(T.explicit(t), t)
    def test_marks_when_neighbour_matches(self):
        out = [seg(1, 35, "t", 1, 2), seg(1, 35, "m", 2, 3, src=0)]
        self.assertEqual(T.mark(out, [0]), 1); self.assertEqual(out[0][3], "o"); self.assertEqual(out[0][2], 35)
    def test_needs_same_speed_same_road(self):
        for nb in (seg(1, 45, "m", 2, 3, src=0), seg(2, 35, "m", 2, 3, src=0), seg(1, 35, "i", 2, 3), seg(1, 35, "t", 2, 3), seg(1, 35, "d", 2, 3)):
            out = [seg(1, 35, "t", 1, 2), nb]; self.assertEqual(T.mark(out, [0]), 0, nb)
    def test_never_on_banned_or_from_banned(self):
        out = [seg(1, 35, "t", 1, 2, src=0, flag=1), seg(1, 35, "v", 2, 3, src=0)]; self.assertEqual(T.mark(out, [0]), 0)
        out = [seg(1, 35, "t", 1, 2), seg(1, 35, "v", 2, 3, src=0, flag=1)]; self.assertEqual(T.mark(out, [0]), 0)
        out = [seg(1, 99, "t", 1, 2), seg(1, 99, "v", 2, 3, src=0)]; self.assertEqual(T.mark(out, [0]), 0)
    def test_not_explicit_not_marked(self):
        out = [seg(1, 35, "t", 1, 2), seg(1, 35, "m", 2, 3, src=0)]; self.assertEqual(T.mark(out, []), 0)
class Data(unittest.TestCase):
    def test_every_o_segment_is_justified(self):
        n = 0
        for d in glob.glob(os.path.join(ROOT, "public/data/*/tiles")):
            segs = [s for f in glob.glob(d + "/*.json") for s in json.load(open(f))]
            at = {}
            for s in segs:
                for x in (s[5], s[6]): at.setdefault((x, s[0]), []).append(s)
            for s in segs:
                if s[3] != "o": continue
                n += 1
                self.assertTrue(s[2] is not None and s[2] < 99, s[:7]); self.assertFalse(len(s) > 9 and s[9] == 1, s[:7])
                nb = [y for x in (s[5], s[6]) for y in at[(x, s[0])] if y is not s]
                self.assertTrue(any((y[3] in "vm" or (y[3] == "d" and len(y) > 8 and y[8] >= 0)) and y[2] == s[2] and not (len(y) > 9 and y[9] == 1) for y in nb), s[:7])
        self.assertGreater(n, 0)
if __name__ == "__main__": unittest.main()
