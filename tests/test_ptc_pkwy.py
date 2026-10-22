"""Peachtree City ordinance (research/regions/ptc.json, enforcement record 2026-10-21): carts barred from Peachtree Pkwy /
N Peachtree Pkwy except to cross. The stretches with no posted limit of their own (built as an assumed 25, which the
GA golf cart cap of 25 let through: 0.34 mi) are banned per segment in build_region.py ('only_codes': ['i']), so no
Peachtree Pkwy segment is golf-cart OK. Posted <=35 stretches stay open to LSVs (state law)."""
import glob, json, math, os, re, unittest
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "data", "ptc")
PK = re.compile(r"(?i)^(north )?peachtree p(arkway|kwy)$")
class PtcPkwy(unittest.TestCase):
    def segs(self):
        names = json.load(open(os.path.join(D, "index.json")))["names"]; seen = set()
        for f in glob.glob(os.path.join(D, "tiles", "*.json")):
            for s in json.load(open(f)):
                if PK.match(names[s[0]]) and (s[5], s[6]) not in seen: seen.add((s[5], s[6])); yield s
    def test_no_golf_cart_ok_segment(self):
        bad = [(s[2], s[3], s[7][0]) for s in self.segs() if s[3] != "c" and s[2] is not None and s[2] <= 25]
        self.assertEqual(bad, [])
    def test_banned_stretches_cite_ordinance(self):
        src = json.load(open(os.path.join(D, "index.json")))["sources"]
        v = [s for s in self.segs() if s[3] == "v" and s[2] == 99]
        self.assertGreaterEqual(len(v), 12)
        self.assertTrue(all("Peachtree City cart ordinance" in src[s[8]][1] for s in v))
    def test_lsv_posted_stretches_stay_open(self):
        mi = sum(sum(math.hypot((b[0]-a[0])*92.9e3, (b[1]-a[1])*111e3) for a, b in zip(s[7], s[7][1:])) for s in self.segs() if s[2] is not None and s[2] <= 35) / 1609
        self.assertGreater(mi, 3.0)
if __name__ == "__main__": unittest.main()
