"""Del Mar speed ordinance (Clerk's File 904-4, effective Nov 19 2026): the map must use the limit posted
today until the ordinance is in force and the new signs are confirmed. Guards against showing a 40-45 mph
stretch as LSV-legal early (bug fixed Oct 18 2026)."""
import glob, json, os, sys, unittest
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import overrides as O

def built(name, lat_lo, lat_hi):
    j = json.load(open(os.path.join(ROOT, "public/data/sd/index.json"))); N = j["names"]; out = []
    for f in glob.glob(os.path.join(ROOT, "public/data/sd/tiles/*.json")):
        for s in json.load(open(f)):
            p = s[7][len(s[7]) // 2]
            if N[s[0]] == name and lat_lo <= p[1] <= lat_hi and -117.275 <= p[0] <= -117.25 and s[3] == "v": out.append(s[2])
    return out

class DelMar(unittest.TestCase):
    def test_switch_needs_date_and_signs(self):
        self.assertFalse(O.dm_in_force("2026-11-18"))
        if not O.DM_SIGNS_CONFIRMED: self.assertFalse(O.dm_in_force("2027-01-01"))
    def test_overrides_use_todays_posted_limit(self):
        if O.dm_in_force(): self.skipTest("ordinance in force and signs confirmed")
        got = {(e["road"], e["from_to_segment_if_known"].split(" — ")[0]): e["speed_mph"] for e in O.INTEL if e.get("source_url") == O.DM_SRC}
        for road, seg, now_, new_ in O._DM:
            self.assertEqual(got[(road, seg)], now_, (road, seg))
    def test_built_data_blocks_40_45_stretches(self):
        if O.dm_in_force(): self.skipTest("ordinance in force and signs confirmed")
        for name, lo, hi, want in [("Camino del Mar", 32.9755, 32.981, 40), ("Jimmy Durante Boulevard", 32.9667, 32.9778, 45), ("Via de la Valle", 32.9794, 32.9805, 40)]:
            v = built(name, lo, hi)
            self.assertTrue(v, name)
            self.assertTrue(all(x > 35 for x in v), (name, sorted(set(v))))
if __name__ == "__main__": unittest.main()
